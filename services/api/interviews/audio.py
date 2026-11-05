"""Audio for live interviews: 16 kHz mono 16-bit little-endian PCM from the browser.

`Segmenter` finds where someone stops speaking using signal energy, so each finished
utterance can be transcribed as one line. `Recorder` keeps every byte of the original in a
WAV file; nothing is dropped or altered.
"""

from __future__ import annotations

import hashlib
import math
import sys
import tempfile
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path

SAMPLE_RATE = 16_000
BYTES_PER_SAMPLE = 2
FRAME_MS = 30
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000  # 480
FRAME_BYTES = FRAME_SAMPLES * BYTES_PER_SAMPLE

START_FRAMES = 3  # 90 ms above the threshold starts speech
END_SILENCE_MS = 800  # a pause this long ends a line
MIN_SPEECH_MS = 400  # anything shorter is a click or a cough, not a line
MAX_LINE_MS = 20_000  # long unbroken speech is cut so the text keeps flowing
PRE_ROLL_MS = 300  # keep a little audio before speech starts so first syllables survive
PARTIAL_EVERY_MS = 1_000  # live words are refreshed this often while someone speaks
MIN_THRESHOLD = 350.0  # RMS on the 16-bit scale; quieter than this is never speech


def ms_to_bytes(ms: int) -> int:
    return ms * SAMPLE_RATE // 1000 * BYTES_PER_SAMPLE


def rms(frame: bytes) -> float:
    samples = array("h")
    samples.frombytes(frame)
    if sys.byteorder == "big":
        samples.byteswap()
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


@dataclass
class Partial:
    """Speech in progress: the audio so far, for live (provisional) words."""

    start_ms: int
    pcm: bytes


@dataclass
class Utterance:
    """A finished line."""

    start_ms: int
    end_ms: int
    pcm: bytes


class Segmenter:
    def __init__(self) -> None:
        self._pending = b""  # bytes not yet making up a whole frame
        self._pos_ms = 0  # position in the recording of the next frame
        self._noise = 200.0
        self._loud_run = 0
        self._recent: list[bytes] = []  # pre-roll frames while silent
        self._speech: list[bytes] | None = None
        self._speech_start = 0
        self._voice_start = 0
        self._silence_ms = 0
        self._last_partial_ms = 0

    @property
    def speaking(self) -> bool:
        return self._speech is not None

    def threshold(self) -> float:
        return max(MIN_THRESHOLD, self._noise * 3)

    def feed(self, pcm: bytes) -> list[Partial | Utterance]:
        data = self._pending + pcm
        whole = len(data) - len(data) % FRAME_BYTES
        self._pending = data[whole:]
        events: list[Partial | Utterance] = []
        for i in range(0, whole, FRAME_BYTES):
            event = self._frame(data[i : i + FRAME_BYTES])
            if event is not None:
                events.append(event)
        return events

    def flush(self) -> Utterance | None:
        """End of recording (or a pause): whatever is being said becomes a line."""
        if self._speech is None:
            return None
        return self._finish(trailing_silence_ms=self._silence_ms)

    def _frame(self, frame: bytes) -> Partial | Utterance | None:
        level = rms(frame)
        loud = level >= self.threshold()
        self._pos_ms += FRAME_MS

        if self._speech is None:
            if not loud:
                # Track background noise only while nobody is speaking.
                self._noise = 0.95 * self._noise + 0.05 * level
            self._recent.append(frame)
            keep = PRE_ROLL_MS // FRAME_MS + START_FRAMES
            del self._recent[:-keep]
            self._loud_run = self._loud_run + 1 if loud else 0
            if self._loud_run >= START_FRAMES:
                self._speech = list(self._recent)
                self._speech_start = self._pos_ms - len(self._speech) * FRAME_MS
                self._voice_start = self._pos_ms - START_FRAMES * FRAME_MS  # without pre-roll
                self._silence_ms = 0
                self._last_partial_ms = self._pos_ms
                self._recent = []
            return None

        self._speech.append(frame)
        self._silence_ms = 0 if loud else self._silence_ms + FRAME_MS
        length = self._pos_ms - self._speech_start
        if self._silence_ms >= END_SILENCE_MS or length >= MAX_LINE_MS:
            return self._finish(trailing_silence_ms=self._silence_ms)
        if self._pos_ms - self._last_partial_ms >= PARTIAL_EVERY_MS:
            self._last_partial_ms = self._pos_ms
            return Partial(self._speech_start, b"".join(self._speech))
        return None

    def _finish(self, trailing_silence_ms: int) -> Utterance | None:
        frames = self._speech or []
        self._speech = None
        self._loud_run = 0
        end = self._speech_start + len(frames) * FRAME_MS - trailing_silence_ms
        if end - self._voice_start < MIN_SPEECH_MS:
            return None
        cut = len(frames) - trailing_silence_ms // FRAME_MS
        return Utterance(self._speech_start, end, b"".join(frames[:cut]))


class Recorder:
    """Writes the original recording to a WAV file as it arrives."""

    def __init__(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(  # noqa: SIM115 - closed in close()
            dir=directory, suffix=".wav", delete=False
        )
        handle.close()
        self.path = Path(handle.name)
        self._wav = wave.open(str(self.path), "wb")  # noqa: SIM115 - closed in close()
        self._wav.setnchannels(1)
        self._wav.setsampwidth(BYTES_PER_SAMPLE)
        self._wav.setframerate(SAMPLE_RATE)
        self.bytes_written = 0
        self.closed = False

    @property
    def duration_ms(self) -> int:
        return self.bytes_written * 1000 // (SAMPLE_RATE * BYTES_PER_SAMPLE)

    def write(self, pcm: bytes) -> None:
        pcm = pcm[: len(pcm) - len(pcm) % BYTES_PER_SAMPLE]
        if not pcm or self.closed:
            return
        if sys.byteorder == "big":
            samples = array("h")
            samples.frombytes(pcm)
            samples.byteswap()
            pcm = samples.tobytes()
        self._wav.writeframes(pcm)
        self.bytes_written += len(pcm)

    def close(self) -> tuple[int, str]:
        """Finish the file. Returns its size and SHA-256."""
        if not self.closed:
            self._wav.close()
            self.closed = True
        digest = hashlib.sha256()
        with self.path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
        return self.path.stat().st_size, digest.hexdigest()
