import type { Message } from "../../lib/api";

const STATUS_NOTE: Partial<Record<Message["status"], string>> = {
  incomplete: "This reply was cut off before it finished.",
  refused: "The assistant declined to answer this.",
  error: "This reply didn't finish. Try sending your message again.",
};

export function MessageList({ messages }: { messages: Message[] }) {
  return (
    <div
      role="log"
      aria-live="polite"
      aria-label="Conversation"
      className="mx-auto flex w-full max-w-[760px] flex-col gap-5 pb-6"
    >
      {messages.map((m) =>
        m.role === "user" ? (
          <div
            key={m.id}
            className="ah-appear max-w-[80%] self-end rounded-xl bg-tint-strong px-3.5 py-2.5 whitespace-pre-line"
          >
            {m.content}
          </div>
        ) : (
          <div key={m.id} className="flex flex-col gap-2.5">
            <div className="whitespace-pre-line">
              {m.content}
              {m.status === "streaming" && (
                <span
                  aria-hidden="true"
                  className="ah-caret ml-0.5 inline-block h-5 w-0.5 bg-accent align-text-bottom"
                />
              )}
            </div>
            {m.status === "streaming" && !m.content && <span className="sr-only">Thinking…</span>}
            {STATUS_NOTE[m.status] && (
              <p className="m-0 text-sm font-medium text-warning">{STATUS_NOTE[m.status]}</p>
            )}
          </div>
        ),
      )}
    </div>
  );
}
