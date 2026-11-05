/** Live guided interviews: REST calls, the audio socket and microphone capture. */
import { request, type Message } from "./api";

export type SessionStatus = "ready" | "recording" | "paused" | "interrupted" | "ended";
export type NoteKind = "person" | "place" | "date" | "question";
export type NoteStatus = "open" | "answered" | "dismissed";

export interface TranscriptLine {
  line: number;
  text: string;
  speaker: string;
  start_ms: number;
  end_ms: number;
}

export interface InterviewNote {
  id: string;
  kind: NoteKind;
  text: string;
  detail: string;
  lines: number[];
  status: NoteStatus;
}

export interface InterviewSession {
  id: string;
  chat_id: string;
  narrator: string;
  interviewer: string;
  status: SessionStatus;
  consent_confirmed_at: string;
  consent_notice: string;
  duration_ms: number;
  has_audio: boolean;
  audio_sha256: string;
  speech_engine: string;
  sent: boolean;
  created_at: string;
  segments?: (TranscriptLine & { engine: string })[];
  notes?: InterviewNote[];
}

export interface FinishResult {
  session: InterviewSession;
  messages: Message[];
  response_error: string | null;
}

export const interviewApi = {
  notice: () => request<{ notice: string }>("GET", "/api/v1/interviews/notice"),
  start: (chatId: string, narrator: string, interviewer: string, consent: boolean) =>
    request<InterviewSession>("POST", `/api/v1/chats/${chatId}/interviews`, {
      narrator,
      interviewer,
      consent,
    }),
  get: (id: string) => request<InterviewSession>("GET", `/api/v1/interviews/${id}`),
  finish: (id: string) => request<FinishResult>("POST", `/api/v1/interviews/${id}/finish`),
  setSpeaker: (id: string, line: number, speaker: string) =>
    request<{ line: number; speaker: string }>("PATCH", `/api/v1/interviews/${id}/lines/${line}`, {
      speaker,
    }),
  setNoteStatus: (noteId: string, status: NoteStatus) =>
    request<{ id: string; status: NoteStatus }>("PATCH", `/api/v1/interview-notes/${noteId}`, {
      status,
    }),
  audioUrl: (id: string) => `/api/v1/interviews/${id}/audio`,
};

export type ServerEvent =
  | { type: "ready"; engine: string }
  | { type: "partial"; text: string; start_ms: number }
  | ({ type: "line" } & TranscriptLine)
  | { type: "notes"; items: InterviewNote[] }
  | { type: "notice"; text: string }
  | { type: "paused" }
  | { type: "resumed" }
  | { type: "ended"; duration_ms: number; lines: number }
  | { type: "error"; text: string };

export function socketUrl(sessionId: string): string {
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${window.location.host}/ws/interviews/${sessionId}`;
}

export interface Capture {
  stop: () => void;
}

export class MicrophoneError extends Error {}

/** Start the microphone. `onChunk` receives 16 kHz mono 16-bit PCM about every 100 ms. */
export async function startCapture(onChunk: (pcm: ArrayBuffer) => void): Promise<Capture> {
  if (!navigator.mediaDevices?.getUserMedia || typeof AudioWorkletNode === "undefined") {
    throw new MicrophoneError(
      "This browser can't record audio. Try a recent Chrome, Edge, Firefox or Safari.",
    );
  }
  let stream: MediaStream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
    });
  } catch (e) {
    const name = (e as DOMException).name;
    throw new MicrophoneError(
      name === "NotAllowedError"
        ? "Microphone access was blocked. Allow it in your browser's address bar, then try again."
        : name === "NotFoundError"
          ? "No microphone was found. Plug one in and try again."
          : "The microphone couldn't be started.",
    );
  }
  const context = new AudioContext();
  await context.audioWorklet.addModule("/worklets/pcm-capture.js");
  const source = context.createMediaStreamSource(stream);
  const node = new AudioWorkletNode(context, "pcm-capture");
  node.port.onmessage = (e: MessageEvent<ArrayBuffer>) => onChunk(e.data);
  source.connect(node);
  return {
    stop: () => {
      node.port.onmessage = null;
      source.disconnect();
      node.disconnect();
      stream.getTracks().forEach((t) => t.stop());
      void context.close();
    },
  };
}

export function formatTime(ms: number): string {
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
