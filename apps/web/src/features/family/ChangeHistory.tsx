/** Bulk changes to the tree (imports, updates, merges, deletions), each undoable in one step. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError } from "../../lib/api";
import { treeApi, type Change } from "../../lib/tree";

const KIND: Record<Change["kind"], string> = {
  import: "Import",
  update: "Update",
  merge: "Merge",
  delete: "Removal",
};

export function ChangeHistory({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();
  const changes = useQuery({
    queryKey: ["changes", projectId],
    queryFn: () => treeApi.changes(projectId),
    enabled: open,
  });
  const undo = useMutation({
    mutationFn: (id: string) => treeApi.undo(projectId, id),
    onSettled: () => {
      for (const key of ["changes", "people", "tree-graph", "tree-health", "lifeline", "trees"])
        qc.invalidateQueries({ queryKey: [key, projectId] });
      qc.invalidateQueries({ queryKey: ["people"] });
    },
  });

  if (!open)
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="min-h-11 cursor-pointer self-start rounded-lg border border-control bg-surface px-3"
      >
        Changes and undo
      </button>
    );

  return (
    <section
      aria-label="Changes to this tree"
      className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-3"
    >
      <div className="flex items-center justify-between">
        <h2 className="m-0 text-lg font-semibold">Changes to this tree</h2>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="min-h-11 cursor-pointer border-0 bg-transparent px-2 text-muted"
        >
          Close
        </button>
      </div>
      <p className="m-0 text-sm text-muted">
        Each import, update, merge or removal can be undone in one step, newest first.
      </p>
      {changes.isPending && <p className="m-0 text-muted">Loading…</p>}
      {changes.data?.length === 0 && <p className="m-0">No changes yet.</p>}
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {changes.data?.map((c) => (
          <li key={c.id} className="flex flex-col gap-1 border-t border-line-soft pt-2 text-sm">
            <div>
              <strong>{KIND[c.kind]}</strong>: {c.summary}
              <span className="text-muted">
                {" "}
                · {new Date(c.created_at).toLocaleDateString("en-GB")}
                {c.by ? ` by ${c.by}` : ""}
              </span>
            </div>
            {c.undone_at ? (
              <span className="text-muted">
                Undone {new Date(c.undone_at).toLocaleDateString("en-GB")}
              </span>
            ) : c.blocked.length ? (
              <span className="text-muted">Can&apos;t be undone yet: {c.blocked.join(" ")}</span>
            ) : (
              <button
                type="button"
                onClick={() => undo.mutate(c.id)}
                disabled={undo.isPending}
                className="min-h-11 cursor-pointer self-start rounded-lg border border-control bg-surface px-3"
              >
                Undo this {KIND[c.kind].toLowerCase()}
              </button>
            )}
          </li>
        ))}
      </ul>
      {undo.isError && (
        <p className="m-0 text-warning">
          {undo.error instanceof ApiError ? undo.error.message : "That couldn't be undone."}
        </p>
      )}
    </section>
  );
}
