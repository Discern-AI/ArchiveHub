/** Save a record from any source into a project's Research Basket. */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../lib/api";

export function SaveToProject({ connector, recordId }: { connector: string; recordId: string }) {
  const qc = useQueryClient();
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const [projectId, setProjectId] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const list = projects.data ?? [];
  if (list.length === 0) return null;
  const chosen = projectId || list[0].id;
  const title = list.find((p) => p.id === chosen)?.title ?? "the project";

  async function save() {
    setBusy(true);
    try {
      await api.addToBasket(chosen, connector, recordId);
      await qc.invalidateQueries({ queryKey: ["basket", chosen] });
      setMessage(`Saved to ${title}.`);
    } catch (err) {
      setMessage((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <span className="inline-flex flex-wrap items-center gap-2 text-sm">
      {list.length > 1 && (
        <select
          aria-label="Project to save to"
          value={chosen}
          onChange={(e) => {
            setProjectId(e.target.value);
            setMessage(null);
          }}
          className="min-h-9 rounded-lg border border-control bg-surface px-1"
        >
          {list.map((p) => (
            <option key={p.id} value={p.id}>
              {p.title}
            </option>
          ))}
        </select>
      )}
      <button
        type="button"
        onClick={save}
        disabled={busy}
        className="min-h-9 cursor-pointer rounded-lg border border-control bg-surface px-2 font-medium disabled:opacity-60"
      >
        {list.length > 1 ? "Save" : `Save to ${title}`}
      </button>
      {message && <span role="status">{message}</span>}
    </span>
  );
}
