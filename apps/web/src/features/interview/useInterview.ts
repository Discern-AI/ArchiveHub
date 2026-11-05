import { useCallback, useEffect, useRef, useState } from "react";
import {
  interviewApi,
  MicrophoneError,
  socketUrl,
  startCapture,
  type Capture,
  type FinishResult,
  type InterviewNote,
  type InterviewSession,
  type ServerEvent,
  type TranscriptLine,
} from "../../lib/interview";

export type Phase =
  "idle" | "connecting" | "recording" | "paused" | "ending" | "sending" | "interrupted";

const BYTES_PER_MS = 32; // 16 kHz × 2 bytes

/**
 * One live interview: microphone → socket → live words, finished lines and notes.
 * "End and send" stops recording, waits for the last lines, then asks the server to put
 * the transcript and a response into the chat.
 */
export function useInterview(onSent: (result: FinishResult) => void) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [session, setSession] = useState<InterviewSession | null>(null);
  const [partial, setPartial] = useState("");
  const [lines, setLines] = useState<TranscriptLine[]>([]);
  const [notes, setNotes] = useState<InterviewNote[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);

  const ws = useRef<WebSocket | null>(null);
  const capture = useRef<Capture | null>(null);
  const phaseRef = useRef<Phase>("idle");
  const sent = useRef(0);
  const sessionRef = useRef<InterviewSession | null>(null);

  const go = useCallback((p: Phase) => {
    phaseRef.current = p;
    setPhase(p);
  }, []);

  const stopCapture = () => {
    capture.current?.stop();
    capture.current = null;
  };

  const finish = useCallback(async () => {
    const s = sessionRef.current;
    if (!s) return;
    go("sending");
    setError(null);
    try {
      const result = await interviewApi.finish(s.id);
      onSent(result);
      if (result.response_error) {
        // The transcript is in the chat; only the response failed. Offer a retry.
        setError(result.response_error);
        go("interrupted");
        return;
      }
      sessionRef.current = null;
      setSession(null);
      setLines([]);
      setPartial("");
      setNotice(null);
      go("idle");
    } catch (e) {
      setError((e as Error).message || "Couldn't send the interview. Try again.");
      go("interrupted");
    }
  }, [go, onSent]);

  const onEvent = useCallback(
    (ev: ServerEvent) => {
      switch (ev.type) {
        case "partial":
          setPartial(ev.text);
          break;
        case "line":
          setPartial("");
          setLines((ls) => [...ls, ev]);
          break;
        case "notes":
          setNotes((ns) => [...ns, ...ev.items]);
          break;
        case "notice":
          setNotice(ev.text);
          break;
        case "error":
          setError(ev.text);
          break;
        case "paused":
          go("paused");
          break;
        case "resumed":
          go("recording");
          break;
        default:
          break;
      }
    },
    [go],
  );

  const start = useCallback(
    async (chatId: string, narrator: string, interviewer: string) => {
      if (phaseRef.current !== "idle") return;
      go("connecting");
      setError(null);
      setNotice(null);
      setLines([]);
      setNotes([]);
      setPartial("");
      setElapsedMs(0);
      sent.current = 0;
      try {
        const s = await interviewApi.start(chatId, narrator, interviewer, true);
        sessionRef.current = s;
        setSession(s);
        const socket = new WebSocket(socketUrl(s.id));
        socket.binaryType = "arraybuffer";
        ws.current = socket;
        await new Promise<void>((resolve, reject) => {
          socket.onmessage = (m) => {
            const ev = JSON.parse(String(m.data)) as ServerEvent;
            if (ev.type === "ready") resolve();
            else if (ev.type === "error") reject(new Error(ev.text));
            else onEvent(ev);
          };
          socket.onclose = () => reject(new Error("Couldn't connect to the interview service."));
        });
        socket.onmessage = (m) => onEvent(JSON.parse(String(m.data)) as ServerEvent);
        socket.onclose = () => {
          stopCapture();
          ws.current = null;
          if (phaseRef.current === "ending") void finish();
          else if (phaseRef.current === "recording" || phaseRef.current === "paused") {
            setError("The connection dropped. Everything recorded so far is saved.");
            go("interrupted");
          }
        };
        capture.current = await startCapture((pcm) => {
          if (phaseRef.current !== "recording" || socket.readyState !== WebSocket.OPEN) return;
          socket.send(pcm);
          sent.current += pcm.byteLength;
          const ms = Math.floor(sent.current / BYTES_PER_MS / 1000) * 1000;
          setElapsedMs((prev) => (prev === ms ? prev : ms));
        });
        go("recording");
      } catch (e) {
        stopCapture();
        ws.current?.close();
        ws.current = null;
        setError(
          e instanceof MicrophoneError
            ? e.message
            : (e as Error).message || "The interview couldn't start.",
        );
        // A session that never recorded anything isn't worth sending.
        sessionRef.current = null;
        setSession(null);
        go("idle");
      }
    },
    [finish, go, onEvent],
  );

  const pause = useCallback(() => ws.current?.send(JSON.stringify({ type: "pause" })), []);
  const resume = useCallback(() => ws.current?.send(JSON.stringify({ type: "resume" })), []);

  const end = useCallback(() => {
    if (phaseRef.current !== "recording" && phaseRef.current !== "paused") return;
    stopCapture();
    go("ending");
    // The server transcribes the last lines, saves the recording, then closes.
    ws.current?.send(JSON.stringify({ type: "end" }));
  }, [go]);

  const setNoteStatus = useCallback(
    async (note: InterviewNote, status: InterviewNote["status"]) => {
      setNotes((ns) => ns.map((n) => (n.id === note.id ? { ...n, status } : n)));
      try {
        await interviewApi.setNoteStatus(note.id, status);
      } catch {
        setNotes((ns) => ns.map((n) => (n.id === note.id ? note : n)));
      }
    },
    [],
  );

  // Leaving the page stops the microphone; the server keeps what was recorded.
  useEffect(
    () => () => {
      capture.current?.stop();
      ws.current?.close();
    },
    [],
  );

  return {
    phase,
    session,
    partial,
    lines,
    notes,
    notice,
    error,
    elapsedMs,
    start,
    pause,
    resume,
    end,
    retrySend: finish,
    setNoteStatus,
    dismissError: () => setError(null),
    /** Close the bar without sending. The recording stays on the interview page. */
    reset: () => {
      sessionRef.current = null;
      setSession(null);
      setLines([]);
      setPartial("");
      setNotice(null);
      setError(null);
      go("idle");
    },
  };
}

export type Interview = ReturnType<typeof useInterview>;
