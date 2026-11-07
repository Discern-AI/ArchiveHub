import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { ACCESS_LABELS, api, type ConnectorRecord } from "../../lib/api";
import type { AttachedRecord } from "../../lib/chat";

const button =
  "min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3 font-medium disabled:cursor-not-allowed disabled:opacity-50";

/** An image we may show: public-domain museum images, or Geograph photos with credit. */
export function recordImage(r: ConnectorRecord): { src: string; credit: string } | null {
  const text = (v: unknown) => (typeof v === "string" ? v : "");
  const image = text(r.fields.image);
  if (image.startsWith("https://")) return { src: image, credit: "Public domain" };
  const thumb = text(r.fields.thumbnail);
  if (r.connector === "geograph" && thumb.startsWith("https://")) {
    const who = text(r.fields.photographer);
    return { src: thumb, credit: `Photo${who ? ` © ${who}` : ""}, CC BY-SA 2.0, via Geograph` };
  }
  return null;
}

function FieldList({ fields }: { fields: Record<string, unknown> }) {
  const entries = Object.entries(fields).filter(
    ([, v]) => v !== null && v !== "" && v !== undefined,
  );
  if (!entries.length) return null;
  const show = (v: unknown) =>
    typeof v === "string" || typeof v === "number" ? String(v) : JSON.stringify(v);
  return (
    <dl className="m-0 grid grid-cols-[minmax(0,1fr)_minmax(0,2fr)] gap-x-3 gap-y-1 text-sm">
      {entries.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="font-medium text-muted">{k.replace(/_/g, " ")}</dt>
          <dd className="m-0 break-words">{show(v)}</dd>
        </div>
      ))}
    </dl>
  );
}

export function ExplorerTab({
  projectId,
  onAsk,
}: {
  projectId: string | null;
  onAsk: (record: AttachedRecord) => void;
}) {
  const qc = useQueryClient();
  const sources = useQuery({ queryKey: ["explorer-sources"], queryFn: api.explorerSources });
  const [sourceKey, setSourceKey] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [cursors, setCursors] = useState<(string | null)[]>([null]);
  const [selected, setSelected] = useState<number | null>(null);
  const [note, setNote] = useState<string | null>(null);

  const available = (sources.data ?? []).filter((s) => s.available);
  const unavailable = (sources.data ?? []).filter((s) => !s.available);
  const source = available.find((s) => s.key === sourceKey) ?? available[0];
  const cursor = cursors[cursors.length - 1];

  const page = useQuery({
    queryKey: ["explorer", source?.key, query, cursor],
    queryFn: () => api.explorerSearch(source!.key, query, cursor),
    enabled: !!source && (source.access_type !== "live_api" || !!query),
  });
  const records = page.data?.records ?? [];
  const current: ConnectorRecord | undefined = selected === null ? undefined : records[selected];

  const detail = useQuery({
    queryKey: ["explorer-record", current?.connector, current?.id],
    queryFn: () => api.explorerRecord(current!.connector, current!.id),
    enabled: !!current,
  });

  function search(e: FormEvent) {
    e.preventDefault();
    setQuery(draft.trim());
    setCursors([null]);
    setSelected(null);
  }

  async function save(record: ConnectorRecord) {
    if (!projectId) return;
    try {
      await api.addToBasket(projectId, record.connector, record.id);
      await qc.invalidateQueries({ queryKey: ["basket", projectId] });
      setNote(`Saved “${record.title}” to this project.`);
    } catch (err) {
      setNote((err as Error).message);
    }
  }

  if (sources.isPending) return <p className="m-0 text-muted">Loading sources…</p>;
  if (!source) return <p className="m-0 text-muted">No sources are available yet.</p>;

  if (current) {
    const r = detail.data ?? current;
    return (
      <div className="flex flex-col gap-3">
        <button type="button" className={button} onClick={() => setSelected(null)}>
          ← Back to results
        </button>
        <div className="text-[13px] font-semibold text-muted uppercase">
          {source.name} · {ACCESS_LABELS[source.access_type]}
        </div>
        <h3 className="m-0 font-serif text-xl font-semibold">{r.title}</h3>
        {r.date_text && <div className="text-sm text-muted">{r.date_text}</div>}
        {(() => {
          const img = recordImage(r);
          return img ? (
            <figure className="m-0 flex flex-col gap-1">
              <img
                src={img.src}
                alt={r.title}
                loading="lazy"
                referrerPolicy="no-referrer"
                className="max-h-64 self-start rounded-lg border border-line object-contain"
                onError={(e) => (e.currentTarget.style.display = "none")}
              />
              <figcaption className="text-[13px] text-muted">
                {r.url ? (
                  <a href={r.url} target="_blank" rel="noreferrer">
                    {img.credit}
                  </a>
                ) : (
                  img.credit
                )}
              </figcaption>
            </figure>
          ) : null;
        })()}
        {r.description && <p className="m-0">{r.description}</p>}
        {r.latitude !== null && r.longitude !== null && (
          <div className="text-sm text-muted">
            Map position: {r.latitude.toFixed(5)}, {r.longitude.toFixed(5)} ·{" "}
            <a href={`/map?lat=${r.latitude}&lng=${r.longitude}`}>Show on the time map</a>
          </div>
        )}
        <FieldList
          fields={Object.fromEntries(
            Object.entries(r.fields).filter(([k]) => k !== "image" && k !== "thumbnail"),
          )}
        />
        {r.url && (
          <a href={r.url} target="_blank" rel="noreferrer">
            Open the original
          </a>
        )}
        {detail.data?.citation && (
          <p className="m-0 text-[13px] text-muted">Cite as: {detail.data.citation}</p>
        )}
        {r.rights && <p className="m-0 text-[13px] text-muted">Rights: {r.rights}</p>}
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="min-h-11 cursor-pointer rounded-lg bg-accent px-3 font-semibold text-white"
            onClick={() => onAsk({ connector: r.connector, id: r.id, title: r.title })}
          >
            Ask about this record
          </button>
          <button
            type="button"
            className={button}
            disabled={!projectId}
            title={projectId ? undefined : "Open this chat in a project to save records"}
            onClick={() => save(r)}
          >
            Save to project
          </button>
        </div>
        {!projectId && (
          <p className="m-0 text-[13px] text-muted">
            Saving needs a project. Start the chat from a project to keep a research basket.
          </p>
        )}
        {note && (
          <p role="status" className="m-0 text-sm font-medium text-accent">
            {note}
          </p>
        )}
        <div className="flex justify-between gap-2">
          <button
            type="button"
            className={button}
            disabled={selected === 0}
            onClick={() => setSelected((selected ?? 1) - 1)}
          >
            Previous record
          </button>
          <button
            type="button"
            className={button}
            disabled={selected === records.length - 1}
            onClick={() => setSelected((selected ?? -1) + 1)}
          >
            Next record
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <label className="flex flex-col gap-1 text-sm font-medium">
        Source
        <select
          value={source.key}
          onChange={(e) => {
            setSourceKey(e.target.value);
            setCursors([null]);
            setSelected(null);
          }}
          className="min-h-11 rounded-lg border border-control bg-surface px-2 font-normal"
        >
          {available.map((s) => (
            <option key={s.key} value={s.key}>
              {s.name} ({ACCESS_LABELS[s.access_type]})
            </option>
          ))}
        </select>
      </label>
      <p className="m-0 text-[13px] text-muted">
        {source.description}
        {source.note ? ` ${source.note}.` : ""}
        {source.licence ? ` Licence: ${source.licence}.` : ""}
      </p>
      {unavailable.length > 0 && (
        <details className="text-[13px] text-muted">
          <summary className="cursor-pointer">
            {unavailable.length} more {unavailable.length === 1 ? "source isn't" : "sources aren't"}{" "}
            available here yet
          </summary>
          <ul className="m-0 mt-1 flex flex-col gap-1 pl-5">
            {unavailable.map((s) => (
              <li key={s.key}>
                <strong className="font-medium text-ink">{s.name}</strong>
                {s.note ? `: ${s.note}` : ""}
              </li>
            ))}
          </ul>
        </details>
      )}
      <form onSubmit={search} className="flex gap-2">
        <label htmlFor="explorer-q" className="sr-only">
          Search {source.name}
        </label>
        <input
          id="explorer-q"
          type="search"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={source.access_type === "live_api" ? "Search (required)" : "Search or browse"}
          className="min-h-11 min-w-0 flex-1 rounded-lg border border-control bg-surface px-3"
        />
        <button type="submit" className={button}>
          Search
        </button>
      </form>

      {page.isFetching && <p className="m-0 text-muted">Searching…</p>}
      {page.isError && (
        <p role="alert" className="m-0 text-warning">
          {(page.error as Error).message}
        </p>
      )}
      {page.data && records.length === 0 && (
        <p className="m-0 text-muted">
          Nothing found in {source.name}. That doesn't mean it doesn't exist elsewhere.
        </p>
      )}
      {records.length > 0 && (
        <ul aria-label="Results" className="m-0 flex list-none flex-col gap-1.5 p-0">
          {records.map((r, i) => (
            <li key={`${r.connector}:${r.id}`}>
              <button
                type="button"
                onClick={() => {
                  setSelected(i);
                  setNote(null);
                }}
                className="w-full cursor-pointer rounded-lg border border-line bg-surface px-3 py-2 text-left hover:bg-tint"
              >
                <span className="block font-semibold">{r.title}</span>
                <span className="block truncate text-[13px] text-muted">
                  {[r.record_type, r.date_text, r.description].filter(Boolean).join(" · ")}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {(cursors.length > 1 || page.data?.next_cursor) && (
        <div className="flex justify-between gap-2">
          <button
            type="button"
            className={button}
            disabled={cursors.length <= 1}
            onClick={() => setCursors(cursors.slice(0, -1))}
          >
            Previous page
          </button>
          <span className="self-center text-sm text-muted">Page {cursors.length}</span>
          <button
            type="button"
            className={button}
            disabled={!page.data?.next_cursor}
            onClick={() => setCursors([...cursors, page.data!.next_cursor])}
          >
            Next page
          </button>
        </div>
      )}
    </div>
  );
}
