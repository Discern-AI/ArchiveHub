/** The evidence behind one answer, and a way to back it with something saved. */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api, request } from "../../lib/api";

export interface EvidenceItem {
  title: string;
  url: string;
  what_it_says: string;
  source?: string;
  stance?: string;
}

export function AnswerEvidence({
  projectId,
  personId,
  claimId,
  evidence,
}: {
  projectId: string;
  personId: string;
  claimId: string;
  evidence: EvidenceItem[];
}) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [choice, setChoice] = useState("");
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const basket = useQuery({
    queryKey: ["basket", projectId],
    queryFn: () => api.basket(projectId),
    enabled: open,
  });

  async function attach() {
    if (!choice) return;
    try {
      await request("POST", `/api/v1/projects/${projectId}/claims/${claimId}/evidence`, {
        basket_item_id: choice,
        note,
        stance: "supports",
      });
      setOpen(false);
      setChoice("");
      setNote("");
      setMsg(null);
      await qc.invalidateQueries({ queryKey: ["person", projectId, personId] });
    } catch (err) {
      setMsg((err as Error).message);
    }
  }

  return (
    <div className="mt-0.5 flex flex-col gap-1 text-sm font-normal">
      {evidence.length > 0 && (
        <ul aria-label="Evidence" className="m-0 flex flex-col gap-0.5 pl-4">
          {evidence.map((e, i) => (
            <li key={i} className="text-muted">
              {e.url ? (
                <a href={e.url} target="_blank" rel="noreferrer">
                  {e.title} ↗
                </a>
              ) : (
                e.title
              )}
              {e.what_it_says && <span>: {e.what_it_says}</span>}
            </li>
          ))}
        </ul>
      )}
      {!open ? (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="cursor-pointer self-start border-0 bg-transparent p-0 text-accent"
        >
          Back this with a saved find
        </button>
      ) : (
        <div className="flex flex-col gap-1 rounded-lg bg-tint p-2">
          {basket.data?.length === 0 ? (
            <span>
              Nothing saved yet. Save a record from Search, the map or the Explorer first.
            </span>
          ) : (
            <>
              <label className="flex flex-col gap-1">
                Saved find
                <select
                  value={choice}
                  onChange={(e) => setChoice(e.target.value)}
                  className="min-h-11 rounded-lg border border-control bg-surface px-2"
                >
                  <option value="">Choose…</option>
                  {basket.data?.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.title}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1">
                What it says (optional)
                <input
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  className="min-h-11 rounded-lg border border-control bg-surface px-2"
                />
              </label>
              <button
                type="button"
                onClick={attach}
                disabled={!choice}
                className="min-h-11 cursor-pointer self-start rounded-lg border-0 bg-accent px-3 font-medium text-white disabled:opacity-50"
              >
                Add as evidence
              </button>
            </>
          )}
          {msg && <span className="text-warning">{msg}</span>}
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="cursor-pointer self-start border-0 bg-transparent p-0 text-accent"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
