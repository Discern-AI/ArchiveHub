import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { interviewApi } from "../../lib/interview";

const input = "min-h-11 rounded-lg border border-control bg-surface px-3 text-ink";

/** Before any recording: who is speaking, the recording notice and consent. */
export function InterviewStartDialog({
  onStart,
  onCancel,
  busy,
}: {
  onStart: (narrator: string, interviewer: string) => void;
  onCancel: () => void;
  busy: boolean;
}) {
  const notice = useQuery({ queryKey: ["interview-notice"], queryFn: interviewApi.notice });
  const [narrator, setNarrator] = useState("");
  const [interviewer, setInterviewer] = useState("");
  const [consent, setConsent] = useState(false);
  const first = useRef<HTMLInputElement>(null);

  useEffect(() => {
    first.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (narrator.trim() && consent && !busy) onStart(narrator.trim(), interviewer.trim());
  };

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
      <form
        role="dialog"
        aria-modal="true"
        aria-labelledby="interview-start-title"
        onSubmit={submit}
        className="flex w-full max-w-[480px] flex-col gap-4 rounded-xl bg-surface p-6 shadow-xl"
      >
        <h2 id="interview-start-title" className="m-0 font-serif text-2xl font-semibold">
          Start a guided interview
        </h2>
        <p className="m-0 text-muted">
          Talk naturally. Your words appear as you speak, and questions you might ask next appear at
          the side. They never interrupt.
        </p>
        <label className="flex flex-col gap-1 font-medium">
          Who is being interviewed?
          <input
            ref={first}
            value={narrator}
            onChange={(e) => setNarrator(e.target.value)}
            placeholder="For example, Grandma Alice"
            maxLength={120}
            required
            className={input}
          />
        </label>
        <label className="flex flex-col gap-1 font-medium">
          Who is asking the questions? <span className="font-normal text-muted">(optional)</span>
          <input
            value={interviewer}
            onChange={(e) => setInterviewer(e.target.value)}
            maxLength={120}
            className={input}
          />
        </label>
        <div className="rounded-lg border border-warning bg-tint p-3">
          <strong className="text-warning">Recording notice</strong>
          <p className="m-0 mt-1">{notice.data?.notice ?? "Loading the recording notice…"}</p>
        </div>
        <label className="flex items-start gap-3">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            disabled={!notice.data}
            className="mt-1 size-5 shrink-0"
          />
          <span>
            Everyone who will be speaking knows they're being recorded and is happy to be.
          </span>
        </label>
        <div className="flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-4"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!narrator.trim() || !consent || busy}
            className="min-h-11 cursor-pointer rounded-lg border-0 bg-live px-4 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "Starting…" : "Start recording"}
          </button>
        </div>
      </form>
    </div>
  );
}
