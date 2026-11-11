/**
 * The Life Report: an illustrated life story to read, edit, save, print or keep as a PDF.
 * Every culture item says why it was chosen and that it shows their world, not them;
 * images appear only where the rights allow. Written from the records, so it's free.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { ApiError, request } from "../../lib/api";

type Block = Record<string, unknown> & { type: string };

interface Report {
  private: boolean;
  note?: string;
  person?: { id: string; name: string };
  length?: string;
  blocks?: Block[];
  cost?: string;
}

const str = (v: unknown) => (typeof v === "string" ? v : "");

export function LifeReportPage() {
  const { projectId = "", personId = "" } = useParams();
  const qc = useQueryClient();
  const [length, setLength] = useState<"short" | "long">("short");
  const [editing, setEditing] = useState(false);
  const draft = useQuery({
    queryKey: ["life-report", projectId, personId, length],
    queryFn: () =>
      request<Report>(
        "GET",
        `/api/v1/projects/${projectId}/people/${personId}/life-report?length=${length}`,
      ),
  });
  const saved = useQuery({
    queryKey: ["life-reports", projectId, personId],
    queryFn: () =>
      request<{ id: string; created_at: string }[]>(
        "GET",
        `/api/v1/projects/${projectId}/people/${personId}/life-reports`,
      ),
  });
  // The family's edits, on top of the draft; null until they change something.
  const [edits, setEdits] = useState<Block[] | null>(null);
  const blocks = edits ?? draft.data?.blocks ?? [];
  const save = useMutation({
    mutationFn: () =>
      request("POST", `/api/v1/projects/${projectId}/people/${personId}/life-reports`, {
        length,
        blocks,
      }),
    onSuccess: () => {
      setEditing(false);
      qc.invalidateQueries({ queryKey: ["life-reports", projectId, personId] });
    },
  });
  const set = (i: number, key: string, value: unknown) =>
    setEdits(blocks.map((b, n) => (n === i ? { ...b, [key]: value } : b)));
  const remove = (i: number) => setEdits(blocks.filter((_, n) => n !== i));

  if (draft.isPending) return <p className="p-8 text-muted">Writing the report…</p>;
  if (draft.isError)
    return <p className="p-8 text-warning">The report couldn&apos;t be written.</p>;
  if (draft.data.private) return <p className="p-8">{draft.data.note}</p>;

  return (
    <div className="mx-auto flex w-full max-w-[820px] flex-col gap-4 px-4 py-8 sm:px-10 print:max-w-none print:p-0">
      <div className="flex flex-wrap items-center justify-between gap-2 print:hidden">
        <Link to={`/projects/${projectId}/people/${personId}`}>← Back to their page</Link>
        <span className="text-sm text-muted">{draft.data.cost}</span>
      </div>
      <div className="flex flex-wrap items-end gap-2 rounded-lg border border-line bg-surface p-3 print:hidden">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Length
          <select
            value={length}
            onChange={(e) => {
              setLength(e.target.value as "short" | "long");
              setEdits(null); // a different length is a fresh draft
            }}
            className="min-h-11 rounded-lg border border-control bg-surface px-2"
          >
            <option value="short">Short</option>
            <option value="long">Long</option>
          </select>
        </label>
        <button
          type="button"
          onClick={() => setEditing((v) => !v)}
          className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3"
        >
          {editing ? "Stop editing" : "Edit"}
        </button>
        <button
          type="button"
          onClick={() => save.mutate()}
          disabled={save.isPending}
          className="min-h-11 cursor-pointer rounded-lg bg-accent px-4 font-semibold text-white"
        >
          Save this version
        </button>
        <button
          type="button"
          onClick={() => window.print()}
          className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3"
        >
          Print or save as PDF
        </button>
        <span className="text-sm text-muted">{draft.data.note}</span>
        {save.isSuccess && (
          <span role="status" className="text-sm font-medium text-accent">
            Saved.
          </span>
        )}
        {save.isError && (
          <span className="text-sm text-warning">
            {save.error instanceof ApiError ? save.error.message : "It couldn't be saved."}
          </span>
        )}
      </div>
      <article aria-label="Life Report" className="flex flex-col gap-4">
        {blocks.map((b, i) => (
          <ReportBlock
            key={i}
            b={b}
            editing={editing}
            onChange={(k, v) => set(i, k, v)}
            onRemove={() => remove(i)}
          />
        ))}
      </article>
      {(saved.data?.length ?? 0) > 0 && (
        <p className="m-0 text-sm text-muted print:hidden">
          {saved.data!.length} saved version{saved.data!.length === 1 ? "" : "s"}, latest{" "}
          {new Date(saved.data![0].created_at).toLocaleDateString("en-GB")}.
        </p>
      )}
    </div>
  );
}

function Editable({
  value,
  editing,
  label,
  onChange,
  rows = 3,
}: {
  value: string;
  editing: boolean;
  label: string;
  onChange: (v: string) => void;
  rows?: number;
}) {
  if (!editing) return <>{value}</>;
  return (
    <textarea
      aria-label={label}
      value={value}
      rows={rows}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-lg border border-control bg-surface p-2 font-normal"
    />
  );
}

function ReportBlock({
  b,
  editing,
  onChange,
  onRemove,
}: {
  b: Block;
  editing: boolean;
  onChange: (k: string, v: unknown) => void;
  onRemove: () => void;
}) {
  switch (b.type) {
    case "title":
      return <h1 className="m-0 font-serif text-[36px] font-semibold">{str(b.text)}</h1>;
    case "glance":
      return (
        <dl className="m-0 grid grid-cols-2 gap-2 rounded-lg border border-line p-3 sm:grid-cols-4">
          {[
            ["Born", b.born],
            ["Died", b.died],
            ["Work", b.occupation],
          ].map(([k, v]) => (
            <div key={String(k)}>
              <dt className="text-xs font-semibold text-muted uppercase">{String(k)}</dt>
              <dd className="m-0">{str(v) || "Not recorded"}</dd>
            </div>
          ))}
        </dl>
      );
    case "heading":
      return <h2 className="m-0 mt-2 font-serif text-2xl font-semibold">{str(b.text)}</h2>;
    case "paragraph":
      return (
        <p className="m-0 text-[17px] leading-relaxed">
          <Editable
            value={str(b.text)}
            editing={editing}
            label="Paragraph"
            onChange={(v) => onChange("text", v)}
          />
        </p>
      );
    case "context":
      return (
        <div className="flex flex-col gap-1 rounded-lg bg-tint p-3">
          <p className="m-0 text-sm text-muted">
            Around {String(b.year)}. {str(b.label)}
          </p>
          <ul className="m-0 flex flex-col gap-1 pl-5">
            {(b.lines as string[]).map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </div>
      );
    case "culture":
      return (
        <figure
          aria-label={str(b.title)}
          className="m-0 flex flex-col gap-2 rounded-lg border border-line bg-surface p-3 print:break-inside-avoid"
        >
          {str(b.image_url) && (
            <img
              src={str(b.image_url)}
              alt={`${str(b.title)}, ${str(b.creator)}`}
              className="max-h-96 w-full rounded object-contain"
            />
          )}
          {str(b.text) && (
            <blockquote className="m-0 border-l-4 border-line pl-3 font-serif text-lg whitespace-pre-wrap">
              {str(b.text)}
            </blockquote>
          )}
          <figcaption className="flex flex-col gap-1 text-sm">
            <strong>
              {str(b.title)}
              <span className="font-normal text-muted">
                {" "}
                · {str(b.creator)} · {str(b.made)}
              </span>
            </strong>
            {b.link_only === true && (
              <a href={str(b.source_url)} target="_blank" rel="noreferrer">
                See it at {str(b.source_name)} ↗
              </a>
            )}
            <span>
              <span className="font-semibold">Why this was chosen: </span>
              <Editable
                value={str(b.why)}
                editing={editing}
                label="Why this was chosen"
                rows={2}
                onChange={(v) => onChange("why", v)}
              />
            </span>
            <span className="text-muted">{str(b.label)}</span>
            <span className="text-xs text-muted">
              {str(b.credit)}{" "}
              <a href={str(b.source_url)} target="_blank" rel="noreferrer" className="print:hidden">
                Source ↗
              </a>
            </span>
            {editing && (
              <button
                type="button"
                onClick={onRemove}
                className="min-h-11 cursor-pointer self-start rounded-lg border border-control bg-surface px-3"
              >
                Leave this out
              </button>
            )}
          </figcaption>
        </figure>
      );
    case "gaps":
      return (
        <ul className="m-0 flex flex-col gap-1 pl-5">
          {(b.lines as string[]).map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
      );
    default:
      return null;
  }
}
