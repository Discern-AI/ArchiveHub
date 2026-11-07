/** What a GEDCOM import brought across, and what it left behind. */

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

export function ImportReport({ result }: { result: Record<string, unknown> }) {
  const r = result.report as GedcomReport | undefined;
  if (!r) return null;
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
      {r.media_note && <p className="m-0 text-muted">{r.media_note}</p>}
    </section>
  );
}
