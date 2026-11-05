import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";
import { api, type Message } from "../../lib/api";
import { streamReply } from "../../lib/chat";
import { Composer } from "./Composer";
import { MessageList } from "./MessageList";
import { StarterPrompts } from "./StarterPrompts";
import { WorkspacePanel } from "./WorkspacePanel";

let tempCounter = 0;
const tempId = () => `temp-${++tempCounter}`;

export function ChatPage() {
  const { chatId } = useParams();
  const [searchParams] = useSearchParams();
  const projectId = searchParams.get("project");
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [activity, setActivity] = useState<string | null>(null);
  // The chat this page created itself: its messages are already in state, so don't reload.
  const [createdId, setCreatedId] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  const ownChat = !!chatId && chatId === createdId;
  const history = useQuery({
    queryKey: ["messages", chatId],
    queryFn: () => api.messages(chatId!),
    enabled: !!chatId && !ownChat,
  });

  // Switching to another chat (or "New chat") resets the view.
  const [shownChat, setShownChat] = useState(chatId);
  if (shownChat !== chatId) {
    setShownChat(chatId);
    if (!ownChat) {
      setMessages([]);
      setError(null);
      setCreatedId(null);
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

  const update = (id: string, patch: Partial<Message>) =>
    setMessages((ms) => ms.map((m) => (m.id === id ? { ...m, ...patch } : m)));

  async function send(text: string) {
    if (busy) return;
    setBusy(true);
    setError(null);
    const userTemp = tempId();
    let replyId = tempId();
    const now = new Date().toISOString();
    setMessages((ms) => [
      ...ms,
      { id: userTemp, role: "user", content: text, status: "complete", created_at: now },
      { id: replyId, role: "assistant", content: "", status: "streaming", created_at: now },
    ]);

    try {
      let id = chatId;
      if (!id) {
        const chat = await api.createChat(projectId);
        id = chat.id;
        setCreatedId(id);
        navigate(`/chat/${id}`, { replace: true });
      }
      abort.current = new AbortController();
      let soFar = "";
      for await (const ev of streamReply(id, text, abort.current.signal)) {
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

  const loading = !!chatId && !ownChat && history.isPending;
  const showStarters = messages.length === 0 && !loading && !history.isError;

  return (
    <div className="flex min-h-0 flex-1">
      <div className="flex min-w-0 flex-1 flex-col px-4 pt-6 sm:px-12">
        <div className="mx-auto flex w-full max-w-[760px] justify-end">
          <button
            type="button"
            aria-expanded={panelOpen}
            aria-controls="workspace-panel"
            onClick={() => setPanelOpen(!panelOpen)}
            className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3 text-sm font-medium"
          >
            {panelOpen ? "Hide workspace" : "Show workspace"}
          </button>
        </div>

        {loading && <p className="mx-auto text-muted">Loading conversation…</p>}
        {history.isError && (
          <p className="mx-auto text-warning">Couldn't load this conversation.</p>
        )}
        {showStarters && <StarterPrompts onPick={send} />}
        {messages.length > 0 && <MessageList messages={messages} activity={activity} />}
        <div ref={bottom} />

        <div className="sticky bottom-0 mt-auto bg-page pt-3 pb-4">
          {error && (
            <p role="alert" className="mx-auto mb-2 max-w-[760px] text-sm font-medium text-warning">
              {error}
            </p>
          )}
          <Composer onSend={send} busy={busy} />
        </div>
      </div>
      {panelOpen && <WorkspacePanel onClose={() => setPanelOpen(false)} />}
    </div>
  );
}
