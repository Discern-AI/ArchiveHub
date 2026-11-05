import { useState, type KeyboardEvent } from "react";

const iconButton =
  "flex size-11 shrink-0 items-center justify-center rounded-lg bg-tint text-ink disabled:cursor-not-allowed disabled:opacity-50";

export function Composer({
  onSend,
  busy,
  onInterview,
}: {
  onSend: (text: string) => void;
  busy: boolean;
  /** Opens the guided interview. */
  onInterview?: () => void;
}) {
  const [text, setText] = useState("");

  const send = () => {
    const clean = text.trim();
    if (!clean || busy) return;
    onSend(clean);
    setText("");
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-[760px] items-end gap-1.5 rounded-xl border border-control bg-surface p-2">
      <label htmlFor="composer" className="sr-only">
        Message ArchiveHub
      </label>
      <textarea
        id="composer"
        rows={2}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask a question, tell a memory or say what you want written."
        className="min-w-0 flex-1 resize-none border-0 bg-transparent p-2 text-ink outline-none focus-visible:outline-none"
      />
      <button
        type="button"
        disabled
        aria-label="Attach a file (uploads arrive in a later version)"
        title="Uploads arrive in a later version"
        className={iconButton}
      >
        <svg
          aria-hidden="true"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 11.5l-8.6 8.6a5.5 5.5 0 0 1-7.8-7.8l9-9a3.7 3.7 0 0 1 5.2 5.2l-9 9a1.8 1.8 0 0 1-2.6-2.6l8.3-8.3" />
        </svg>
      </button>
      <button
        type="button"
        disabled={!onInterview || busy}
        onClick={onInterview}
        aria-label="Start a guided interview"
        title="Start a guided interview"
        className={`${iconButton} cursor-pointer`}
      >
        <svg
          aria-hidden="true"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="9" y="3" width="6" height="11" rx="3" />
          <path d="M5 11a7 7 0 0 0 14 0" />
          <path d="M12 18v3" />
        </svg>
      </button>
      <button
        type="button"
        aria-label="Send"
        onClick={send}
        disabled={busy || !text.trim()}
        className="flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-lg bg-accent text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        <svg
          aria-hidden="true"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 19V5" />
          <path d="M6 11l6-6 6 6" />
        </svg>
      </button>
    </div>
  );
}
