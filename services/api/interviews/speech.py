"""Speech-to-text adapter (ADR-028).

`transcribe(pcm, final, context)` turns 16 kHz mono PCM into text. Providers are blocking;
callers run them in a worker thread. "whisper" runs faster-whisper on our own server (the
recording never leaves it); "fake" is deterministic, for tests and offline work. A hosted
provider plugs in here once the speech spike (docs/WP5.md) justifies one.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from functools import cache
from typing import Protocol

from django.conf import settings

from .audio import SAMPLE_RATE


class SpeechUnavailable(Exception):
    """The transcriber can't run here (not installed, or the model couldn't load)."""


@dataclass
class Transcript:
    text: str
    engine: str


class SpeechProvider(Protocol):
    engine: str

    def warm_up(self) -> None: ...

    def transcribe(self, pcm: bytes, final: bool, context: str = "") -> Transcript: ...


class WhisperProvider:
    """faster-whisper (MIT) with a CTranslate2 model, loaded once per process."""

    def __init__(self, model: str, device: str, compute_type: str) -> None:
        self.model_name = model
        self.device = device
        self.compute_type = compute_type
        self.engine = f"faster-whisper {model}"
        self._model = None
        self._load_lock = threading.Lock()
        # One transcription at a time per process: the model already uses every core.
        self._run_lock = threading.Lock()

    def warm_up(self) -> None:
        with self._load_lock:
            if self._model is not None:
                return
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise SpeechUnavailable(
                    "Speech recognition isn't installed on this server "
                    "(pip install -r requirements-speech.txt)."
                ) from exc
            try:
                self._model = WhisperModel(
                    self.model_name, device=self.device, compute_type=self.compute_type
                )
            except Exception as exc:
                raise SpeechUnavailable(
                    f"The speech model '{self.model_name}' couldn't be loaded."
                ) from exc

    def transcribe(self, pcm: bytes, final: bool, context: str = "") -> Transcript:
        import numpy as np

        self.warm_up()
        audio = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        if audio.size < SAMPLE_RATE // 10:
            return Transcript("", self.engine)
        with self._run_lock:
            segments, _info = self._model.transcribe(
                audio,
                language="en",
                # Live words favour speed; finished lines get a wider search.
                beam_size=5 if final else 1,
                # Earlier lines help with names and spelling, but never carry over errors.
                initial_prompt=context[-400:] or None,
                condition_on_previous_text=False,
                vad_filter=False,
                without_timestamps=True,
            )
            text = " ".join(s.text.strip() for s in segments).strip()
        return Transcript(text, self.engine)


class FakeSpeech:
    """Deterministic: finished lines come from a script; live words are its first words."""

    engine = "fake"
    SCRIPT = [
        "I grew up on Cheap Street in Newbury.",
        "My grandmother Alice Marsh ran the bakery there from 1931.",
        "She used to say the market was busiest before the war.",
    ]

    def __init__(self) -> None:
        self.finals = 0

    def warm_up(self) -> None:
        return None

    def transcribe(self, pcm: bytes, final: bool, context: str = "") -> Transcript:
        line = self.SCRIPT[self.finals % len(self.SCRIPT)]
        if final:
            self.finals += 1
            return Transcript(line, self.engine)
        seconds = max(1, len(pcm) // (SAMPLE_RATE * 2))
        return Transcript(" ".join(line.split()[: seconds * 2]), self.engine)


@cache
def _whisper(model: str, device: str, compute_type: str) -> WhisperProvider:
    return WhisperProvider(model, device, compute_type)


def get_speech_providers() -> tuple[SpeechProvider, SpeechProvider]:
    """(finished lines, live words). Live words are provisional and must keep up with
    the speaker, so they can use a smaller, faster model; finished lines use the best one."""
    if settings.SPEECH_PROVIDER == "fake":
        fake = FakeSpeech()  # a fresh script per session
        return fake, fake
    if settings.SPEECH_PROVIDER == "whisper":
        device, compute = settings.SPEECH_DEVICE, settings.SPEECH_COMPUTE_TYPE
        return (
            _whisper(settings.SPEECH_MODEL, device, compute),
            _whisper(settings.SPEECH_LIVE_MODEL, device, compute),
        )
    raise SpeechUnavailable(f"Unknown speech provider '{settings.SPEECH_PROVIDER}'.")


def warm_up_in_background() -> None:
    """Start loading the models while the user reads the consent notice."""

    def load() -> None:
        try:
            for provider in get_speech_providers():
                provider.warm_up()
        except SpeechUnavailable:
            pass  # reported properly when the interview connects

    threading.Thread(target=load, daemon=True).start()
