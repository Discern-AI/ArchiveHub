"""The live interview socket: /ws/interviews/<session id>.

Client → server: binary frames of 16 kHz mono 16-bit PCM, and JSON
{"type": "pause" | "resume" | "end"}.

Server → client JSON: ready, partial (provisional live words), line (a finished line,
saved), notes (people, places, dates and questions picked up), notice, paused, resumed,
ended, error.

Every byte of audio received while recording is kept in the original WAV. Transcription
and notes run in worker threads so the socket never stalls; prompts never interrupt the
speaker because they only ever appear in the side panel.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from pathlib import Path

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.core.files import File
from django.utils import timezone

from assistant.providers import USER_MESSAGES, ProviderError
from core.models import audit
from projects.permissions import writable_chats

from .analysis import get_analyst
from .audio import BYTES_PER_SAMPLE, SAMPLE_RATE, Partial, Recorder, Segmenter, Utterance
from .models import InterviewSession, Note, NoteStatus, Segment, SessionStatus
from .speech import SpeechUnavailable, get_speech_providers

logger = logging.getLogger(__name__)

MAX_FRAME_BYTES = 64 * 1024
# Audio may arrive a little faster than real time (buffering), but never much faster.
REALTIME_SLACK_SECONDS = 10
CLOSE_UNAUTHORISED = 4401
CLOSE_FORBIDDEN = 4403
CLOSE_UNAVAILABLE = 4503
NOTES_STOP_KINDS = {"config", "billing"}


def note_json(n: Note) -> dict:
    return {
        "id": str(n.id), "kind": n.kind, "text": n.text, "detail": n.detail,
        "lines": n.lines, "status": n.status,
    }  # fmt: skip


@database_sync_to_async
def _load_session(user, session_id) -> InterviewSession | None:
    return (
        InterviewSession.objects.filter(
            pk=session_id, chat__in=writable_chats(user), status=SessionStatus.READY
        )
        .select_related("chat")
        .first()
    )


@database_sync_to_async
def _set_status(session: InterviewSession, status: str) -> None:
    session.status = status
    session.save(update_fields=["status", "updated_at"])


@database_sync_to_async
def _save_line(session, line, start_ms, end_ms, text, engine) -> Segment:
    return Segment.objects.create(
        session=session, line=line, start_ms=start_ms, end_ms=end_ms, text=text,
        speaker=session.narrator, engine=engine,
    )  # fmt: skip


@database_sync_to_async
def _transcript(session) -> list[tuple[int, str, str]]:
    return list(session.segments.values_list("line", "speaker", "text"))


@database_sync_to_async
def _known_notes(session) -> list[str]:
    return [f"{k}:{t}" for k, t in session.notes.values_list("kind", "text")]


@database_sync_to_async
def _save_notes(session, result) -> list[dict]:
    saved = [
        Note.objects.create(
            session=session,
            kind=i.kind,
            text=i.text,
            detail=i.detail,
            lines=i.lines,
            status=NoteStatus.OPEN,
        )  # fmt: skip
        for i in result.items
    ]
    u = result.usage
    session.analysis_model = u.model or session.analysis_model
    session.analysis_input_tokens += u.input_tokens
    session.analysis_output_tokens += u.output_tokens
    session.save()
    return [note_json(n) for n in saved]


@database_sync_to_async
def _store_recording(session, recorder: Recorder, status: str, engine: str, user) -> None:
    size, sha = recorder.close()
    with recorder.path.open("rb") as fh:
        session.audio.save("interview.wav", File(fh), save=False)
    recorder.path.unlink(missing_ok=True)
    session.audio_size, session.audio_sha256 = size, sha
    session.duration_ms = recorder.duration_ms
    session.speech_engine = engine
    session.status = status
    session.ended_at = timezone.now()
    session.save()
    audit(user, "interview.recorded", session, duration_ms=session.duration_ms, status=status)


class InterviewConsumer(AsyncWebsocketConsumer):
    async def connect(self) -> None:
        user = self.scope.get("user")
        if user is None or not user.is_authenticated:
            await self.close(code=CLOSE_UNAUTHORISED)
            return
        session = await _load_session(user, self.scope["url_route"]["kwargs"]["session_id"])
        if session is None:
            await self.close(code=CLOSE_FORBIDDEN)
            return
        self.user = user
        self.session = session
        self.stopped = False
        self.paused = False
        self.line = 0
        self.started = time.monotonic()
        self.paused_seconds = 0.0
        self.paused_since: float | None = None
        self.segmenter = Segmenter()
        self.recorder: Recorder | None = None
        self.finals: asyncio.Queue[Utterance | None] = asyncio.Queue()
        self.partial_task: asyncio.Task | None = None
        self.notes_task: asyncio.Task | None = None
        self.notes_pending = False
        self.notes_enabled = True
        self.first_unnoted = 1
        await self.accept()

        try:
            self.speech, self.live_speech = get_speech_providers()
            await asyncio.to_thread(self.speech.warm_up)
            await asyncio.to_thread(self.live_speech.warm_up)
        except SpeechUnavailable as exc:
            await self._send("error", text=str(exc))
            await self.close(code=CLOSE_UNAVAILABLE)
            self.stopped = True
            return
        self.analyst = get_analyst()
        self.recorder = Recorder(Path(settings.MEDIA_ROOT) / "interviews" / "tmp")
        self.final_worker = asyncio.create_task(self._final_worker())
        await _set_status(session, SessionStatus.RECORDING)
        await self._send("ready", engine=self.speech.engine)

    async def disconnect(self, code) -> None:
        # Lost connection: keep everything recorded so far; the user can still finish.
        if getattr(self, "recorder", None) is not None and not self.stopped:
            await self._stop(SessionStatus.INTERRUPTED)

    # --- Receiving ------------------------------------------------------------------

    async def receive(self, text_data=None, bytes_data=None) -> None:
        if self.stopped or self.recorder is None:
            return
        if bytes_data is not None:
            await self._audio(bytes_data)
            return
        try:
            kind = json.loads(text_data or "{}").get("type")
        except (json.JSONDecodeError, AttributeError):
            return
        if kind == "pause" and not self.paused:
            self.paused, self.paused_since = True, time.monotonic()
            self._queue_final(self.segmenter.flush())
            await _set_status(self.session, SessionStatus.PAUSED)
            await self._send("paused")
        elif kind == "resume" and self.paused:
            self.paused = False
            self.paused_seconds += time.monotonic() - (self.paused_since or time.monotonic())
            await _set_status(self.session, SessionStatus.RECORDING)
            await self._send("resumed")
        elif kind == "end":
            await self._stop(SessionStatus.ENDED)
            await self.close()

    async def _audio(self, data: bytes) -> None:
        if self.paused:
            return  # nothing is recorded while paused
        if len(data) > MAX_FRAME_BYTES:
            await self._fail("Audio arrived in pieces that were too large.")
            return
        recorded = self.recorder.bytes_written + len(data)
        elapsed = time.monotonic() - self.started - self.paused_seconds
        if recorded > (elapsed + REALTIME_SLACK_SECONDS) * SAMPLE_RATE * BYTES_PER_SAMPLE:
            await self._fail("Audio arrived faster than it can be spoken.")
            return
        self.recorder.write(data)
        for event in self.segmenter.feed(data):
            if isinstance(event, Utterance):
                self._queue_final(event)
            elif isinstance(event, Partial):
                self._start_partial(event)
        if self.recorder.duration_ms >= settings.INTERVIEW_MAX_MINUTES * 60_000:
            await self._send("notice", text="This interview reached the time limit and stopped.")
            await self._stop(SessionStatus.ENDED)
            await self.close()

    # --- Transcription --------------------------------------------------------------

    def _queue_final(self, utterance: Utterance | None) -> None:
        if utterance is not None:
            self.finals.put_nowait(utterance)

    def _start_partial(self, event: Partial) -> None:
        # Live words are best-effort: skip if a line is waiting or one is already running.
        if self.finals.qsize() or (self.partial_task and not self.partial_task.done()):
            return
        self.partial_task = asyncio.create_task(self._partial(event))

    async def _partial(self, event: Partial) -> None:
        try:
            result = await asyncio.to_thread(self.live_speech.transcribe, event.pcm, False)
        except Exception:
            logger.exception("Live transcription failed")
            return
        if result.text and not self.stopped and self.segmenter.speaking:
            await self._send("partial", text=result.text, start_ms=event.start_ms)

    async def _final_worker(self) -> None:
        while True:
            utterance = await self.finals.get()
            if utterance is None:
                return
            try:
                await self._final(utterance)
            except Exception:
                logger.exception("Transcribing a line failed")
                await self._send("notice", text="A line couldn't be transcribed. "
                                 "The recording still has it.")  # fmt: skip

    async def _final(self, u: Utterance) -> None:
        recent = await _transcript(self.session)
        context = " ".join(text for _, _, text in recent[-3:])
        result = await asyncio.to_thread(self.speech.transcribe, u.pcm, True, context)
        if not result.text:
            return
        self.line += 1
        seg = await _save_line(
            self.session, self.line, u.start_ms, u.end_ms, result.text, result.engine
        )
        await self._send(
            "line", line=seg.line, text=seg.text, speaker=seg.speaker,
            start_ms=seg.start_ms, end_ms=seg.end_ms,
        )  # fmt: skip
        self._request_notes()

    # --- Notes ----------------------------------------------------------------------

    def _request_notes(self) -> None:
        if not self.notes_enabled:
            return
        if self.notes_task and not self.notes_task.done():
            self.notes_pending = True  # picked up when the current run finishes
            return
        self.notes_task = asyncio.create_task(self._notes())

    async def _notes(self) -> None:
        while True:
            self.notes_pending = False
            lines = await _transcript(self.session)
            if not lines or lines[-1][0] < self.first_unnoted:
                return
            first_new = self.first_unnoted
            self.first_unnoted = lines[-1][0] + 1
            known = await _known_notes(self.session)
            try:
                result = await asyncio.to_thread(
                    self.analyst.notes, self.session.narrator, lines, first_new, known
                )
            except ProviderError as exc:
                await self._notes_failed(exc.kind)
                return
            except Exception:
                logger.exception("Interview notes failed")
                await self._notes_failed("unknown")
                return
            items = await _save_notes(self.session, result)
            if items:
                await self._send("notes", items=items)
            if not self.notes_pending:
                return

    async def _notes_failed(self, kind: str) -> None:
        if kind in NOTES_STOP_KINDS:
            self.notes_enabled = False
            await self._send(
                "notice",
                text=f"{USER_MESSAGES.get(kind, USER_MESSAGES['unknown'])} Notes are off for "
                "this interview; the recording and transcript carry on.",
            )

    # --- Stopping -------------------------------------------------------------------

    async def _stop(self, status: str) -> None:
        if self.stopped:
            return
        self.stopped = True
        self._queue_final(self.segmenter.flush())
        self.finals.put_nowait(None)
        await self.final_worker  # every line said before "end" is transcribed
        if self.partial_task:
            self.partial_task.cancel()
        if self.notes_task and not self.notes_task.done():
            with contextlib.suppress(Exception):
                await asyncio.wait_for(self.notes_task, timeout=60)
        await _store_recording(self.session, self.recorder, status, self.speech.engine, self.user)
        if status == SessionStatus.ENDED:
            await self._send("ended", duration_ms=self.session.duration_ms, lines=self.line)

    async def _fail(self, text: str) -> None:
        await self._send("error", text=text)
        await self._stop(SessionStatus.INTERRUPTED)
        await self.close(code=CLOSE_FORBIDDEN)

    async def _send(self, kind: str, **data) -> None:
        with contextlib.suppress(Exception):  # the browser may already have gone
            await self.send(text_data=json.dumps({"type": kind, **data}))
