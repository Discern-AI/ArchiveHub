/**
 * The Lifeline: every relative as a bar through time, a year line you drag, how many were
 * alive each year, wars, laws and record milestones you can switch on and off, and a map
 * of where people were recorded by that year.
 *
 * Faded bar ends mean the date isn't exact. Living people keep their dates private, so
 * they're listed but never placed in time. Written from scratch (ADR-048).
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { Link, useParams } from "react-router";
import { api, ApiError } from "../../lib/api";
import {
  aliveCounts,
  directLine,
  generations,
  LAYERS,
  lifeLabel,
  lifelineApi,
  spans,
  statusAt,
  whyUncertain,
  yearRange,
  type LifePerson,
  type Overlay,
  type Status,
} from "../../lib/lifeline";
import { mapApi } from "../../lib/map";

const LifelineMap = lazy(() => import("./LifelineMap"));

const ROW_H = 34;
const FADE = 25; // years of fade drawn for an unknown or approximate end
const SPEEDS = [1, 5, 10];
const KIND_COLOUR: Record<string, string> = {
  war: "#b3261e",
  records: "#1f5c4d",
  law: "#6b5a3e",
  calendar: "#52635e",
  local: "#a14a12",
  custom: "#6b3fa0",
};
const STATUS_TEXT: Record<Status, string> = {
  alive: "alive",
  uncertain: "possibly alive",
  "recently-died": "died shortly before",
  "soon-born": "born shortly after",
  "not-alive": "not alive",
  private: "living: dates private",
};

type Row = { type: "group"; label: string } | { type: "person"; person: LifePerson };

/** The element's width, measured whenever it appears (it isn't there while loading).
 * ResizeObserver reports the size as soon as it starts observing. */
function useWidth<T extends HTMLElement>() {
  const [el, setEl] = useState<T | null>(null);
  const [width, setWidth] = useState(800);
  useEffect(() => {
    if (!el) return;
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(300, entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, [el]);
  return [setEl, width] as const;
}

export function LifelinePage() {
  const { projectId = "" } = useParams();
  const qc = useQueryClient();
  const data = useQuery({
    queryKey: ["lifeline", projectId],
    queryFn: () => lifelineApi.get(projectId),
  });
  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.project(projectId),
  });
  const layers = useQuery({ queryKey: ["map-layers"], queryFn: mapApi.layers });

  const [year, setYear] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const [direction, setDirection] = useState<1 | -1>(1);
  const [speed, setSpeed] = useState(5);
  const [groupBy, setGroupBy] = useState<"none" | "surname" | "generation">("none");
  const [focus, setFocus] = useState("");
  const [q, setQ] = useState("");
  const [kinds, setKinds] = useState<string[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [openOverlay, setOpenOverlay] = useState<Overlay | null>(null);
  const [showMap, setShowMap] = useState(true);
  const [timelineRef, width] = useWidth<HTMLDivElement>();
  const scrollRef = useRef<HTMLDivElement>(null);

  const d = data.data;
  const range = useMemo(() => (d ? yearRange(d) : ([1850, 2026] as [number, number])), [d]);
  const [lo, hi] = range;
  const current = year ?? Math.min(hi, Math.max(lo, 1900));
  const activeKinds = kinds ?? d?.kinds ?? [];

  const savePreset = useMutation({
    mutationFn: (next: string[]) => lifelineApi.savePreset(projectId, next),
  });
  const toggleKind = (kind: string) => {
    const next = activeKinds.includes(kind)
      ? activeKinds.filter((k) => k !== kind)
      : [...activeKinds, kind];
    setKinds(next);
    savePreset.mutate(next);
  };

  // Autoplay through time, stopping at either end.
  useEffect(() => {
    if (!playing) return;
    const t = window.setInterval(() => {
      setYear((y) => {
        const next = (y ?? current) + direction;
        if (next > hi || next < lo) {
          setPlaying(false);
          return y;
        }
        return next;
      });
    }, 1000 / speed);
    return () => window.clearInterval(t);
  }, [playing, direction, speed, lo, hi, current]);

  const people = useMemo(() => d?.people ?? [], [d]);
  const gens = useMemo(() => generations(people), [people]);
  const shown = useMemo(() => {
    const line = focus ? directLine(people, focus) : null;
    const needle = q.trim().toLowerCase();
    return people.filter(
      (p) =>
        (!line || line.has(p.id)) &&
        (!needle ||
          p.name.toLowerCase().includes(needle) ||
          p.places.some((pl) => pl.place.toLowerCase().includes(needle))),
    );
  }, [people, focus, q]);

  const rows: Row[] = useMemo(() => {
    const sortKey = (p: LifePerson) => spans(p).possibleFrom ?? 99999;
    const sorted = [...shown].sort(
      (a, b) => sortKey(a) - sortKey(b) || a.name.localeCompare(b.name),
    );
    if (groupBy === "none") return sorted.map((person) => ({ type: "person", person }));
    const groups = new Map<string, LifePerson[]>();
    for (const p of sorted) {
      const key =
        groupBy === "surname" ? p.surname || "No surname" : `Generation ${gens.get(p.id) ?? 1}`;
      groups.set(key, [...(groups.get(key) ?? []), p]);
    }
    const keys = [...groups.keys()].sort((a, b) =>
      groupBy === "generation"
        ? Number(a.split(" ")[1]) - Number(b.split(" ")[1])
        : a.localeCompare(b),
    );
    return keys.flatMap((k) => [
      { type: "group" as const, label: `${k} (${groups.get(k)!.length})` },
      ...groups.get(k)!.map((person) => ({ type: "person" as const, person })),
    ]);
  }, [shown, groupBy, gens]);

  // TanStack Virtual returns functions the React Compiler can't memoise; this component
  // simply isn't compiler-optimised, which is fine for one page.
  // eslint-disable-next-line react-hooks/incompatible-library
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_H,
    overscan: 12,
    initialRect: { width: 800, height: 520 },
  });

  const nameW = width < 640 ? 110 : 190;
  const plotW = Math.max(120, width - nameW - 8);
  const x = (y: number) => ((y - lo) / Math.max(1, hi - lo)) * plotW;
  const yearAt = (px: number) =>
    Math.round(Math.min(hi, Math.max(lo, lo + (px / plotW) * (hi - lo))));

  const counts = useMemo(() => aliveCounts(shown, lo, hi), [shown, lo, hi]);
  const maxCount = Math.max(1, ...counts.map((c) => c.alive + c.uncertain));
  const overlays = (d?.overlays ?? []).filter(
    (o) => activeKinds.includes(o.kind) && (o.year_to ?? o.year_from) >= lo && o.year_from <= hi,
  );

  const byStatus = useMemo(() => {
    const out: Record<Status, LifePerson[]> = {
      alive: [],
      uncertain: [],
      "recently-died": [],
      "soon-born": [],
      "not-alive": [],
      private: [],
    };
    for (const p of shown) out[statusAt(p, current)].push(p);
    return out;
  }, [shown, current]);

  // Drag along the timeline to move the year.
  const dragging = useRef(false);
  const fromPointer = (e: ReactPointerEvent<HTMLElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setYear(yearAt(e.clientX - rect.left - nameW));
  };

  if (data.isError) {
    return (
      <div className="mx-auto max-w-[1040px] px-4 py-8">
        <p className="text-warning">The Lifeline couldn't be loaded.</p>
      </div>
    );
  }

  const ticks: number[] = [];
  const step = hi - lo > 200 ? 50 : hi - lo > 80 ? 20 : 10;
  for (let t = Math.ceil(lo / step) * step; t <= hi; t += step) ticks.push(t);

  return (
    <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-4 px-4 py-6 sm:px-8 print:px-0">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[13px] font-semibold text-muted uppercase">
            <Link to={`/projects/${projectId}/people`}>Family tree</Link> · Lifeline
          </div>
          <h1 className="m-0 font-serif text-[32px] font-semibold">{project.data?.title ?? "…"}</h1>
          <p className="mt-1 mb-0 max-w-[70ch] text-muted">
            Everyone as a bar through time. Faded ends mean a date is approximate or not recorded.
            Living relatives keep their dates private, so they aren't placed in time.
          </p>
        </div>
        <button
          type="button"
          onClick={() => window.print()}
          className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-4 print:hidden"
        >
          Print
        </button>
      </div>

      <section aria-label="Controls" className="flex flex-col gap-3 print:hidden">
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 font-medium">
            Year
            <input
              type="number"
              min={lo}
              max={hi}
              value={current}
              onChange={(e) => {
                const v = Number(e.target.value);
                if (Number.isFinite(v)) setYear(Math.min(hi, Math.max(lo, Math.round(v))));
              }}
              className="min-h-11 w-28 rounded-lg border border-control bg-surface px-3 font-normal"
            />
          </label>
          <label className="flex min-w-[220px] flex-1 flex-col gap-1 font-medium">
            <span>
              Move through time{" "}
              <span className="font-normal text-muted">
                ({lo}–{hi})
              </span>
            </span>
            <input
              type="range"
              min={lo}
              max={hi}
              value={current}
              aria-label="Year slider"
              onChange={(e) => setYear(Number(e.target.value))}
              className="min-h-11"
            />
          </label>
          <div className="flex items-end gap-2">
            <button
              type="button"
              onClick={() => {
                setDirection(-1);
                setPlaying(true);
              }}
              aria-label="Play backwards"
              className="min-h-11 min-w-11 cursor-pointer rounded-lg border border-control bg-surface px-3"
            >
              ◀
            </button>
            <button
              type="button"
              onClick={() => {
                if (playing) setPlaying(false);
                else {
                  setDirection(1);
                  setPlaying(true);
                }
              }}
              className="min-h-11 cursor-pointer rounded-lg bg-accent px-4 font-semibold text-white"
            >
              {playing ? "Pause" : "Play"}
            </button>
            <label className="flex flex-col gap-1 text-sm font-medium">
              Speed
              <select
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
                className="min-h-11 rounded-lg border border-control bg-surface px-2"
              >
                {SPEEDS.map((s) => (
                  <option key={s} value={s}>
                    {s} {s === 1 ? "year" : "years"} a second
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 font-medium">
            Group by
            <select
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value as typeof groupBy)}
              className="min-h-11 rounded-lg border border-control bg-surface px-2"
            >
              <option value="none">Nothing</option>
              <option value="surname">Surname</option>
              <option value="generation">Generation</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 font-medium">
            Show
            <select
              value={focus}
              onChange={(e) => setFocus(e.target.value)}
              className="min-h-11 max-w-[260px] rounded-lg border border-control bg-surface px-2"
            >
              <option value="">Everyone</option>
              {people
                .slice()
                .sort((a, b) => a.name.localeCompare(b.name))
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    Direct line of {p.name}
                  </option>
                ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 font-medium">
            Find a name or place
            <input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="min-h-11 rounded-lg border border-control bg-surface px-3 font-normal"
            />
          </label>
        </div>
        <fieldset className="m-0 flex flex-wrap gap-x-4 gap-y-1 border-0 p-0">
          <legend className="mb-1 font-medium">Show on the timeline</legend>
          {LAYERS.map((l) => (
            <label key={l.kind} className="flex min-h-11 items-center gap-2">
              <input
                type="checkbox"
                checked={activeKinds.includes(l.kind)}
                onChange={() => toggleKind(l.kind)}
              />
              {l.kind !== "family" && (
                <span
                  aria-hidden="true"
                  className="inline-block size-3 rounded-sm"
                  style={{ background: KIND_COLOUR[l.kind] }}
                />
              )}
              {l.label}
            </label>
          ))}
        </fieldset>
        <AddMarker
          projectId={projectId}
          year={current}
          onAdded={() => qc.invalidateQueries({ queryKey: ["lifeline", projectId] })}
        />
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_340px]">
        <section aria-label="Lifeline" className="flex min-w-0 flex-col gap-1">
          {data.isPending ? (
            <p className="text-muted">Loading the Lifeline…</p>
          ) : people.length === 0 ? (
            <p className="text-muted">
              No one in this tree yet.{" "}
              <Link to={`/archive?project=${projectId}`}>Import a GEDCOM file</Link> to see everyone
              through time.
            </p>
          ) : (
            <div ref={timelineRef} className="min-w-0">
              {/* How many were alive each year */}
              <svg
                width={nameW + plotW}
                height={52}
                role="img"
                aria-label={`Relatives alive each year. In ${current}: ${byStatus.alive.length} alive, ${byStatus.uncertain.length} possibly alive.`}
                className="block"
              >
                <text x={0} y={14} className="fill-muted text-[12px]">
                  Alive each year
                </text>
                <g transform={`translate(${nameW},0)`}>
                  {counts.map((c) => {
                    const w = Math.max(1, plotW / Math.max(1, hi - lo + 1));
                    const ha = (c.alive / maxCount) * 44;
                    const hu = (c.uncertain / maxCount) * 44;
                    return (
                      <g key={c.year}>
                        <rect x={x(c.year)} y={48 - ha} width={w} height={ha} fill="#1f5c4d" />
                        <rect
                          x={x(c.year)}
                          y={48 - ha - hu}
                          width={w}
                          height={hu}
                          fill="#1f5c4d"
                          opacity={0.3}
                        />
                      </g>
                    );
                  })}
                </g>
              </svg>
              {/* Axis and overlay labels: click or drag to set the year */}
              <div
                className="relative cursor-ew-resize select-none border-b border-line"
                style={{ height: 40 }}
                onPointerDown={(e) => {
                  dragging.current = true;
                  e.currentTarget.setPointerCapture?.(e.pointerId);
                  fromPointer(e);
                }}
                onPointerMove={(e) => dragging.current && fromPointer(e)}
                onPointerUp={() => (dragging.current = false)}
                aria-hidden="true"
              >
                {ticks.map((t) => (
                  <span
                    key={t}
                    className="absolute bottom-0 -translate-x-1/2 text-xs text-muted"
                    style={{ left: nameW + x(t) }}
                  >
                    {t}
                  </span>
                ))}
                <span
                  className="absolute top-0 -translate-x-1/2 rounded bg-focus px-1.5 text-xs font-semibold text-white"
                  style={{ left: nameW + x(current) }}
                >
                  {current}
                </span>
              </div>
              <ul aria-label="Events shown" className="m-0 flex list-none flex-wrap gap-1 p-0 py-1">
                {overlays.map((o) => (
                  <li key={o.id}>
                    <button
                      type="button"
                      onClick={() => setOpenOverlay(o)}
                      className="cursor-pointer rounded-full border-0 px-2 py-0.5 text-xs text-white"
                      style={{ background: KIND_COLOUR[o.kind] }}
                      data-kind={o.kind}
                    >
                      {o.title} {o.date_text || o.year_from}
                      {o.area ? ` (${o.area})` : ""}
                    </button>
                  </li>
                ))}
              </ul>
              {openOverlay && (
                <OverlayDetail
                  overlay={openOverlay}
                  projectId={projectId}
                  onClose={() => setOpenOverlay(null)}
                  onDeleted={() => {
                    setOpenOverlay(null);
                    qc.invalidateQueries({ queryKey: ["lifeline", projectId] });
                  }}
                />
              )}
              <div
                ref={scrollRef}
                className="relative overflow-y-auto rounded-lg border border-line bg-surface"
                style={{ height: Math.min(560, Math.max(160, rows.length * ROW_H + 8)) }}
              >
                <div
                  className="relative"
                  style={{ height: virtualizer.getTotalSize(), width: nameW + plotW }}
                  onPointerDown={(e) => {
                    if ((e.target as HTMLElement).closest("a,button")) return;
                    const rect = e.currentTarget.getBoundingClientRect();
                    if (e.clientX - rect.left > nameW)
                      setYear(yearAt(e.clientX - rect.left - nameW));
                  }}
                >
                  {/* Overlays behind the bars */}
                  {overlays.map((o) => (
                    <div
                      key={o.id}
                      aria-hidden="true"
                      data-overlay={o.kind}
                      className="pointer-events-none absolute top-0 bottom-0"
                      style={{
                        left: nameW + x(Math.max(lo, o.year_from)),
                        width: o.year_to
                          ? Math.max(
                              2,
                              x(Math.min(hi, o.year_to + 1)) - x(Math.max(lo, o.year_from)),
                            )
                          : 2,
                        background: KIND_COLOUR[o.kind],
                        opacity: o.year_to ? 0.12 : 0.5,
                      }}
                    />
                  ))}
                  {virtualizer.getVirtualItems().map((item) => {
                    const row = rows[item.index];
                    return (
                      <div
                        key={item.key}
                        className="absolute left-0 flex w-full items-center"
                        style={{ top: item.start, height: ROW_H }}
                      >
                        {row.type === "group" ? (
                          <div className="w-full bg-tint px-2 text-sm font-semibold">
                            {row.label}
                          </div>
                        ) : (
                          <PersonRow
                            person={row.person}
                            projectId={projectId}
                            year={current}
                            nameW={nameW}
                            plotW={plotW}
                            x={x}
                            showFamily={activeKinds.includes("family")}
                            selected={selected === row.person.id}
                          />
                        )}
                      </div>
                    );
                  })}
                  {/* The year line */}
                  <div
                    aria-hidden="true"
                    className="pointer-events-none absolute top-0 bottom-0 w-0.5 bg-focus"
                    style={{ left: nameW + x(current) }}
                  />
                </div>
              </div>
              <p className="m-0 text-xs text-muted">
                Faded ends: a date is "about", "before", a range, or not recorded. A recorded
                address shows they were alive that year. Wars and laws are shown for context: they
                don't say anyone took part.
              </p>
            </div>
          )}
        </section>

        <aside className="flex flex-col gap-3">
          <div className="flex items-center justify-between lg:hidden print:hidden">
            <button
              type="button"
              onClick={() => setShowMap((v) => !v)}
              className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3"
            >
              {showMap ? "Hide map" : "Show map"}
            </button>
          </div>
          {showMap && (
            <section aria-label="Where they were" className="flex flex-col gap-1 print:hidden">
              <h2 className="m-0 text-lg font-semibold">Where they were by {current}</h2>
              <div className="h-72">
                {layers.data?.today.style ? (
                  <Suspense fallback={<p className="text-sm text-muted">Loading the map…</p>}>
                    <LifelineMap
                      styleUrl={layers.data.today.style}
                      people={shown}
                      year={current}
                      onSelect={setSelected}
                    />
                  </Suspense>
                ) : (
                  <p className="text-sm text-muted">Loading the map…</p>
                )}
              </div>
              <p className="m-0 text-xs text-muted">
                Each point is the last place recorded for someone by {current}. Dashed lines join
                their recorded places in date order: when and how they moved isn't known. Faint
                points are suggested locations not yet checked.
              </p>
            </section>
          )}
          <AliveList
            year={current}
            byStatus={byStatus}
            livingPrivate={shown.filter((p) => p.living).length}
            projectId={projectId}
          />
        </aside>
      </div>
    </div>
  );
}

function PersonRow({
  person: p,
  projectId,
  year,
  nameW,
  plotW,
  x,
  showFamily,
  selected,
}: {
  person: LifePerson;
  projectId: string;
  year: number;
  nameW: number;
  plotW: number;
  x: (y: number) => number;
  showFamily: boolean;
  selected: boolean;
}) {
  const status = statusAt(p, year);
  const label = lifeLabel(p);
  const { possibleFrom, possibleTo, sureFrom, sureTo } = spans(p);
  const colour = status === "alive" || status === "uncertain" ? "#1f5c4d" : "#8a9c96";
  const gid = `fade-${p.id}`;
  let bar = null;
  if (!p.living && possibleFrom !== null && possibleTo !== null) {
    let solidFrom: number;
    let solidTo: number;
    if (sureFrom !== null && sureTo !== null && sureFrom <= sureTo) {
      solidFrom = sureFrom;
      solidTo = sureTo;
    } else if (sureFrom !== null) {
      solidFrom = solidTo = sureFrom; // born, but no later record or death
    } else if (sureTo !== null) {
      solidFrom = solidTo = sureTo; // died, but no record of the birth
    } else {
      solidFrom = solidTo = possibleFrom;
    }
    const startFaded = !p.start || p.start.certainty !== "exact";
    const endFaded = !p.end || p.end.certainty !== "exact";
    const fadeInFrom = Math.max(possibleFrom, solidFrom - FADE);
    const fadeInTo = solidFrom;
    const fadeOutFrom = solidTo;
    const fadeOutTo = Math.min(possibleTo, solidTo + FADE);
    const s = solidFrom;
    const e = solidTo;
    bar = (
      <svg width={plotW} height={ROW_H} className="block" aria-hidden="true">
        <defs>
          <linearGradient id={`${gid}-in`}>
            <stop offset="0" stopColor={colour} stopOpacity="0" />
            <stop offset="1" stopColor={colour} stopOpacity="0.9" />
          </linearGradient>
          <linearGradient id={`${gid}-out`}>
            <stop offset="0" stopColor={colour} stopOpacity="0.9" />
            <stop offset="1" stopColor={colour} stopOpacity="0" />
          </linearGradient>
        </defs>
        {startFaded && fadeInTo > fadeInFrom && (
          <rect
            data-part="fade-in"
            x={x(fadeInFrom)}
            y={10}
            width={x(fadeInTo) - x(fadeInFrom)}
            height={14}
            fill={`url(#${gid}-in)`}
          />
        )}
        {
          <rect
            data-part="sure"
            x={x(s)}
            y={10}
            width={Math.max(2, x(e) - x(s))}
            height={14}
            rx={3}
            fill={colour}
          />
        }
        {endFaded && fadeOutTo > fadeOutFrom && (
          <rect
            data-part="fade-out"
            x={x(fadeOutFrom)}
            y={10}
            width={x(fadeOutTo) - x(fadeOutFrom)}
            height={14}
            fill={`url(#${gid}-out)`}
          />
        )}
        {showFamily &&
          p.places.map((pl, i) => {
            const y = pl.year_from ?? pl.year_to;
            if (y === null) return null;
            return (
              <circle
                key={i}
                data-part="event"
                cx={x(y)}
                cy={17}
                r={4}
                fill="#ffffff"
                stroke="#6b3fa0"
                strokeWidth={2}
              >
                <title>
                  {pl.kind} {pl.date_text}: {pl.place}
                </title>
              </circle>
            );
          })}
      </svg>
    );
  }
  return (
    <div
      className={`flex w-full items-center ${selected ? "bg-selected" : ""}`}
      data-status={status}
      data-start={p.start && p.start.certainty === "exact" ? "sharp" : "faded"}
      data-testid={`row-${p.id}`}
    >
      <Link
        to={`/projects/${projectId}/people/${p.id}`}
        className="shrink-0 truncate px-2 text-sm"
        style={{ width: nameW }}
        title={`${p.name}: ${label}`}
        aria-label={`${p.name}, ${label}. In ${year}: ${STATUS_TEXT[status]}`}
      >
        {p.name}
      </Link>
      {p.living ? (
        <span className="relative rounded bg-surface px-1 text-xs text-muted">
          Living: dates private
        </span>
      ) : (
        (bar ?? <span className="text-xs text-muted">No dates recorded</span>)
      )}
    </div>
  );
}

function AliveList({
  year,
  byStatus,
  livingPrivate,
  projectId,
}: {
  year: number;
  byStatus: Record<Status, LifePerson[]>;
  livingPrivate: number;
  projectId: string;
}) {
  const link = (p: LifePerson, note?: string) => (
    <li key={p.id}>
      <Link to={`/projects/${projectId}/people/${p.id}`}>{p.name}</Link>
      {note && <span className="text-muted"> · {note}</span>}
    </li>
  );
  return (
    <section
      aria-label={`Alive in ${year}`}
      className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-3"
    >
      <h2 className="m-0 text-lg font-semibold">Alive in {year}</h2>
      <p className="m-0 text-sm text-muted">
        {byStatus.alive.length} placed alive by their records
        {byStatus.uncertain.length ? `, ${byStatus.uncertain.length} possibly` : ""}.
      </p>
      {byStatus.alive.length > 0 && (
        <ul aria-label="Alive" className="m-0 flex flex-col gap-0.5 pl-5 text-sm">
          {byStatus.alive.map((p) => link(p))}
        </ul>
      )}
      {byStatus.uncertain.length > 0 && (
        <>
          <h3 className="m-0 text-sm font-semibold">Possibly alive</h3>
          <ul aria-label="Possibly alive" className="m-0 flex flex-col gap-0.5 pl-5 text-sm">
            {byStatus.uncertain.map((p) => link(p, whyUncertain(p, year)))}
          </ul>
        </>
      )}
      {(byStatus["recently-died"].length > 0 || byStatus["soon-born"].length > 0) && (
        <>
          <h3 className="m-0 text-sm font-semibold">Just before and after</h3>
          <ul aria-label="Just before and after" className="m-0 flex flex-col gap-0.5 pl-5 text-sm">
            {byStatus["recently-died"].map((p) => link(p, `died ${lifeLabel(p).split(" – ")[1]}`))}
            {byStatus["soon-born"].map((p) => link(p, `born ${lifeLabel(p).split(" – ")[0]}`))}
          </ul>
        </>
      )}
      {livingPrivate > 0 && (
        <p className="m-0 text-xs text-muted">
          {livingPrivate} living {livingPrivate === 1 ? "relative isn't" : "relatives aren't"}{" "}
          counted: their dates are private.
        </p>
      )}
    </section>
  );
}

function OverlayDetail({
  overlay: o,
  projectId,
  onClose,
  onDeleted,
}: {
  overlay: Overlay;
  projectId: string;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const remove = useMutation({
    mutationFn: () => lifelineApi.deleteMarker(projectId, o.id),
    onSuccess: onDeleted,
  });
  return (
    <div
      role="region"
      aria-label={o.title}
      className="mb-2 rounded-lg border border-line bg-surface p-3 text-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <strong>{o.title}</strong>, {o.date_text || o.year_from}
          {o.year_to && !o.date_text ? `–${o.year_to}` : ""}
          {o.area && <span className="text-muted"> · {o.area}</span>}
        </div>
        <button
          type="button"
          onClick={onClose}
          className="min-h-11 cursor-pointer border-0 bg-transparent px-2 text-muted"
        >
          Close
        </button>
      </div>
      {o.note && <p className="my-1">{o.note}</p>}
      {o.source_url && (
        <a href={o.source_url} target="_blank" rel="noreferrer">
          Source: {o.source_title} ↗
        </a>
      )}
      {!o.builtin && (
        <button
          type="button"
          onClick={() => remove.mutate()}
          className="ml-2 min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3"
        >
          Remove this marker
        </button>
      )}
      {remove.isError && <p className="m-0 text-warning">The marker couldn't be removed.</p>}
    </div>
  );
}

function AddMarker({
  projectId,
  year,
  onAdded,
}: {
  projectId: string;
  year: number;
  onAdded: () => void;
}) {
  const [title, setTitle] = useState("");
  const [from, setFrom] = useState("");
  const add = useMutation({
    mutationFn: () =>
      lifelineApi.addMarker(projectId, { title: title.trim(), year_from: Number(from || year) }),
    onSuccess: () => {
      setTitle("");
      setFrom("");
      onAdded();
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (title.trim()) add.mutate();
  };
  return (
    <details>
      <summary className="min-h-11 cursor-pointer py-2 font-medium">Add your own marker</summary>
      <form onSubmit={submit} className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-sm font-medium">
          What happened
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="I was born"
            className="min-h-11 rounded-lg border border-control bg-surface px-3 font-normal"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Marker year
          <input
            type="number"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            placeholder={String(year)}
            className="min-h-11 w-28 rounded-lg border border-control bg-surface px-3 font-normal"
          />
        </label>
        <button
          type="submit"
          className="min-h-11 cursor-pointer rounded-lg bg-accent px-4 font-semibold text-white"
        >
          Add marker
        </button>
        {add.isError && (
          <p className="m-0 text-warning">
            {add.error instanceof ApiError ? add.error.message : "The marker couldn't be added."}
          </p>
        )}
      </form>
    </details>
  );
}
