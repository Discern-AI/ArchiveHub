import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";
import { api, type Dispute, type Message } from "../../lib/api";
import { streamReply, type AttachedRecord } from "../../lib/chat";
import type { FinishResult } from "../../lib/interview";
import { InterviewBar } from "../interview/InterviewBar";
import { InterviewStartDialog } from "../interview/InterviewStartDialog";
import { useInterview } from "../interview/useInterview";
import { Composer } from "./Composer";
import { MessageList } from "./MessageList";
import { StarterPrompts } from "./StarterPrompts";
import { WorkspacePanel, type WorkspaceTab } from "./WorkspacePanel";

let tempCounter = 0;
const tempId = () => `temp-${++tempCounter}`;

export function ChatPage() {
  const { chatId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activity, setActivity] = useState<string | null>(null);
  const [panel, setPanel] = useState<WorkspaceTab | null>(null);
  const [dispute, setDispute] = useState<Dispute | null>(null);
  const [attached, setAttached] = useState<AttachedRecord | null>(null);
  // The chat this page created itself: its messages are already in state, so don't reload.
  const [createdId, setCreatedId] = useState<string | null>(null);
  const [startOpen, setStartOpen] = useState(false);
  const [starting, setStarting] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const currentChat = useRef(chatId);
  const bottom = useRef<HTMLDivElement>(null);

  const ownChat = !!chatId && chatId === createdId;
  const history = useQuery({
    queryKey: ["messages", chatId],
    queryFn: () => api.messages(chatId!),
    enabled: !!chatId && !ownChat,
  });
  const chat = useQuery({
    queryKey: ["chat", chatId],
    queryFn: () => api.chat(chatId!),
    enabled: !!chatId,
  });
  const projectId = chat.data?.project_id ?? (chatId ? null : searchParams.get("project"));

  // Switching to another chat (or "New chat") resets the view.
  const [shownChat, setShownChat] = useState(chatId);
  if (shownChat !== chatId) {
    setShownChat(chatId);
    if (!ownChat) {
      setMessages([]);
      setError(null);
      setCreatedId(null);
      setAttached(null);
      setDispute(null);
    }
  }
  // Show history once it arrives for a chat we didn't just create.
  const [loadedFrom, setLoadedFrom] = useState<Message[] | undefined>(undefined);
  if (!ownChat && history.data && loadedFrom !== history.data) {
    setLoadedFrom(history.data);
    setMessages(history.data);
  }

  // A reply still streaming belongs to the chat we left: stop it.
  useEffect(() => {
    if (!ownChat) abort.current?.abort();
  }, [chatId, ownChat]);
  useEffect(() => () => abort.current?.abort(), []);
  useEffect(() => {
    bottom.current?.scrollIntoView?.({ block: "end" });
  }, [messages]);

  useEffect(() => {
    currentChat.current = chatId;
  }, [chatId]);

  // "End and send" puts the transcript and response into the interview's chat.
  const onInterviewSent = useCallback(
    (result: FinishResult) => {
      if (result.session.chat_id === currentChat.current) {
        setMessages((ms) => {
          const known = new Set(ms.map((m) => m.id));
          return [...ms, ...result.messages.filter((m) => !known.has(m.id))];
        });
      }
      void qc.invalidateQueries({ queryKey: ["messages", result.session.chat_id] });
      void qc.invalidateQueries({ queryKey: ["chats"] });
    },
    [qc],
  );
  const interview = useInterview(onInterviewSent);
  const interviewing = interview.phase !== "idle";

  // Moving to another chat mid-interview ends it; everything recorded is kept and sent.
  const { end: endInterview, phase: interviewPhase, session: interviewSession } = interview;
  useEffect(() => {
    const live = interviewPhase === "recording" || interviewPhase === "paused";
    if (live && interviewSession && interviewSession.chat_id !== chatId) endInterview();
  }, [chatId, interviewPhase, interviewSession, endInterview]);

  async function ensureChat(): Promise<string> {
    if (chatId) return chatId;
    const created = await api.createChat(projectId);
    setCreatedId(created.id);
    qc.setQueryData(["chat", created.id], created);
    currentChat.current = created.id;
    navigate(`/chat/${created.id}`, { replace: true });
    return created.id;
  }

  async function beginInterview(narrator: string, interviewer: string) {
    setStarting(true);
    setError(null);
    try {
      const id = await ensureChat();
      setStartOpen(false);
      if (!window.matchMedia?.("(max-width: 767px)").matches) setPanel("interview");
      await interview.start(id, narrator, interviewer);
    } catch (e) {
      setError((e as Error).message || "The interview couldn't start.");
    } finally {
      setStarting(false);
    }
  }

  const update = (id: string, patch: Partial<Message>) =>
    setMessages((ms) => ms.map((m) => (m.id === id ? { ...m, ...patch } : m)));

  async function send(text: string) {
    if (busy) return;
    const record = attached;
    setBusy(true);
    setError(null);
    setAttached(null);
    const userTemp = tempId();
    let replyId = tempId();
    const now = new Date().toISOString();
    setMessages((ms) => [
      ...ms,
      { id: userTemp, role: "user", content: text, status: "complete", created_at: now },
      { id: replyId, role: "assistant", content: "", status: "streaming", created_at: now },
    ]);

    try {
      const id = await ensureChat();
      abort.current = new AbortController();
      let soFar = "";
      for await (const ev of streamReply(id, text, abort.current.signal, record)) {
        if (ev.type === "start") {
          update(userTemp, ev.userMessage);
          update(replyId, { id: ev.replyId });
          replyId = ev.replyId;
        } else if (ev.type === "delta") {
          soFar += ev.text;
          setActivity(null);
          update(replyId, { content: soFar });
        } else if (ev.type === "tool") {
          setActivity(ev.label);
        } else if (ev.type === "done") {
          update(replyId, ev.message);
        } else if (ev.type === "error") {
          update(replyId, ev.message ?? { status: "error" });
          setError(ev.detail);
        }
      }
      qc.invalidateQueries({ queryKey: ["chats"] });
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        update(replyId, { status: "error" });
        setError((e as Error).message || "Something went wrong.");
      }
    } finally {
      setBusy(false);
      setActivity(null);
    }
  }

  function compare(d: Dispute) {
    setDispute(d);
    setPanel("evidence");
  }

  function askAbout(record: AttachedRecord) {
    setAttached(record);
    // On phones the panel covers the chat; close it so the composer is visible.
    if (window.matchMedia?.("(max-width: 767px)").matches) setPanel(null);
    document.getElementById("composer")?.focus();
  }

  const loading = !!chatId && !ownChat && history.isPending;
  const showStarters = messages.length === 0 && !loading && !history.isError && !interviewing;
  const shownError = error ?? (interviewing ? null : interview.error);

  return (
    <div className="flex min-h-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col px-4 pt-6 sm:px-12">
        <div className="mx-auto flex w-full max-w-[760px] justify-end">
          <button
            type="button"
            aria-expanded={!!panel}
            aria-controls="workspace-panel"
            onClick={() => setPanel(panel ? null : "explorer")}
            className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3 text-sm font-medium"
          >
            {panel ? "Hide workspace" : "Open Explorer"}
          </button>
        </div>

        {loading && <p className="mx-auto text-muted">Loading conversation…</p>}
        {history.isError && (
          <p className="mx-auto text-warning">Couldn't load this conversation.</p>
        )}
        {showStarters && <StarterPrompts onPick={send} />}
        {(messages.length > 0 || interview.lines.length > 0) && (
          <MessageList
            messages={messages}
            activity={activity}
            onCompare={compare}
            liveLines={interviewing ? interview.lines : undefined}
          />
        )}
        <div ref={bottom} />

        <div className="sticky bottom-0 mt-auto bg-page pt-3 pb-4">
          {shownError && (
            <p role="alert" className="mx-auto mb-2 max-w-[760px] text-sm font-medium text-warning">
              {shownError}
            </p>
          )}
          {attached && (
            <div className="mx-auto mb-2 flex max-w-[760px] flex-wrap items-center gap-2 text-sm">
              <span className="rounded-full bg-tint-strong px-3 py-1">
                Asking about: <strong>{attached.title}</strong>
              </span>
              <button
                type="button"
                onClick={() => setAttached(null)}
                className="min-h-11 cursor-pointer rounded-lg border-0 bg-transparent px-2 text-accent"
              >
                Remove
              </button>
            </div>
          )}
          {interviewing ? (
            <InterviewBar interview={interview} />
          ) : (
            <Composer onSend={send} busy={busy} onInterview={() => setStartOpen(true)} />
          )}
        </div>
      </div>
      {panel && (
        <WorkspacePanel
          tab={panel}
          onTab={setPanel}
          onClose={() => setPanel(null)}
          projectId={projectId}
          dispute={dispute}
          onAsk={askAbout}
          interview={interview.session || interview.notes.length ? interview : null}
        />
      )}
      {startOpen && (
        <InterviewStartDialog
          busy={starting}
          onStart={(narrator, interviewer) => void beginInterview(narrator, interviewer)}
          onCancel={() => setStartOpen(false)}
        />
      )}
    </div>
  );
}
