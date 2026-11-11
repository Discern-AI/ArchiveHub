/**
 * Lineages: who held a role at a place, one after another (pub licensees, owners,
 * vicars...). Each holder is from a record; years with nobody recorded are shown as gaps;
 * recent holders' names are hidden; family-tree matches are suggestions to check.
 */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { lineageApi, type Holder } from "../../lib/lineages";

export function LineagesPage() {
  const subjects = useQuery({ queryKey: ["lineages"], queryFn: lineageApi.subjects });
  return (
    <div className="mx-auto flex w-full max-w-[900px] flex-col gap-4 px-4 py-8 sm:px-12">
      <div>
        <div className="text-[13px] font-semibold text-muted uppercase">Research</div>
        <h1 className="m-0 font-serif text-[32px] font-semibold">Lineages</h1>
        <p className="mt-1 mb-0 text-muted">
          Who held a role at a place, one after another: pub licensees, owners, tenants, vicars.
          Each name comes from a record.
        </p>
      </div>
      {subjects.isPending && <p className="text-muted">Loading…</p>}
      {subjects.data?.length === 0 && <p>No lineages recorded yet.</p>}
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {subjects.data?.map((s) => (
          <li key={s.id} className="rounded-lg border border-line bg-surface p-3">
            <Link to={`/lineages/${s.type}/${s.id}`} className="text-lg font-semibold">
              {s.name}
            </Link>
            <span className="text-muted"> {s.kind && `· ${s.kind}`}</span>
            <div className="text-sm text-muted">
              {s.roles.map((r) => `${r.count} ${r.label.toLowerCase()}`).join(", ")}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function span(h: Holder) {
  const a = h.year_from ?? h.year_to;
  const b = h.year_to ?? h.year_from;
  return [a, b] as const;
}

export function LineagePage() {
  const { type = "", id = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const role = params.get("role") ?? "";
  const data = useQuery({
    queryKey: ["lineage", type, id, role],
    queryFn: () => lineageApi.lineage(type, id, role),
  });
  const [open, setOpen] = useState<string | null>(null);
  const d = data.data;
  if (data.isError)
    return <p className="p-8 text-warning">This lineage couldn&apos;t be loaded.</p>;
  if (!d) return <p className="p-8 text-muted">Loading…</p>;

  const years = d.holders.flatMap((h) => span(h).filter((y): y is number => y !== null));
  const lo = Math.floor((Math.min(...years) - 5) / 10) * 10;
  const hi = Math.ceil((Math.max(...years) + 5) / 10) * 10;
  const pct = (y: number) => `${((y - lo) / Math.max(1, hi - lo)) * 100}%`;
  const width = (a: number, b: number) =>
    `${(Math.max(1, b - a + 1) / Math.max(1, hi - lo)) * 100}%`;
  // Holders and gaps in one chronological list, so a gap sits between the people it separates.
  const rows = [
    ...d.holders
      .filter((h) => span(h)[0] !== null)
      .map((h) => ({ key: h.id, span: span(h) as [number, number], holder: h, gap: false })),
    ...d.gaps.map((g) => ({
      key: `gap-${g.from}`,
      span: [g.from, g.to] as [number, number],
      holder: null as Holder | null,
      gap: true,
    })),
  ].sort((x, y) => x.span[0] - y.span[0]);
  const ticks = [];
  for (let t = lo; t <= hi; t += hi - lo > 100 ? 20 : 10) ticks.push(t);

  return (
    <div className="mx-auto flex w-full max-w-[1000px] flex-col gap-4 px-4 py-8 sm:px-12">
      <div>
        <div className="text-[13px] font-semibold text-muted uppercase">
          <Link to="/lineages">Lineages</Link>
        </div>
        <h1 className="m-0 font-serif text-[32px] font-semibold">{d.subject.name}</h1>
      </div>
      {d.roles.length > 1 && (
        <div
          role="tablist"
          aria-label="Roles"
          className="flex flex-wrap gap-2 border-b border-line"
        >
          {d.roles.map((r) => (
            <button
              key={r.role}
              type="button"
              role="tab"
              aria-selected={d.role === r.role}
              onClick={() => setParams({ role: r.role })}
              className={`-mb-px min-h-11 cursor-pointer border-0 border-b-2 bg-transparent px-3 ${d.role === r.role ? "border-accent font-semibold" : "border-transparent text-muted"}`}
            >
              {r.label}
            </button>
          ))}
        </div>
      )}
      <section
        aria-label={`${d.role_label} over time`}
        className="flex flex-col gap-1 rounded-lg border border-line bg-surface p-4"
      >
        <h2 className="m-0 text-lg font-semibold">{d.role_label} over time</h2>
        <div className="relative h-5 text-xs text-muted" aria-hidden="true">
          {ticks.map((t) => (
            <span key={t} className="absolute -translate-x-1/2" style={{ left: pct(t) }}>
              {t}
            </span>
          ))}
        </div>
        <div className="relative flex flex-col gap-1">
          {rows.map((row) => {
            const [a, b] = row.span;
            const late = (a - lo) / Math.max(1, hi - lo) > 0.7;
            const label = row.gap
              ? `Not recorded ${a}–${b}`
              : (row.holder!.name ?? "Name hidden (may be living)");
            return (
              <div
                key={row.key}
                className="relative h-7"
                data-testid={row.gap ? "gap" : "succession-bar"}
              >
                <div
                  className={`absolute top-1 h-5 rounded ${
                    row.gap
                      ? "border border-dashed border-control"
                      : row.holder!.hidden
                        ? "bg-control"
                        : "bg-accent"
                  }`}
                  style={{ left: pct(a), width: width(a, b), minWidth: 6 }}
                  title={label}
                />
                <span
                  className={`absolute top-1 px-2 text-sm whitespace-nowrap ${row.gap || row.holder!.hidden ? "text-muted" : "font-medium"}`}
                  style={
                    late
                      ? { right: `calc(100% - ${pct(a)})` }
                      : { left: `calc(${pct(a)} + ${width(a, b)})` }
                  }
                >
                  {label}
                </span>
              </div>
            );
          })}
        </div>
      </section>
      <section aria-label="Holders and their records" className="flex flex-col gap-2">
        <h2 className="m-0 text-lg font-semibold">In order</h2>
        <ol className="m-0 flex flex-col gap-3 pl-5">
          {d.holders.map((h) => (
            <li key={h.id}>
              <strong>{h.name ?? "Name hidden: they may still be living"}</strong>{" "}
              <span className="text-muted">{h.date_text || span(h)[0]}</span>
              {h.sources.length > 0 && (
                <button
                  type="button"
                  aria-expanded={open === h.id}
                  onClick={() => setOpen(open === h.id ? null : h.id)}
                  className="ml-2 min-h-8 cursor-pointer border-0 bg-transparent p-0 text-sm text-accent underline"
                >
                  {open === h.id ? "Hide sources" : `Sources (${h.sources.length})`}
                </button>
              )}
              {open === h.id && (
                <ul className="m-0 mt-1 flex flex-col gap-1 pl-5 text-sm">
                  {h.sources.map((s, i) => (
                    <li key={i}>
                      {s.url ? (
                        <a href={s.url} target="_blank" rel="noreferrer">
                          {s.title} ↗
                        </a>
                      ) : (
                        s.title
                      )}
                      {s.what_it_says && <span className="text-muted"> · “{s.what_it_says}”</span>}
                    </li>
                  ))}
                </ul>
              )}
              {h.connections.map((c) => (
                <p key={c.person_id} className="m-0 mt-1 rounded-lg bg-tint p-2 text-sm">
                  May be{" "}
                  <Link to={`/projects/${c.project_id}/people/${c.person_id}`}>{c.name}</Link> in{" "}
                  {c.project} ({c.reason}). Check the records before treating them as the same
                  person.
                </p>
              ))}
            </li>
          ))}
        </ol>
      </section>
      <ul className="m-0 flex flex-col gap-1 pl-5 text-sm text-muted">
        {d.notes.map((n) => (
          <li key={n}>{n}</li>
        ))}
      </ul>
    </div>
  );
}
