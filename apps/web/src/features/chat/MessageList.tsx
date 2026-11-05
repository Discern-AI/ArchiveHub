import { Link } from "react-router";
import type { Dispute, Message } from "../../lib/api";
import type { TranscriptLine } from "../../lib/interview";

const STATUS_NOTE: Partial<Record<Message["status"], string>> = {
  incomplete: "This reply was cut off before it finished.",
  refused: "The assistant declined to answer this.",
  error: "This reply didn't finish.",
};

function Checked({ items }: { items: NonNullable<Message["checked"]> }) {
  return (
    <div className="flex flex-col gap-1 rounded-lg bg-tint p-3 text-sm">
      <strong>What I checked</strong>
      {items.map((c, i) => (
        <div key={i}>
          <strong>{c.status}:</strong> {c.text}
        </div>
      ))}
    </div>
  );
}

function Sources({ items }: { items: NonNullable<Message["sources"]> }) {
  return (
    <div className="flex flex-col gap-1 text-[13px]">
      <span className="text-muted">Sources</span>
      <ol className="m-0 flex list-none flex-col gap-1 p-0">
        {items.map((s) => (
          <li key={s.n} className="flex gap-2">
            <span className="shrink-0 font-semibold text-muted">[{s.n}]</span>
            {s.url ? (
              <a href={s.url} target="_blank" rel="noreferrer">
                {s.label}
              </a>
            ) : (
              <span>{s.label}</span>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

export function MessageList({
  messages,
  activity,
  onCompare,
  liveLines,
}: {
  messages: Message[];
  /** Finished lines of an interview in progress; they settle here from the bottom bar. */
  liveLines?: TranscriptLine[];
  /** What the assistant is doing right now, e.g. "Searching records". */
  activity?: string | null;
  onCompare?: (d: Dispute) => void;
}) {
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
            {m.sources && m.sources.length > 0 && (
              <span className="mt-1 block text-[13px] text-muted">
                About:{" "}
                {m.sources.map((s, i) => (
                  <span key={s.n}>
                    {i > 0 && ", "}
                    {s.url?.startsWith("/") ? <Link to={s.url}>{s.label}</Link> : s.label}
                  </span>
                ))}
              </span>
            )}
          </div>
        ) : (
          <div key={m.id} className="flex flex-col gap-2.5">
            {(m.content || m.status !== "streaming") && (
              <div className="whitespace-pre-line">
                {m.content}
                {m.status === "streaming" && (
                  <span
                    aria-hidden="true"
                    className="ah-caret ml-0.5 inline-block h-5 w-0.5 bg-accent align-text-bottom"
                  />
                )}
              </div>
            )}
            {m.status === "streaming" && (
              <p role="status" className="m-0 text-sm text-muted">
                {activity ? `${activity}…` : m.content ? "" : "Thinking…"}
              </p>
            )}
            {m.disputes?.map((d) => (
              <div
                key={`${d.subject_id}:${d.predicate}`}
                className="flex flex-wrap items-center gap-2 rounded-lg border border-warning bg-surface p-2.5"
              >
                <span className="flex-1 text-sm">
                  <strong className="text-warning">Sources disagree</strong> on the {d.predicate} of{" "}
                  {d.subject}.
                </span>
                {onCompare && (
                  <button
                    type="button"
                    onClick={() => onCompare(d)}
                    className="min-h-11 cursor-pointer rounded-lg border border-warning bg-surface px-3 font-semibold text-warning"
                  >
                    Compare sources
                  </button>
                )}
              </div>
            ))}
            {m.checked && m.checked.length > 0 && <Checked items={m.checked} />}
            {m.sources && m.sources.length > 0 && <Sources items={m.sources} />}
            {STATUS_NOTE[m.status] && (
              <p className="m-0 text-sm font-medium text-warning">{STATUS_NOTE[m.status]}</p>
            )}
          </div>
        ),
      )}
      {liveLines && liveLines.length > 0 && (
        <div className="flex max-w-[80%] flex-col gap-1.5 self-end" aria-label="Interview so far">
          {liveLines.map((l) => (
            <p key={l.line} className="ah-settle m-0 rounded-xl bg-tint-strong px-3.5 py-2.5">
              <span className="sr-only">{l.speaker}: </span>
              {l.text}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
