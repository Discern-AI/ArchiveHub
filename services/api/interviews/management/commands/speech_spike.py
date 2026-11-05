"""WP5 speech spike: compare transcribers on accuracy, delay and cost.

Put consented recordings in a folder: `name.wav` (or any format ffmpeg reads, when
faster-whisper is installed) with a hand-checked `name.txt` transcript beside each. An
optional `manifest.csv` with columns `file,group` (e.g. "older speaker, Berkshire") breaks
results down by group. Recordings go through the same pipeline as a live interview: split
into lines at pauses, then each line transcribed.

    python manage.py speech_spike --dir var/speech-spike --engine whisper:base.en
        --engine whisper:small.en --out var/speech-spike/report.md
"""

from __future__ import annotations

import csv
import statistics
import time
import wave
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from interviews.audio import END_SILENCE_MS, FRAME_BYTES, SAMPLE_RATE, Segmenter, Utterance
from interviews.speech import FakeSpeech, SpeechUnavailable, WhisperProvider
from interviews.wer import word_errors

AUDIO = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"}


def load_pcm(path: Path) -> bytes:
    """16 kHz mono 16-bit PCM, as the browser sends it."""
    if path.suffix.lower() == ".wav":
        with wave.open(str(path), "rb") as w:
            if (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (SAMPLE_RATE, 1, 2):
                return w.readframes(w.getnframes())
    try:
        import numpy as np
        from faster_whisper import decode_audio
    except ImportError as exc:
        raise CommandError(
            f"{path.name} isn't 16 kHz mono WAV; install requirements-speech.txt to convert it."
        ) from exc
    audio = decode_audio(str(path), sampling_rate=SAMPLE_RATE)
    return (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()


def make_engine(spec: str):
    kind, _, model = spec.partition(":")
    if kind == "fake":
        return FakeSpeech()
    if kind == "whisper":
        return WhisperProvider(model or "small.en", "cpu", "int8")
    raise CommandError(f"Unknown engine '{spec}'. Use whisper:<model> or fake.")


def run(engine, pcm: bytes) -> tuple[str, list[float]]:
    """Transcribe line by line. Returns the text and each line's delay in seconds (pause
    detection plus transcription): what the speaker waits before a line appears."""
    seg = Segmenter()
    lines: list[Utterance] = []
    step = FRAME_BYTES * 10
    for i in range(0, len(pcm), step):
        lines += [e for e in seg.feed(pcm[i : i + step]) if isinstance(e, Utterance)]
    last = seg.flush()
    if last:
        lines.append(last)
    texts: list[str] = []
    delays: list[float] = []
    for u in lines:
        started = time.perf_counter()
        text = engine.transcribe(u.pcm, True, " ".join(texts[-3:])).text
        delays.append(END_SILENCE_MS / 1000 + time.perf_counter() - started)
        if text:
            texts.append(text)
    return " ".join(texts), delays


def build_report(rows: list[dict], prices: dict[str, str]) -> str:
    out = [
        "# Speech spike results",
        "",
        "| Engine | Files | Audio (min) | WER | Line delay median / p90 (s) "
        "| Speed (x real time) | Cost per audio hour |",
        "|---|---|---|---|---|---|---|",
    ]
    by_engine: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_engine[r["engine"]].append(r)
    for spec, rs in by_engine.items():
        errors, words = sum(r["errors"] for r in rs), sum(r["words"] for r in rs)
        delays = sorted(d for r in rs for d in r["delays"]) or [0.0]
        p90 = delays[min(len(delays) - 1, int(len(delays) * 0.9))]
        seconds = sum(r["seconds"] for r in rs)
        took = sum(r["took"] for r in rs)
        speed = seconds / took if took else 0
        cost = (
            f"£{float(prices[spec]) * 60:.2f}"
            if spec in prices
            else "no per-minute charge (our server's time)"
        )
        out.append(
            f"| {spec} | {len(rs)} | {seconds / 60:.1f} | {errors / max(words, 1):.1%} "
            f"| {statistics.median(delays):.1f} / {p90:.1f} | {speed:.1f} | {cost} |"
        )
    grouped = [r for r in rows if r["group"]]
    if grouped:
        out += ["", "## By group", "", "| Engine | Group | WER |", "|---|---|---|"]
        acc: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
        for r in grouped:
            acc[(r["engine"], r["group"])][0] += r["errors"]
            acc[(r["engine"], r["group"])][1] += r["words"]
        for (spec, group), (e, w) in sorted(acc.items()):
            out.append(f"| {spec} | {group} | {e / max(w, 1):.1%} |")
    out += ["", "## Per file", "", "| Engine | File | WER | Transcript |", "|---|---|---|---|"]
    for r in rows:
        snippet = r["hypothesis"][:120].replace("|", "/")
        rate = r["errors"] / max(r["words"], 1)
        out.append(f"| {r['engine']} | {r['file']} | {rate:.1%} | {snippet} |")
    return "\n".join(out) + "\n"


class Command(BaseCommand):
    help = "Compare speech-to-text engines on consented test recordings (WP5 spike)."

    def add_arguments(self, parser):
        parser.add_argument("--dir", required=True)
        parser.add_argument("--engine", action="append", dest="engines")
        parser.add_argument(
            "--price",
            action="append",
            default=[],
            help="engine=pounds per audio minute, for hosted engines",
        )
        parser.add_argument("--out")

    def handle(self, *args, **opts):
        folder = Path(opts["dir"])
        if not folder.is_dir():
            raise CommandError(f"{folder} isn't a folder.")
        files = sorted(p for p in folder.iterdir() if p.suffix.lower() in AUDIO)
        pairs = [(p, p.with_suffix(".txt")) for p in files if p.with_suffix(".txt").exists()]
        if not pairs:
            raise CommandError(f"No recordings with matching .txt transcripts in {folder}.")
        groups: dict[str, str] = {}
        manifest = folder / "manifest.csv"
        if manifest.exists():
            with manifest.open(encoding="utf-8-sig", newline="") as fh:
                groups = {row["file"]: row.get("group", "") for row in csv.DictReader(fh)}
        prices = dict(p.split("=", 1) for p in opts["price"])

        rows = []
        for spec in opts["engines"] or ["whisper:small.en"]:
            engine = make_engine(spec)
            try:
                engine.warm_up()
            except SpeechUnavailable as exc:
                raise CommandError(str(exc)) from exc
            for audio_path, ref_path in pairs:
                pcm = load_pcm(audio_path)
                started = time.perf_counter()
                text, delays = run(engine, pcm)
                errors, words = word_errors(ref_path.read_text(encoding="utf-8"), text)
                rows.append(
                    {
                        "engine": spec,
                        "file": audio_path.name,
                        "group": groups.get(audio_path.name, ""),
                        "seconds": len(pcm) / (SAMPLE_RATE * 2),
                        "took": time.perf_counter() - started,
                        "errors": errors,
                        "words": words,
                        "delays": delays,
                        "hypothesis": text,
                    }
                )
                self.stdout.write(f"{spec}  {audio_path.name}: WER {errors / max(words, 1):.1%}")

        report = build_report(rows, prices)
        if opts["out"]:
            Path(opts["out"]).write_text(report, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Report written to {opts['out']}"))
        else:
            self.stdout.write(report)
