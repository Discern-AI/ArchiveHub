import type { InterviewNote, NoteKind } from "../../lib/interview";

const GROUPS: [NoteKind, string][] = [
  ["person", "People"],
  ["place", "Places"],
  ["date", "Dates"],
];

function LineLinks({ lines, sessionId }: { lines: number[]; sessionId: string | null }) {
  if (!sessionId) return null;
  return (
    <span className="text-[13px] text-muted">
      {" "}
      (
      {lines.map((n, i) => (
        <span key={n}>
          {i > 0 && ", "}
          <a href={`/interviews/${sessionId}#line-${n}`} target="_blank" rel="noreferrer">
            line {n}
          </a>
        </span>
      ))}
      )
    </span>
  );
}

/**
 * Questions and what the assistant picked up during the interview. Questions are only
 * offered here; the speaker is never interrupted.
 */
export function InterviewTab({
  notes,
  sessionId,
  onStatus,
}: {
  notes: InterviewNote[];
  sessionId: string | null;
  onStatus: (note: InterviewNote, status: InterviewNote["status"]) => void;
}) {
  const questions = notes.filter((n) => n.kind === "question" && n.status === "open");
  const answered = notes.filter((n) => n.kind === "question" && n.status === "answered");

  return (
    <div className="flex flex-col gap-5">
      <section className="flex flex-col gap-2">
        <h3 className="m-0 text-base font-semibold">Questions you could ask</h3>
        {questions.length === 0 && (
          <p className="m-0 text-sm text-muted">
            Suggestions appear here as the conversation goes on. Answer them, ignore them or pause
            whenever you like.
          </p>
        )}
        <ul className="m-0 flex list-none flex-col gap-2 p-0">
          {questions.map((q) => (
            <li key={q.id} className="ah-appear rounded-lg bg-tint p-3">
              <p className="m-0">{q.text}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => onStatus(q, "answered")}
                  className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3 text-sm"
                >
                  Asked it
                </button>
                <button
                  type="button"
                  onClick={() => onStatus(q, "dismissed")}
                  className="min-h-11 cursor-pointer rounded-lg border-0 bg-transparent px-3 text-sm text-accent"
                >
                  Not now
                </button>
              </div>
            </li>
          ))}
        </ul>
        {answered.length > 0 && (
          <p className="m-0 text-sm text-muted">{answered.length} asked so far.</p>
        )}
      </section>

      {GROUPS.map(([kind, label]) => {
        const items = notes.filter((n) => n.kind === kind && n.status !== "dismissed");
        return (
          <section key={kind} className="flex flex-col gap-1">
            <h3 className="m-0 text-base font-semibold">{label}</h3>
            {items.length === 0 ? (
              <p className="m-0 text-sm text-muted">None picked up yet.</p>
            ) : (
              <ul className="m-0 flex list-disc flex-col gap-1 pl-5">
                {items.map((n) => (
                  <li key={n.id}>
                    {n.text}
                    {n.detail && <span className="text-muted">: {n.detail}</span>}
                    <LineLinks lines={n.lines} sessionId={sessionId} />
                  </li>
                ))}
              </ul>
            )}
          </section>
        );
      })}
      <p className="m-0 text-[13px] text-muted">
        Picked up by the assistant from the transcript. Speech recognition can mishear names, so
        check them against the recording.
      </p>
    </div>
  );
}
