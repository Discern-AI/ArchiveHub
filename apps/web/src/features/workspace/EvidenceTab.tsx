import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, type Dispute } from "../../lib/api";

const WEIGHT_BY: Record<string, string> = {
  editor: "suggested by an ArchiveHub editor",
  ai: "suggested by AI",
  user: "your own weighting",
};

export function EvidenceTab({
  dispute,
  projectId,
}: {
  dispute: Dispute | null;
  projectId: string | null;
}) {
  const qc = useQueryClient();
  const [full, setFull] = useState(false);
  const [reason, setReason] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  const evidence = useQuery({
    queryKey: ["evidence", dispute, projectId],
    queryFn: () => api.evidence(dispute!, projectId),
    enabled: !!dispute,
  });

  if (!dispute) {
    return (
      <p className="m-0 text-muted">
        When sources disagree, choose “Compare sources” under the assistant's answer to see them
        side by side here.
      </p>
    );
  }
  if (evidence.isPending) return <p className="m-0 text-muted">Loading the evidence…</p>;
  if (evidence.isError) {
    return (
      <p role="alert" className="m-0 text-warning">
        {(evidence.error as Error).message}
      </p>
    );
  }

  const e = evidence.data;
  const decision = e.decision;

  async function decide(choice: { chosen_id?: string; keep_disputed?: boolean }) {
    if (!projectId) return;
    try {
      await api.saveDecision(projectId, dispute!, { ...choice, reason });
      await qc.invalidateQueries({ queryKey: ["evidence", dispute, projectId] });
      setStatus(
        choice.keep_disputed
          ? "Saved: this stays marked as disputed. All sources stay on file."
          : "Saved for this project. All the other sources stay on file.",
      );
    } catch (err) {
      setStatus((err as Error).message);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="text-[13px] font-semibold text-warning uppercase">
        {e.disputed ? "Sources disagree" : "What the sources say"}
      </div>
      <h3 className="m-0 font-serif text-xl font-semibold">
        {e.predicate[0].toUpperCase() + e.predicate.slice(1)} of {e.subject.name}
      </h3>
      <p className="m-0 text-muted">
        {e.claims.length} different answers in the records. Different numbering over time could
        explain some of this; nothing here proves which is right.
      </p>

      <ul aria-label="Answers" className="m-0 flex list-none flex-col gap-2 p-0">
        {e.claims.map((c) => {
          const chosen = decision?.chosen_id === c.id;
          return (
            <li
              key={c.id}
              className={`flex flex-col gap-1.5 rounded-lg border p-3 ${chosen ? "border-accent bg-selected" : "border-line"}`}
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <strong className="text-lg">{c.value}</strong>
                <span className="text-[13px] text-muted">
                  {[
                    c.date,
                    c.status,
                    `${c.evidence.length} source${c.evidence.length === 1 ? "" : "s"}`,
                  ]
                    .filter(Boolean)
                    .join(" · ")}
                </span>
              </div>
              {c.note && <p className="m-0 text-sm text-muted">{c.note}</p>}
              {full &&
                c.evidence.map((ev) => (
                  <div key={ev.record_key} className="border-l-2 border-line pl-2 text-sm">
                    <a href={ev.url} target="_blank" rel="noreferrer">
                      {ev.record_title}
                    </a>
                    <div>{ev.what_it_says}</div>
                    {ev.suggested_weight && (
                      <div className="text-[13px] text-muted">
                        <strong>Suggested weight: {ev.suggested_weight}</strong>
                        {ev.weight_suggested_by &&
                          ` (${WEIGHT_BY[ev.weight_suggested_by] ?? ev.weight_suggested_by})`}
                      </div>
                    )}
                  </div>
                ))}
              {projectId && (
                <div>
                  <button
                    type="button"
                    aria-pressed={chosen}
                    onClick={() => decide({ chosen_id: c.id })}
                    className={`min-h-11 cursor-pointer rounded-lg border border-accent px-3 font-medium ${chosen ? "bg-accent text-white" : "bg-surface text-accent"}`}
                  >
                    {chosen ? "Used in this project" : `Use ${c.value}`}
                  </button>
                </div>
              )}
            </li>
          );
        })}
      </ul>

      <button
        type="button"
        aria-expanded={full}
        onClick={() => setFull(!full)}
        className="min-h-11 cursor-pointer self-start rounded-lg border-0 bg-transparent px-0 font-semibold text-accent"
      >
        {full ? "Hide the full comparison" : "Show the full comparison"}
      </button>

      {projectId ? (
        <fieldset className="m-0 flex flex-col gap-2 rounded-lg border border-line p-3">
          <legend className="px-1 font-semibold">What should your project use?</legend>
          <p className="m-0 text-[13px] text-muted">
            Choosing an answer means your project uses it. It doesn't make it true, and the other
            sources stay on file.
          </p>
          <label htmlFor="decision-reason" className="text-sm font-medium">
            Your reason (optional)
          </label>
          <textarea
            id="decision-reason"
            rows={2}
            value={reason}
            onChange={(ev) => setReason(ev.target.value)}
            className="rounded-lg border border-control p-2"
          />
          <button
            type="button"
            aria-pressed={!!decision?.keep_disputed}
            onClick={() => decide({ keep_disputed: true })}
            className="min-h-11 cursor-pointer self-start rounded-lg border border-control bg-surface px-3 font-medium"
          >
            {decision?.keep_disputed ? "Kept as disputed" : "Keep it disputed"}
          </button>
          {status && (
            <p role="status" className="m-0 text-sm font-medium text-accent">
              {status}
            </p>
          )}
        </fieldset>
      ) : (
        <p className="m-0 text-[13px] text-muted">
          To record which answer you use, start this chat from a project.
        </p>
      )}
    </div>
  );
}
