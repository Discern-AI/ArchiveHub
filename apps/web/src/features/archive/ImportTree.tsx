/**
 * Importing a family tree, with a look first: add it as a new tree or update an earlier
 * import of the same tree, see what would be added, updated, kept and worth a second look,
 * then import. Nothing changes until "Import", and the import can be undone in one step.
 */
import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError } from "../../lib/api";
import { treeApi, type ImportPreview } from "../../lib/tree";

export function ImportTree({
  fileId,
  projectId,
  onImported,
}: {
  fileId: string;
  projectId: string;
  onImported: () => void;
}) {
  const trees = useQuery({
    queryKey: ["trees", projectId],
    queryFn: () => treeApi.trees(projectId),
  });
  const [choice, setChoice] = useState<string | null>(null); // "new" or a tree id
  const list = trees.data ?? [];
  const selected = choice ?? (list.length ? list[0].tree : "new");
  const mode = selected === "new" ? "new" : "update";
  const base = selected === "new" ? "" : selected;

  const preview = useMutation({ mutationFn: () => treeApi.preview(fileId, mode, base) });
  const run = useMutation({
    mutationFn: () => treeApi.importTree(fileId, mode, base),
    onSuccess: onImported,
  });

  return (
    <section
      aria-label="Import this family tree"
      className="flex flex-col gap-2 rounded-lg border border-line p-3"
    >
      <h3 className="m-0 text-base font-semibold">Import this family tree</h3>
      {list.length > 0 && (
        <fieldset className="m-0 flex flex-col gap-1 border-0 p-0">
          <legend className="mb-1 text-sm">
            Is this a new export of a tree you&apos;ve imported before?
          </legend>
          {list.map((t) => (
            <label key={t.tree} className="flex min-h-11 items-center gap-2">
              <input
                type="radio"
                name="tree"
                checked={selected === t.tree}
                onChange={() => {
                  setChoice(t.tree);
                  preview.reset();
                }}
              />
              <span>
                Update <strong>{t.first_file}</strong> ({t.people} people
                {t.last_file && t.last_file !== t.first_file
                  ? `, last updated from ${t.last_file}`
                  : ""}
                )
              </span>
            </label>
          ))}
          <label className="flex min-h-11 items-center gap-2">
            <input
              type="radio"
              name="tree"
              checked={selected === "new"}
              onChange={() => {
                setChoice("new");
                preview.reset();
              }}
            />
            Add it as a separate tree
          </label>
        </fieldset>
      )}
      {!preview.data && (
        <button
          type="button"
          onClick={() => preview.mutate()}
          disabled={preview.isPending}
          className="min-h-11 cursor-pointer self-start rounded-lg border border-accent bg-surface px-3 font-medium text-accent"
        >
          {preview.isPending ? "Looking at the file…" : "Preview the import"}
        </button>
      )}
      {preview.isError && (
        <p className="m-0 text-warning">
          {preview.error instanceof ApiError
            ? preview.error.message
            : "The preview couldn't be made."}
        </p>
      )}
      {preview.data && <PreviewSummary p={preview.data} />}
      {preview.data && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => run.mutate()}
            disabled={run.isPending}
            className="min-h-11 cursor-pointer rounded-lg bg-accent px-4 font-semibold text-white"
          >
            {run.isPending ? "Importing…" : mode === "update" ? "Update the tree" : "Import"}
          </button>
          <button
            type="button"
            onClick={() => preview.reset()}
            className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3"
          >
            Back
          </button>
        </div>
      )}
      {run.isError && (
        <p className="m-0 text-warning">The import didn&apos;t finish. Nothing was changed.</p>
      )}
    </section>
  );
}

function PreviewSummary({ p }: { p: ImportPreview }) {
  const findings = p.health.findings;
  return (
    <div role="region" aria-label="Import preview" className="flex flex-col gap-2 text-sm">
      <p className="m-0">
        <strong>{p.people}</strong> people and {p.families} families in this file.{" "}
        {p.mode === "update" ? (
          <>
            <strong>{p.updated}</strong> would be updated and <strong>{p.added}</strong> added.
          </>
        ) : (
          <>
            All <strong>{p.added}</strong> would be added.
          </>
        )}{" "}
        {p.living_private > 0 && `${p.living_private} look to be living and will stay private.`}
      </p>
      {p.not_in_file_count > 0 && (
        <details>
          <summary className="cursor-pointer">
            {p.not_in_file_count === 1
              ? "1 person in the tree isn't in this file. They'll be kept."
              : `${p.not_in_file_count} people in the tree aren't in this file. They'll be kept.`}
          </summary>
          <ul className="m-0 pl-5">
            {p.not_in_file.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </details>
      )}
      {p.id_but_not_name.length > 0 && (
        <div className="rounded-lg border border-warning p-2">
          <strong>Same ID, different name</strong>: these have an ID the tree already uses for
          someone else, so they&apos;ll be added as new people and nobody is overwritten.
          <ul className="m-0 pl-5">
            {p.id_but_not_name.map((m) => (
              <li key={m.id}>
                {m.in_file} (the tree has {m.in_tree} as {m.id})
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="m-0">
        {findings.length === 0
          ? "The health check found nothing to look at after this import."
          : `After this import the health check would find ${findings.length} things worth a second look:`}
      </p>
      {findings.length > 0 && (
        <ul aria-label="Health check after import" className="m-0 pl-5">
          {findings.slice(0, 8).map((f, i) => (
            <li key={i}>
              {f.title}: {f.people.map((x) => x.name).join(", ")}
            </li>
          ))}
          {findings.length > 8 && <li>and {findings.length - 8} more</li>}
        </ul>
      )}
      <p className="m-0 text-muted">
        Nothing has changed yet. You can undo the import afterwards in one step.
      </p>
    </div>
  );
}
