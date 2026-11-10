/**
 * A family chart: one person, their ancestors above and their children below.
 * Drawn as plain SVG. Boxes are focusable buttons; choose one to move the chart to them.
 * Living people show as "Living", without dates.
 */
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, type KeyboardEvent } from "react";
import { Link } from "react-router";
import { request } from "../../lib/api";

interface Node {
  id: string;
  name: string;
  sex: string;
  living: boolean;
  born: number | null;
  died: number | null;
}

interface Graph {
  people: Node[];
  links: { from: string; to: string; kind: "parent" | "spouse" }[];
}

const BOX_W = 150;
const BOX_H = 54;
const GAP_X = 14;
const GAP_Y = 46;
const MAX_CHILDREN = 8;

function years(n: Node): string {
  if (n.living) return "Living";
  if (n.born && n.died) return `${n.born}–${n.died}`;
  if (n.born) return `born ${n.born}`;
  if (n.died) return `died ${n.died}`;
  return "";
}

function short(name: string, max = 20): string {
  return name.length > max ? `${name.slice(0, max - 1)}…` : name;
}

export function TreeChart({ projectId }: { projectId: string }) {
  const graph = useQuery({
    queryKey: ["tree-graph", projectId],
    queryFn: () => request<Graph>("GET", `/api/v1/projects/${projectId}/tree-graph`),
  });
  const [focusId, setFocusId] = useState<string | null>(null);
  const [generations, setGenerations] = useState(2);

  const index = useMemo(() => {
    const people = new Map((graph.data?.people ?? []).map((p) => [p.id, p]));
    const parents = new Map<string, string[]>();
    const children = new Map<string, string[]>();
    const partners = new Map<string, string[]>();
    const degree = new Map<string, number>();
    for (const l of graph.data?.links ?? []) {
      degree.set(l.from, (degree.get(l.from) ?? 0) + 1);
      degree.set(l.to, (degree.get(l.to) ?? 0) + 1);
      if (l.kind === "spouse") {
        partners.set(l.from, [...(partners.get(l.from) ?? []), l.to]);
        partners.set(l.to, [...(partners.get(l.to) ?? []), l.from]);
        continue;
      }
      parents.set(l.to, [...(parents.get(l.to) ?? []), l.from]);
      children.set(l.from, [...(children.get(l.from) ?? []), l.to]);
    }
    // Start on the best-connected person.
    const start = [...people.keys()].sort((a, b) => (degree.get(b) ?? 0) - (degree.get(a) ?? 0))[0];
    return { people, parents, children, partners, start };
  }, [graph.data]);

  if (graph.isPending) return null;
  if (graph.isError || !graph.data?.people.length) return null;
  const focus = index.people.get(focusId ?? "") ?? index.people.get(index.start)!;

  const parentsOf = (id: string) =>
    (index.parents.get(id) ?? [])
      .map((pid) => index.people.get(pid)!)
      .filter(Boolean)
      .sort((a, b) => (a.sex === "F" ? 1 : 0) - (b.sex === "F" ? 1 : 0))
      .slice(0, 2);

  // How many generations up actually exist (up to the number chosen), so there's no gap.
  let depth = 0;
  let frontier = [focus.id];
  while (depth < generations) {
    const up = frontier.flatMap((id) => parentsOf(id).map((p) => p.id));
    if (!up.length) break;
    depth += 1;
    frontier = up;
  }

  // Ancestors: generation k has 2^k slots; father on the left, mother on the right.
  const partners = (index.partners.get(focus.id) ?? [])
    .map((id) => index.people.get(id)!)
    .filter(Boolean)
    .slice(0, 3);
  const slotW = BOX_W + GAP_X;
  const treeWidth = 2 ** depth * slotW;
  const focusX = treeWidth / 2;
  const width = Math.max(treeWidth, focusX + (partners.length + 0.5) * slotW);
  type Placed = { node: Node; x: number; y: number; childOf?: { x: number; y: number } };
  const placed: Placed[] = [];
  const rowY = (row: number) => row * (BOX_H + GAP_Y);
  placed.push({ node: focus, x: focusX, y: rowY(depth) });
  partners.forEach((p, j) => placed.push({ node: p, x: focusX + (j + 1) * slotW, y: rowY(depth) }));
  let level: { id: string; x: number }[] = [{ id: focus.id, x: focusX }];
  for (let g = 1; g <= depth; g++) {
    const next: { id: string; x: number }[] = [];
    const span = treeWidth / 2 ** g;
    level.forEach((item, i) => {
      parentsOf(item.id).forEach((p, j) => {
        const x = (i * 2 + j + 0.5) * span;
        placed.push({
          node: p,
          x,
          y: rowY(depth - g),
          childOf: { x: item.x, y: rowY(depth - g + 1) },
        });
        next.push({ id: p.id, x });
      });
    });
    level = next;
  }
  const kids = (index.children.get(focus.id) ?? [])
    .map((id) => index.people.get(id)!)
    .filter(Boolean)
    .sort((a, b) => (a.born ?? 9999) - (b.born ?? 9999));
  const shownKids = kids.slice(0, MAX_CHILDREN);
  const kidsWidth = shownKids.length * slotW;
  const kidsStart = Math.max(0, focusX - kidsWidth / 2);
  shownKids.forEach((k, i) => {
    placed.push({ node: k, x: kidsStart + (i + 0.5) * slotW, y: rowY(depth + 1) });
  });
  const totalWidth = Math.max(width, kidsStart + kidsWidth);
  const height = rowY(depth + (shownKids.length ? 2 : 1));
  const generationsRow = depth; // the focus person's row

  function keyed(e: KeyboardEvent, id: string) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setFocusId(id);
    }
  }

  return (
    <section
      aria-label="Family chart"
      className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-4"
    >
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="m-0 text-lg font-semibold">Family chart</h2>
          <p className="m-0 text-sm text-muted">Choose a box to move the chart to that person.</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm font-medium">
            Person
            <select
              value={focus.id}
              onChange={(e) => setFocusId(e.target.value)}
              className="min-h-11 rounded-lg border border-control bg-surface px-2 font-normal"
            >
              {[...index.people.values()]
                .sort((a, b) => a.name.localeCompare(b.name))
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Generations up
            <select
              value={generations}
              onChange={(e) => setGenerations(Number(e.target.value))}
              className="min-h-11 rounded-lg border border-control bg-surface px-2 font-normal"
            >
              {[1, 2, 3].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      <div className="overflow-x-auto">
        <svg
          width={totalWidth}
          height={height}
          viewBox={`0 0 ${totalWidth} ${height}`}
          role="group"
          aria-label={`Family chart for ${focus.name}`}
        >
          {placed.map(
            (p) =>
              p.childOf && (
                <path
                  key={`line-${p.node.id}-${p.x}`}
                  d={`M${p.x},${p.y + BOX_H} V${p.y + BOX_H + GAP_Y / 2} H${p.childOf.x} V${p.childOf.y}`}
                  fill="none"
                  stroke="var(--color-line)"
                  strokeWidth={1.5}
                />
              ),
          )}
          {shownKids.length > 0 && (
            <path
              d={`M${focusX},${rowY(generationsRow) + BOX_H} V${rowY(generationsRow + 1) - GAP_Y / 2} ${shownKids
                .map(
                  (_, i) =>
                    `M${kidsStart + (i + 0.5) * (BOX_W + GAP_X)},${rowY(generationsRow + 1) - GAP_Y / 2} V${rowY(generationsRow + 1)}`,
                )
                .join(
                  " ",
                )} M${kidsStart + 0.5 * (BOX_W + GAP_X)},${rowY(generationsRow + 1) - GAP_Y / 2} H${kidsStart + (shownKids.length - 0.5) * (BOX_W + GAP_X)}`}
              fill="none"
              stroke="var(--color-line)"
              strokeWidth={1.5}
            />
          )}
          {partners.length > 0 && (
            <path
              d={`M${focusX + BOX_W / 2},${rowY(generationsRow) + BOX_H / 2} H${focusX + partners.length * slotW - BOX_W / 2}`}
              fill="none"
              stroke="var(--color-control)"
              strokeWidth={1.5}
              strokeDasharray="4 3"
            />
          )}
          {placed.map((p) => {
            const isFocus = p.node.id === focus.id && p.y === rowY(generationsRow);
            return (
              <g
                key={`${p.node.id}-${p.x}-${p.y}`}
                role="button"
                tabIndex={0}
                aria-label={`${p.node.name}${years(p.node) ? `, ${years(p.node)}` : ""}`}
                onClick={() => setFocusId(p.node.id)}
                onKeyDown={(e) => keyed(e, p.node.id)}
                className="cursor-pointer"
                transform={`translate(${p.x - BOX_W / 2},${p.y})`}
              >
                <rect
                  width={BOX_W}
                  height={BOX_H}
                  rx={8}
                  fill={isFocus ? "var(--color-selected)" : "var(--color-surface)"}
                  stroke={isFocus ? "var(--color-accent)" : "var(--color-control)"}
                  strokeWidth={isFocus ? 2 : 1}
                />
                <text x={10} y={22} fontSize={13} fontWeight={600} fill="var(--color-ink)">
                  {short(p.node.name)}
                </text>
                <text x={10} y={40} fontSize={12} fill="var(--color-muted)">
                  {years(p.node)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      {kids.length > MAX_CHILDREN && (
        <p className="m-0 text-sm text-muted">
          Showing {MAX_CHILDREN} of {kids.length} children.
        </p>
      )}
      <Link to={`/projects/${projectId}/people/${focus.id}`} className="self-start">
        Open {focus.name}'s page
      </Link>
    </section>
  );
}
