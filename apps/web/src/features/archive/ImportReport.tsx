/** What a GEDCOM import brought across, what it left behind, and a one-step undo. */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "../../lib/api";
import { treeApi } from "../../lib/tree";

export interface GedcomReport {
  gedcom_version: string;
  made_by: string;
  source_citations_not_imported: number;
  source_records_not_imported: number;
  notes_not_imported: number;
  media_references: number;
  media_files_named: number;
  media_note: string;
  other_facts_not_imported: Record<string, number>;
}

export function ImportReport({
  result,
  projectId,
  onUndone,
}: {
  result: Record<string, unknown>;
  projectId?: string;
  onUndone?: () => void;
}) {
  const qc = useQueryClient();
  const changeId = typeof result.change_set === "string" ? result.change_set : null;
  const undo = useMutation({
    mutationFn: () => treeApi.undo(projectId!, changeId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["trees", projectId] });
      qc.invalidateQueries({ queryKey: ["changes", projectId] });
      onUndone?.();
    },
  });
  const r = result.report as GedcomReport | undefined;
  if (!r) return null;
  const health = result.health as { count: number } | undefined;
  const left: string[] = [];
  if (r.source_citations_not_imported)
    left.push(`${r.source_citations_not_imported} source citations`);
  if (r.source_records_not_imported) left.push(`${r.source_records_not_imported} source records`);
  if (r.notes_not_imported) left.push(`${r.notes_not_imported} notes`);
  if (r.media_references) left.push(`${r.media_references} media references`);
  for (const [what, n] of Object.entries(r.other_facts_not_imported)) left.push(`${n} ${what}`);
  return (
    <section
      aria-label="Import report"
      className="flex flex-col gap-1 rounded-lg border border-line bg-surface p-3 text-sm"
    >
      <h3 className="m-0 text-base font-semibold">What came across</h3>
      <p className="m-0">
        {String(result.people)} people and {String(result.families)} families
        {r.made_by ? ` from ${r.made_by}` : ""}
        {r.gedcom_version ? ` (GEDCOM ${r.gedcom_version})` : ""}.{" "}
        {Number(result.living_private) > 0 &&
          `${String(result.living_private)} may be living, so they're kept private.`}
      </p>
      {left.length > 0 ? (
        <p className="m-0">
          <strong>Not brought in yet:</strong> {left.join(", ")}. They're still in the original
          file, which is kept unchanged.
        </p>
      ) : (
        <p className="m-0">Nothing was left out.</p>
      )}
      {result.mode === "update" && (
        <p className="m-0">
          Updated {String(result.updated)} people and added {String(result.added)}.{" "}
          {Number(result.not_in_file_count) === 1 && "1 person not in this file was kept."}
          {Number(result.not_in_file_count) > 1 &&
            `${String(result.not_in_file_count)} people not in this file were kept.`}
        </p>
      )}
      {health && (
        <p className="m-0">
          {health.count === 0
            ? "The health check found nothing to look at."
            : `The health check found ${health.count} things worth a second look. See "Check this tree" on the family page.`}
        </p>
      )}
      {r.media_note && <p className="m-0 text-muted">{r.media_note}</p>}
      {changeId && projectId && !undo.isSuccess && (
        <button
          type="button"
          onClick={() => undo.mutate()}
          disabled={undo.isPending}
          className="min-h-11 cursor-pointer self-start rounded-lg border border-control bg-surface px-3"
        >
          {undo.isPending ? "Undoing…" : "Undo this import"}
        </button>
      )}
      {undo.isSuccess && <p className="m-0">The import was undone. The file is still here.</p>}
      {undo.isError && (
        <p className="m-0 text-warning">
          {undo.error instanceof ApiError ? undo.error.message : "The import couldn't be undone."}
        </p>
      )}
    </section>
  );
}
