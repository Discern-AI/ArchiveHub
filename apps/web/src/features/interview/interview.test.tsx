import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../../app/routes";
import { installFetch, json } from "../../test/fakeServer";

// The microphone: tests push audio chunks by hand.
const mic = vi.hoisted(() => ({
  onChunk: null as ((pcm: ArrayBuffer) => void) | null,
  stopped: 0,
  fail: null as Error | null,
}));
vi.mock("../../lib/interview", async (importOriginal) => {
  const real = await importOriginal<typeof import("../../lib/interview")>();
  return {
    ...real,
    startCapture: vi.fn(async (onChunk: (pcm: ArrayBuffer) => void) => {
      if (mic.fail) throw mic.fail;
      mic.onChunk = onChunk;
      return { stop: () => (mic.stopped += 1) };
    }),
  };
});

class FakeSocket {
  static OPEN = 1;
  static last: FakeSocket | null = null;
  readyState = 1;
  binaryType = "blob";
  sent: (string | ArrayBuffer)[] = [];
  onmessage: ((m: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  constructor(public url: string) {
    FakeSocket.last = this;
    setTimeout(() => this.emit({ type: "ready", engine: "fake" }), 0);
  }
  send(data: string | ArrayBuffer) {
    this.sent.push(data);
    if (typeof data === "string" && JSON.parse(data).type === "end") {
      setTimeout(() => {
        this.emit({ type: "ended", duration_ms: 4000, lines: 1 });
        this.close();
      }, 0);
    }
  }
  close() {
    this.readyState = 3;
    this.onclose?.();
  }
  emit(ev: unknown) {
    this.onmessage?.({ data: JSON.stringify(ev) });
  }
}

const USER = { id: "u1", email: "alice@example.com", display: "alice" };
const CHAT = { id: "c1", project_id: null, title: "", created_at: "", updated_at: "" };
const SESSION = {
  id: "s1",
  chat_id: "c1",
  narrator: "Grandma Alice",
  interviewer: "",
  status: "ready",
  consent_confirmed_at: "2026-11-05T10:00:00Z",
  consent_notice: "This interview will be recorded.",
  duration_ms: 0,
  has_audio: false,
  audio_sha256: "",
  speech_engine: "",
  sent: false,
  created_at: "2026-11-05T10:00:00Z",
  segments: [],
  notes: [],
};
const NOTICE = { notice: "This interview will be recorded and transcribed." };

function routes(extra = {}) {
  return installFetch({
    "GET /_allauth/browser/v1/auth/session": () => json({ data: { user: USER } }),
    "GET /api/v1/projects": () => json([]),
    "GET /api/v1/chats": () => json([CHAT]),
    "GET /api/v1/chats/c1": () => json(CHAT),
    "GET /api/v1/chats/c1/messages": () => json([]),
    "GET /api/v1/interviews/notice": () => json(NOTICE),
    "POST /api/v1/chats/c1/interviews": () => json(SESSION, 201),
    "PATCH /api/v1/interview-notes/n2": () => json({ id: "n2", status: "answered" }),
    "POST /api/v1/interviews/s1/finish": () =>
      json({
        session: { ...SESSION, status: "ended", sent: true },
        messages: [
          {
            id: "m1",
            role: "user",
            content:
              "Interview with Grandma Alice (4 s)\n\n1. Grandma Alice: I grew up on Cheap Street.",
            status: "complete",
            created_at: "",
            sources: [{ n: 0, label: "Recording and transcript", url: "/interviews/s1" }],
          },
          {
            id: "m2",
            role: "assistant",
            content: "Thank you. You grew up on Cheap Street [1].",
            status: "complete",
            created_at: "",
            sources: [{ n: 1, label: "Line 1", url: "/interviews/s1#line-1" }],
          },
        ],
        response_error: null,
      }),
    ...extra,
  });
}

function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function openAndStart(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("button", { name: "Start a guided interview" }));
  const dialog = await screen.findByRole("dialog", { name: "Start a guided interview" });
  await within(dialog).findByText(NOTICE.notice);
  await user.type(within(dialog).getByLabelText("Who is being interviewed?"), "Grandma Alice");
  const start = within(dialog).getByRole("button", { name: "Start recording" });
  expect(start).toBeDisabled(); // consent not given yet
  await user.click(within(dialog).getByRole("checkbox"));
  await user.click(start);
}

beforeEach(() => {
  vi.stubGlobal("WebSocket", FakeSocket);
  mic.onChunk = null;
  mic.stopped = 0;
  mic.fail = null;
});
afterEach(() => vi.unstubAllGlobals());

describe("guided interview", () => {
  it("records with consent, shows live words and notes, then ends and sends", async () => {
    const user = userEvent.setup();
    const calls = routes();
    renderAt("/chat/c1");
    await openAndStart(user);

    const bar = await screen.findByRole("region", { name: "Interview" });
    await within(bar).findByText(/Recording 0:00/);
    expect(calls.find((c) => c.path === "/api/v1/chats/c1/interviews")?.body).toEqual({
      narrator: "Grandma Alice",
      interviewer: "",
      consent: true,
    });
    const socket = FakeSocket.last!;
    expect(socket.url).toMatch(/\/ws\/interviews\/s1$/);

    act(() => mic.onChunk!(new ArrayBuffer(3200)));
    expect(socket.sent).toHaveLength(1);

    act(() => socket.emit({ type: "partial", text: "I grew up", start_ms: 0 }));
    expect(within(bar).getByText("I grew up")).toBeInTheDocument();
    act(() =>
      socket.emit({
        type: "line",
        line: 1,
        text: "I grew up on Cheap Street.",
        speaker: "Grandma Alice",
        start_ms: 0,
        end_ms: 2000,
      }),
    );
    const log = screen.getByRole("log", { name: "Conversation" });
    expect(within(log).getByText("I grew up on Cheap Street.")).toBeInTheDocument();

    act(() =>
      socket.emit({
        type: "notes",
        items: [
          { id: "n1", kind: "place", text: "Cheap Street", detail: "", lines: [1], status: "open" },
          {
            id: "n2",
            kind: "question",
            text: "Which house was it?",
            detail: "",
            lines: [1],
            status: "open",
          },
        ],
      }),
    );
    const panel = screen.getByRole("complementary", { name: "Workspace" });
    expect(within(panel).getByRole("tab", { name: "Interview" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(within(panel).getByText("Cheap Street")).toBeInTheDocument();
    expect(within(panel).getByRole("link", { name: "line 1" })).toHaveAttribute(
      "href",
      "/interviews/s1#line-1",
    );
    await user.click(within(panel).getByRole("button", { name: "Asked it" }));
    expect(within(panel).queryByText("Which house was it?")).not.toBeInTheDocument();
    expect(calls.some((c) => c.method === "PATCH" && c.path === "/api/v1/interview-notes/n2")).toBe(
      true,
    );

    // Pausing stops audio leaving the browser.
    await user.click(within(bar).getByRole("button", { name: "Pause" }));
    act(() => socket.emit({ type: "paused" }));
    act(() => mic.onChunk!(new ArrayBuffer(3200)));
    expect(socket.sent.filter((d) => d instanceof ArrayBuffer)).toHaveLength(1);
    expect(within(bar).getByText(/Paused at/)).toBeInTheDocument();

    await user.click(within(bar).getByRole("button", { name: "End and send" }));
    expect(mic.stopped).toBe(1);
    await screen.findByText("Thank you. You grew up on Cheap Street [1].");
    expect(screen.queryByRole("region", { name: "Interview" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Recording and transcript" })).toHaveAttribute(
      "href",
      "/interviews/s1",
    );
    expect(screen.getByRole("textbox", { name: "Message ArchiveHub" })).toBeInTheDocument();
  });

  it("explains a blocked microphone and goes back to the composer", async () => {
    const user = userEvent.setup();
    const { MicrophoneError } = await import("../../lib/interview");
    mic.fail = new MicrophoneError("Microphone access was blocked.");
    routes();
    renderAt("/chat/c1");
    await openAndStart(user);
    expect(await screen.findByRole("alert")).toHaveTextContent("Microphone access was blocked.");
    expect(screen.getByRole("textbox", { name: "Message ArchiveHub" })).toBeInTheDocument();
  });

  it("keeps a dropped recording and offers to send it", async () => {
    const user = userEvent.setup();
    routes();
    renderAt("/chat/c1");
    await openAndStart(user);
    const bar = await screen.findByRole("region", { name: "Interview" });
    await within(bar).findByText(/Recording/);
    act(() => FakeSocket.last!.close());
    expect(await within(bar).findByRole("alert")).toHaveTextContent("Everything recorded so far");
    await user.click(within(bar).getByRole("button", { name: "Send what was recorded" }));
    await screen.findByText("Thank you. You grew up on Cheap Street [1].");
  });

  it("shows the recording, transcript lines and consent on the interview page", async () => {
    routes({
      "GET /api/v1/interviews/s1": () =>
        json({
          ...SESSION,
          status: "ended",
          has_audio: true,
          audio_sha256: "abcdef0123456789",
          speech_engine: "faster-whisper small.en",
          duration_ms: 65000,
          segments: [
            {
              line: 1,
              text: "I grew up on Cheap Street.",
              speaker: "Grandma Alice",
              start_ms: 12000,
              end_ms: 14000,
              engine: "faster-whisper small.en",
            },
          ],
        }),
      "PATCH /api/v1/interviews/s1/lines/1": () => json({ line: 1, speaker: "Interviewer" }),
    });
    renderAt("/interviews/s1#line-1");
    expect(
      await screen.findByRole("heading", { name: "Interview with Grandma Alice" }),
    ).toBeInTheDocument();
    expect(document.querySelector("audio")).toHaveAttribute("src", "/api/v1/interviews/s1/audio");
    expect(document.getElementById("line-1")).toHaveClass("bg-selected");
    expect(screen.getByRole("button", { name: "Play line 1 from 0:12" })).toBeInTheDocument();
    expect(screen.getByText(/Consent confirmed/)).toHaveTextContent(SESSION.consent_notice);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /Change speaker for line 1/ }));
    expect(screen.getByLabelText("Speaker for line 1")).toHaveValue("Grandma Alice");
  });
});

it("waits for the socket before recording", async () => {
  // Sanity check on the fake: "ready" arrives asynchronously.
  const s = new FakeSocket("ws://x");
  const got: string[] = [];
  s.onmessage = (m) => got.push(JSON.parse(m.data).type);
  await waitFor(() => expect(got).toEqual(["ready"]));
});
