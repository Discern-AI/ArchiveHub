"""WP5: live guided interviews. Audio is synthetic (tones and silence); speech and notes
use the fake providers."""

import hashlib
import io
import math
import struct
import wave

import pytest
from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core.management import call_command
from django.utils import timezone

from assistant.providers import ProviderError
from interviews.analysis import FakeAnalyst, NoteItem, clean_items, resolve_line_citations
from interviews.audio import FRAME_MS, MAX_LINE_MS, Partial, Recorder, Segmenter, Utterance
from interviews.models import InterviewSession, Note, Segment, SessionStatus
from interviews.routing import websocket_urlpatterns
from interviews.wer import wer
from projects.models import Chat, Message

RATE = 16_000


def tone(ms: int, amplitude: int = 8000) -> bytes:
    n = RATE * ms // 1000
    return b"".join(
        struct.pack("<h", int(amplitude * math.sin(2 * math.pi * 440 * i / RATE))) for i in range(n)
    )


def silence(ms: int) -> bytes:
    return b"\x00\x00" * (RATE * ms // 1000)


def utterances(events):
    return [e for e in events if isinstance(e, Utterance)]


# --- Segmenter and recorder ----------------------------------------------------------


def test_pause_ends_a_line():
    seg = Segmenter()
    events = seg.feed(silence(500) + tone(1500) + silence(1000))
    [u] = utterances(events)
    assert 150 <= u.start_ms <= 500  # includes a little pre-roll
    assert abs(u.end_ms - 2000) <= 2 * FRAME_MS
    assert len(u.pcm) == (u.end_ms - u.start_ms) * RATE // 1000 * 2
    assert any(isinstance(e, Partial) for e in events)  # live words while speaking


def test_clicks_are_not_lines():
    seg = Segmenter()
    assert utterances(seg.feed(silence(300) + tone(150) + silence(1500))) == []


def test_long_speech_is_cut_and_flush_keeps_the_rest():
    seg = Segmenter()
    events = seg.feed(tone(MAX_LINE_MS + 3000))
    assert len(utterances(events)) == 1
    rest = seg.flush()
    assert rest is not None and rest.end_ms > rest.start_ms


def test_feeding_odd_sizes_gives_the_same_lines():
    audio = silence(300) + tone(1200) + silence(1000) + tone(900) + silence(1000)
    whole = utterances(Segmenter().feed(audio))
    seg = Segmenter()
    pieces = []
    for i in range(0, len(audio), 777):
        pieces += utterances(seg.feed(audio[i : i + 777]))
    assert [(u.start_ms, u.end_ms) for u in pieces] == [(u.start_ms, u.end_ms) for u in whole]
    assert len(whole) == 2


def test_recorder_keeps_every_byte(tmp_path):
    rec = Recorder(tmp_path)
    audio = tone(700) + silence(300)
    rec.write(audio[:1001])  # odd byte count: the half sample is dropped
    rec.write(audio[1000:])
    size, sha = rec.close()
    data = rec.path.read_bytes()
    assert size == len(data) and sha == hashlib.sha256(data).hexdigest()
    with wave.open(io.BytesIO(data)) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (RATE, 1, 2)
        assert w.readframes(w.getnframes()) == audio
    assert rec.duration_ms == 1000


# --- Analysis helpers ----------------------------------------------------------------


def test_wer():
    assert wer("My grandmother ran the bakery.", "my grandmother ran the bakery") == 0
    assert wer("one two three four", "one too three") == 0.5


def test_line_citations_are_built_by_the_server():
    text, sources = resolve_line_citations(
        "You spoke about the bakery [L2] and the street [L1][L9].",
        {1: "I grew up on Cheap Street.", 2: "Alice ran the bakery."},
        "/interviews/x",
    )
    assert text == "You spoke about the bakery [2] and the street [1]."
    assert [s["n"] for s in sources] == [1, 2]
    assert sources[1]["url"] == "/interviews/x#line-2"


def test_notes_must_cite_new_lines_and_not_repeat():
    data = {
        "people": [
            {"text": "Alice Marsh", "detail": "", "lines": [2]},
            {"text": "Ghost", "detail": "", "lines": [7]},  # no such line
        ],
        "places": [{"text": "Newbury", "detail": "", "lines": [2]}],  # already noted
        "dates": [],
        "questions": [{"text": f"Q{i}?", "detail": "", "lines": [2]} for i in range(4)],
    }
    items = clean_items(data, {2}, ["place:newbury"])
    assert [(i.kind, i.text) for i in items] == [
        ("person", "Alice Marsh"),
        ("question", "Q0?"),
        ("question", "Q1?"),
    ]
    assert isinstance(items[0], NoteItem)


# --- REST ----------------------------------------------------------------------------


@pytest.fixture
def chat(alice):
    return Chat.objects.create(owner=alice)


def make_session(chat, user, **kw) -> InterviewSession:
    return InterviewSession.objects.create(
        chat=chat, started_by=user, narrator="Alice Marsh", consent_confirmed_by=user,
        consent_confirmed_at=timezone.now(), consent_notice="notice", **kw,
    )  # fmt: skip


def test_starting_needs_consent_and_a_narrator(alice_client, chat):
    url = f"/api/v1/chats/{chat.id}/interviews"
    r = alice_client.post(url, {"narrator": "Gran", "consent": False}, "application/json")
    assert r.status_code == 422 and "recorded" in r.json()["detail"]
    r = alice_client.post(url, {"narrator": "  ", "consent": True}, "application/json")
    assert r.status_code == 422
    r = alice_client.post(url, {"narrator": "Gran", "consent": True}, "application/json")
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "ready" and body["consent_notice"].startswith("This interview")
    assert alice_client.get("/api/v1/interviews/notice").json()["notice"] == body["consent_notice"]


def test_others_cannot_start_or_see_interviews(bob_client, chat, alice):
    r = bob_client.post(
        f"/api/v1/chats/{chat.id}/interviews",
        {"narrator": "Gran", "consent": True},
        "application/json",
    )
    assert r.status_code == 404
    s = make_session(chat, alice)
    assert bob_client.get(f"/api/v1/interviews/{s.id}").status_code == 404
    assert bob_client.get(f"/api/v1/interviews/{s.id}/audio").status_code == 404
    assert bob_client.post(f"/api/v1/interviews/{s.id}/finish").status_code == 404


def _ended_session(chat, alice) -> InterviewSession:
    s = make_session(chat, alice, status=SessionStatus.ENDED, duration_ms=65_000)
    Segment.objects.create(session=s, line=1, start_ms=0, end_ms=2000, speaker="Alice Marsh",
                           text="I grew up on Cheap Street.", engine="fake")  # fmt: skip
    Segment.objects.create(session=s, line=2, start_ms=3000, end_ms=6000, speaker="Alice Marsh",
                           text="Gran ran the bakery.", engine="fake")  # fmt: skip
    Note.objects.create(session=s, kind="question", text="What was the bakery called?", lines=[2])
    return s


def test_end_and_send_writes_transcript_and_response(alice_client, chat, alice):
    s = _ended_session(chat, alice)
    r = alice_client.post(f"/api/v1/interviews/{s.id}/finish")
    assert r.status_code == 200
    body = r.json()
    transcript, reply = body["messages"]
    assert body["response_error"] is None
    assert transcript["role"] == "user"
    assert transcript["content"].startswith("Interview with Alice Marsh (1 min 5 s)")
    assert "2. Alice Marsh: Gran ran the bakery." in transcript["content"]
    assert reply["role"] == "assistant"
    assert "What was the bakery called?" in reply["content"]
    assert reply["sources"][0]["url"] == f"/interviews/{s.id}#line-1"
    # The transcript is replayed to the assistant later as marked data.
    stored = Message.objects.get(pk=transcript["id"])
    assert "<interview_transcript" in stored.raw_content[0]["text"]
    # Repeating is safe.
    again = alice_client.post(f"/api/v1/interviews/{s.id}/finish").json()
    assert [m["id"] for m in again["messages"]] == [transcript["id"], reply["id"]]
    assert Message.objects.filter(chat=chat).count() == 2


def test_failed_response_is_not_saved_and_can_be_retried(alice_client, chat, alice, monkeypatch):
    s = _ended_session(chat, alice)

    def broken(*args, **kwargs):
        raise ProviderError("billing")

    monkeypatch.setattr(FakeAnalyst, "response", broken)
    body = alice_client.post(f"/api/v1/interviews/{s.id}/finish").json()
    assert "run out of credit" in body["response_error"]
    assert [m["role"] for m in body["messages"]] == ["user"]
    monkeypatch.undo()
    body = alice_client.post(f"/api/v1/interviews/{s.id}/finish").json()
    assert [m["role"] for m in body["messages"]] == ["user", "assistant"]
    assert body["response_error"] is None


def test_cannot_finish_while_recording(alice_client, chat, alice):
    s = make_session(chat, alice, status=SessionStatus.RECORDING)
    assert alice_client.post(f"/api/v1/interviews/{s.id}/finish").status_code == 409


def test_speakers_and_notes_can_be_corrected(alice_client, bob_client, chat, alice):
    s = _ended_session(chat, alice)
    url = f"/api/v1/interviews/{s.id}/lines/2"
    assert bob_client.patch(url, {"speaker": "Bob"}, "application/json").status_code == 404
    r = alice_client.patch(url, {"speaker": "Interviewer"}, "application/json")
    assert r.json() == {"line": 2, "speaker": "Interviewer"}
    note = s.notes.get()
    r = alice_client.patch(
        f"/api/v1/interview-notes/{note.id}", {"status": "dismissed"}, "application/json"
    )
    assert r.json()["status"] == "dismissed"
    detail = alice_client.get(f"/api/v1/interviews/{s.id}").json()
    assert detail["segments"][1]["speaker"] == "Interviewer"
    assert detail["notes"][0]["status"] == "dismissed"


# --- The live socket -----------------------------------------------------------------


async def connect(session, user):
    comm = WebsocketCommunicator(URLRouter(websocket_urlpatterns), f"/ws/interviews/{session.id}")
    comm.scope["user"] = user
    connected, _ = await comm.connect()
    return comm, connected


async def until(comm, kind, seen=None, timeout=5):
    while True:
        msg = await comm.receive_json_from(timeout=timeout)
        if seen is not None:
            seen.append(msg)
        if msg["type"] == kind:
            return msg


async def send_audio(comm, audio, chunk=3200):
    for i in range(0, len(audio), chunk):
        await comm.send_to(bytes_data=audio[i : i + chunk])


@pytest.mark.django_db(transaction=True)
async def test_live_interview_end_to_end(alice):
    chat = await Chat.objects.acreate(owner=alice)
    session = await sync_to_async(make_session)(chat, alice)
    comm, connected = await connect(session, alice)
    assert connected
    assert (await until(comm, "ready"))["engine"] == "fake"

    seen: list[dict] = []
    first = silence(300) + tone(1500) + silence(1000)
    await send_audio(comm, first)
    line = await until(comm, "line", seen)
    assert line["line"] == 1 and line["text"] == "I grew up on Cheap Street in Newbury."
    assert line["speaker"] == "Alice Marsh"
    assert any(m["type"] == "partial" for m in seen)
    notes = await until(comm, "notes")
    assert {n["text"] for n in notes["items"]} == {"Cheap Street", "Newbury"}

    await comm.send_json_to({"type": "pause"})
    await until(comm, "paused")
    await send_audio(comm, tone(1000))  # not recorded while paused
    await comm.send_json_to({"type": "resume"})
    await until(comm, "resumed")

    second = tone(1500) + silence(1000)
    await send_audio(comm, second)
    line = await until(comm, "line")
    assert line["line"] == 2 and "1931" in line["text"]
    notes = await until(comm, "notes")
    kinds = {(n["kind"], n["text"]) for n in notes["items"]}
    assert ("person", "Alice Marsh") in kinds and ("date", "1931") in kinds
    assert ("question", "What was the bakery called?") in kinds

    await comm.send_json_to({"type": "end"})
    ended = await until(comm, "ended")
    assert ended["lines"] == 2
    await comm.wait()

    session = await InterviewSession.objects.aget(pk=session.id)
    assert session.status == SessionStatus.ENDED
    assert session.duration_ms == (len(first) + len(second)) * 1000 // (RATE * 2)
    data = await sync_to_async(lambda: session.audio.open("rb").read())()
    assert hashlib.sha256(data).hexdigest() == session.audio_sha256
    with wave.open(io.BytesIO(data)) as w:
        assert w.readframes(w.getnframes()) == first + second
    assert await Segment.objects.filter(session=session).acount() == 2


@pytest.mark.django_db(transaction=True)
async def test_lost_connection_keeps_the_recording(alice):
    chat = await Chat.objects.acreate(owner=alice)
    session = await sync_to_async(make_session)(chat, alice)
    comm, _ = await connect(session, alice)
    await until(comm, "ready")
    await send_audio(comm, tone(1200))  # still speaking when the connection drops
    await comm.disconnect()
    session = await InterviewSession.objects.aget(pk=session.id)
    assert session.status == SessionStatus.INTERRUPTED
    assert session.audio and session.duration_ms == 1200
    assert await Segment.objects.filter(session=session).acount() == 1


@pytest.mark.django_db(transaction=True)
async def test_others_and_used_sessions_are_refused(alice, bob):
    chat = await Chat.objects.acreate(owner=alice)
    session = await sync_to_async(make_session)(chat, alice)
    _, connected = await connect(session, bob)
    assert not connected
    used = await sync_to_async(make_session)(chat, alice, status=SessionStatus.ENDED)
    _, connected = await connect(used, alice)
    assert not connected


@pytest.mark.django_db(transaction=True)
async def test_websocket_rejects_other_origins(alice):
    from archivehub.asgi import application

    chat = await Chat.objects.acreate(owner=alice)
    session = await sync_to_async(make_session)(chat, alice)
    comm = WebsocketCommunicator(
        application, f"/ws/interviews/{session.id}", headers=[(b"origin", b"https://evil.example")]
    )
    connected, _ = await comm.connect()
    assert not connected


@pytest.mark.django_db(transaction=True)
async def test_audio_faster_than_speech_is_refused(alice):
    chat = await Chat.objects.acreate(owner=alice)
    session = await sync_to_async(make_session)(chat, alice)
    comm, _ = await connect(session, alice)
    await until(comm, "ready")
    await send_audio(comm, silence(12_000), chunk=32_000)
    error = await until(comm, "error")
    assert "faster" in error["text"]
    assert (await comm.receive_output(timeout=5))["type"] == "websocket.close"
    session = await InterviewSession.objects.aget(pk=session.id)
    assert session.status == SessionStatus.INTERRUPTED


@pytest.mark.django_db(transaction=True)
async def test_notes_failing_never_stops_the_transcript(alice, monkeypatch):
    def broken(*args, **kwargs):
        raise ProviderError("billing")

    monkeypatch.setattr(FakeAnalyst, "notes", broken)
    chat = await Chat.objects.acreate(owner=alice)
    session = await sync_to_async(make_session)(chat, alice)
    comm, _ = await connect(session, alice)
    await until(comm, "ready")
    await send_audio(comm, tone(1500) + silence(1000))
    seen: list[dict] = []
    await until(comm, "notice", seen)
    await send_audio(comm, tone(1500) + silence(1000))
    await until(comm, "line", seen)
    lines = [m for m in seen if m["type"] == "line"]
    assert len(lines) == 2
    await comm.send_json_to({"type": "end"})
    await until(comm, "ended")


@pytest.mark.django_db(transaction=True)
async def test_missing_speech_engine_is_explained(alice, settings):
    settings.SPEECH_PROVIDER = "not-installed"
    chat = await Chat.objects.acreate(owner=alice)
    session = await sync_to_async(make_session)(chat, alice)
    comm, connected = await connect(session, alice)
    assert connected
    error = await until(comm, "error")
    assert "not-installed" in error["text"]


# --- Speech spike --------------------------------------------------------------------


def test_speech_spike_report(tmp_path):
    folder = tmp_path / "spike"
    folder.mkdir()
    audio = silence(300) + tone(1500) + silence(1000) + tone(1500) + silence(1000)
    with wave.open(str(folder / "gran.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(audio)
    (folder / "gran.txt").write_text(
        "I grew up on Cheap Street in Newbury. "
        "My grandmother Alice Marsh ran the bakery there from 1931.",
        encoding="utf-8",
    )
    (folder / "manifest.csv").write_text("file,group\ngran.wav,older speaker\n", encoding="utf-8")
    out = tmp_path / "report.md"
    call_command("speech_spike", dir=str(folder), engines=["fake"], out=str(out))
    report = out.read_text(encoding="utf-8")
    assert "| fake | 1 |" in report and "| 0.0% |" in report
    assert "| fake | older speaker | 0.0% |" in report
