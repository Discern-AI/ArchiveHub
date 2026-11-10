# WP5 — Live guided interview

**Gate (SPEC §12):** five real interviews are completed and people want to continue.

**Status (5 Nov 2026):** built and tested, including end-to-end runs on the real servers: real speech recognition (faster-whisper) through the Vite proxy and WebSocket, with the original recording checked byte for byte. **The gate needs people:** five real interviews with older relatives or volunteers, with their consent. The speech spike also still needs real recordings (below).

## What was built

- **Start** (microphone button in any chat): who is being interviewed, who is asking (optional), the recording notice, and a consent checkbox. The server records who confirmed consent, when, and the exact notice shown.
- **Live bar:** words appear as they're spoken (provisional), with a recording timer, Pause/Resume and **End and send**. Each finished line lifts out of the bar and fades as it rises, while the same line settles into the chat. With reduced motion, lines simply appear.
- **Side panel → Interview tab:** questions you could ask (answer them with "Asked it", ignore them, or "Not now"), plus the people, places and dates picked up, each linked to its transcript lines. Prompts never appear over the speaker or in the chat.
- **Server** (`services/api/interviews`): a Channels WebSocket takes 16 kHz PCM from an AudioWorklet. A pause detector splits speech into lines, each line is transcribed, and every byte is kept in a WAV original with a SHA-256. Nothing is recorded or sent while paused. If the connection drops, the recording is kept and can still be sent. Audio arriving faster than real time is refused.
- **Background notes:** after each line, Claude picks up people, places, dates and up to two gentle follow-up questions, as structured output. Items must cite real lines, and duplicates are dropped. If notes fail (e.g. no API credit), a notice says so and the transcript carries on.
- **End and send:** the transcript goes into the chat (and is replayed to the assistant later as marked data), followed by a response with a short summary citing lines and "Questions for next time". Line citations are built by the server and link to the interview page. If the response fails, it isn't saved; the transcript is, and "Send what was recorded" retries.
- **Interview page** (`/interviews/:id`): the original recording with a player, the full transcript with "play from here" for each line, speaker names you can correct, the consent record, and the assistant's notes marked as interpretation.

## Speech spike (SPEC §8: accuracy, delay and cost; British accents; older speakers)

```bash
cd services/api
pip install -r requirements-speech.txt
python manage.py speech_spike --dir var/speech-spike \
    --engine whisper:base.en --engine whisper:small.en --engine whisper:medium.en \
    --out var/speech-spike/report.md
```

Put recordings in `var/speech-spike/` (git-ignored, never committed): `name.wav` (or mp3/m4a) plus a hand-checked `name.txt`. Add `manifest.csv` with `file,group` (e.g. `gran.wav,older speaker / Berkshire`) to get results by group. Recordings go through the same line splitting as a live interview. The report gives word error rate (WER), how long each line takes to appear, speed, and cost per audio hour (`--price engine=0.006` for a hosted engine's £ per minute).

**What's needed:** about ten consented 2–5 minute recordings, with at least half from speakers over 70 and a mix of local accents, each with a careful transcript. A hosted engine can be added to the adapter if `small.en` or `medium.en` isn't good enough on them.

**Synthetic check only so far** (Windows text-to-speech, 16 s, one voice; *not* evidence about real speakers):

| Engine | WER | Line delay (incl. 0.8 s pause) |
|---|---|---|
| whisper base.en | 3.7% ("Newberry") | ~1.8 s |
| whisper small.en | 0.0% | ~3.5 s |

In the live end-to-end run on the same laptop, live words trailed speech by about 1–2 s and finished lines arrived about 4–5 s after a pause (ADR-028).

## Running it

- `pip install -r requirements-speech.txt`. Models download on first use (about 600 MB) and load while the consent notice is open.
- Run the API with **uvicorn** (it serves both HTTP and the WebSocket). Vite forwards `/ws`.
- Offline: `SPEECH_PROVIDER=fake` gives a scripted transcript; `ASSISTANT_PROVIDER=fake` gives simple notes.

## Known limits

- **No speaker separation:** every line is labelled with the narrator. Correct speakers on the interview page; automatic speaker separation can be evaluated later.
- **Notes and the closing response were checked against the real API** on 10 Nov 2026 with a synthetic three-line transcript: structured people, places, dates and questions citing real lines, and a response that noticed a possible inconsistency in the story. Still to see in a full live interview.
- **One transcription at a time per server process.** Fine for the pilot; a separate speech service or GPU is needed for many simultaneous interviews.
- Interview audio isn't listed in the Archive yet; it's on the interview page, linked from the chat.
- Credits for interviews are not yet counted (ADR-027). Duration and AI token use are recorded per interview for cost-per-interview figures.
- Not yet tested on real phones or Safari; AudioWorklet is supported in current versions of all major browsers.
