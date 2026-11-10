/**
 * Lifeline data and the rules for reading it. Each end of a life is a window
 * (earliest, latest); "about 1850" is a few years either side, "before 1953" has no
 * earliest year. Nothing here guesses a date: unknown stays unknown and is labelled.
 */
import { request } from "./api";

export interface LifeEnd {
  earliest: number | null;
  latest: number | null;
  certainty: "exact" | "about" | "before" | "after" | "range" | "baptised" | "buried";
  text: string;
  from: string;
}

export interface LifePlace {
  kind: "birth" | "baptism" | "residence" | "death" | "burial";
  place: string;
  latitude: number | null;
  longitude: number | null;
  located: "checked" | "suggested" | "not yet";
  year_from: number | null;
  year_to: number | null;
  date_text: string;
}

export interface LifePerson {
  id: string;
  name: string;
  surname: string;
  sex: string;
  living: boolean;
  parents: string[];
  partners: string[];
  start: LifeEnd | null;
  end: LifeEnd | null;
  places: LifePlace[];
}

export type OverlayKind = "war" | "law" | "records" | "calendar" | "local" | "custom";

export interface Overlay {
  id: string;
  kind: OverlayKind;
  title: string;
  year_from: number;
  year_to: number | null;
  date_text: string;
  area: string;
  note: string;
  source_title: string;
  source_url: string;
  builtin: boolean;
}

export interface LifelineData {
  people: LifePerson[];
  overlays: Overlay[];
  kinds: string[];
  living_private: number;
  this_year: number;
  about_years: number;
}

export const LAYERS: { kind: string; label: string }[] = [
  { kind: "war", label: "Wars" },
  { kind: "records", label: "Censuses and registration" },
  { kind: "law", label: "Laws" },
  { kind: "calendar", label: "Calendar" },
  { kind: "family", label: "Family events" },
  { kind: "custom", label: "Your markers" },
];

export const lifelineApi = {
  get: (projectId: string) =>
    request<LifelineData>("GET", `/api/v1/projects/${projectId}/lifeline`),
  addMarker: (projectId: string, body: { title: string; year_from: number; year_to?: number }) =>
    request<Overlay>("POST", `/api/v1/projects/${projectId}/lifeline/markers`, body),
  deleteMarker: (projectId: string, id: string) =>
    request<void>("DELETE", `/api/v1/projects/${projectId}/lifeline/markers/${id}`),
  savePreset: (projectId: string, kinds: string[]) =>
    request<{ kinds: string[] }>("PUT", `/api/v1/projects/${projectId}/lifeline/preset`, {
      kinds,
    }),
};

/** Longest life we'll assume when a death isn't recorded, for "possibly alive". */
export const MAX_LIFE = 105;
/** How close a birth or death counts as "just before" or "just after" the chosen year. */
export const NEAR_YEARS = 5;

export type Status =
  | "alive" // the records place them alive in that year
  | "uncertain" // they may have been: a date is approximate or unknown
  | "recently-died"
  | "soon-born"
  | "not-alive"
  | "private"; // living, so their dates aren't shown

/** The years a life could cover, and the years it certainly covers. */
export function spans(p: LifePerson): {
  possibleFrom: number | null;
  possibleTo: number | null;
  sureFrom: number | null;
  sureTo: number | null;
} {
  const s = p.start;
  const e = p.end;
  // A residence recorded in a year shows they were alive that year.
  const resYears = p.places
    .filter((pl) => pl.kind === "residence")
    .map((pl) => pl.year_to ?? pl.year_from)
    .filter((y): y is number => y !== null);
  const firstRes = resYears.length ? Math.min(...resYears) : null;
  const lastRes = resYears.length ? Math.max(...resYears) : null;
  let sureFrom = s ? (s.latest ?? null) : null;
  if (firstRes !== null) sureFrom = sureFrom === null ? firstRes : Math.min(sureFrom, firstRes);
  let sureTo = e ? (e.earliest ?? null) : null;
  if (lastRes !== null) sureTo = sureTo === null ? lastRes : Math.max(sureTo, lastRes);
  // Open-ended windows ("before 1953", death unknown) are bounded by the other end of the
  // life and the longest life we assume, never by a guessed date.
  let possibleFrom = s?.earliest ?? null;
  let possibleTo = e?.latest ?? null;
  const knownTo = possibleTo ?? sureTo;
  const knownFrom = possibleFrom ?? sureFrom;
  if (possibleFrom === null)
    possibleFrom = knownTo !== null ? knownTo - MAX_LIFE : sureFrom !== null ? sureFrom : null;
  if (possibleTo === null)
    possibleTo = knownFrom !== null ? knownFrom + MAX_LIFE : sureTo !== null ? sureTo : null;
  if (s && s.earliest === null && sureFrom !== null && knownTo !== null)
    possibleFrom = Math.min(sureFrom, knownTo - MAX_LIFE);
  return { possibleFrom, possibleTo, sureFrom, sureTo };
}

export function statusAt(p: LifePerson, year: number): Status {
  if (p.living) return "private";
  const { possibleFrom, possibleTo, sureFrom, sureTo } = spans(p);
  if (possibleFrom === null || possibleTo === null) return "not-alive"; // no dates at all
  if (sureFrom !== null && sureTo !== null && sureFrom <= year && year <= sureTo) return "alive";
  if (possibleFrom <= year && year <= possibleTo) return "uncertain";
  if (p.end && year > possibleTo && year - possibleTo <= NEAR_YEARS) return "recently-died";
  if (p.start && year < possibleFrom && possibleFrom - year <= NEAR_YEARS) return "soon-born";
  return "not-alive";
}

/** "about 1850", "before 1953", "1990–1992"; empty when unknown. */
export function endLabel(e: LifeEnd | null): string {
  if (!e) return "";
  const y = e.earliest ?? e.latest;
  switch (e.certainty) {
    case "about":
      return `about ${(e.earliest! + e.latest!) / 2}`;
    case "before":
      return `before ${e.latest}`;
    case "after":
      return `after ${e.earliest}`;
    case "range":
      return `${e.earliest}–${e.latest}`;
    case "baptised":
      return `baptised ${e.latest}`;
    case "buried":
      return `buried ${e.latest}`;
    default:
      return `${y}`;
  }
}

export function lifeLabel(p: LifePerson): string {
  if (p.living) return "Living: dates private";
  const a = endLabel(p.start);
  const b = endLabel(p.end);
  if (a && b) return `${a} – ${b}`;
  if (a) return `${a} – death not recorded`;
  if (b) return `birth not recorded – ${b}`;
  return "No dates recorded";
}

/** Why someone is uncertain in a year, in words. */
export function whyUncertain(p: LifePerson, year: number): string {
  const { sureFrom, sureTo } = spans(p);
  if (!p.start) return "birth not recorded";
  if (!p.end) return "death not recorded";
  if (sureFrom === null || year < sureFrom) return `born ${endLabel(p.start)}`;
  if (sureTo === null || year > sureTo) return `died ${endLabel(p.end)}`;
  return "dates approximate";
}

export function aliveCounts(
  people: LifePerson[],
  from: number,
  to: number,
): { year: number; alive: number; uncertain: number }[] {
  const out = [];
  for (let y = from; y <= to; y++) {
    let alive = 0;
    let uncertain = 0;
    for (const p of people) {
      const s = statusAt(p, y);
      if (s === "alive") alive++;
      else if (s === "uncertain") uncertain++;
    }
    out.push({ year: y, alive, uncertain });
  }
  return out;
}

function placeYear(pl: LifePlace): number | null {
  return pl.year_from ?? pl.year_to;
}

/** Recorded places with a location, in date order, up to and including the year. */
export function placesBy(p: LifePerson, year: number): LifePlace[] {
  return p.places.filter((pl) => {
    const y = placeYear(pl);
    return pl.latitude !== null && pl.longitude !== null && y !== null && y <= year;
  });
}

/** Where the records last put them, by that year: a recorded place, not a guess. */
export function lastPlace(p: LifePerson, year: number): LifePlace | null {
  const seen = placesBy(p, year);
  return seen.length ? seen[seen.length - 1] : null;
}

/** Generation numbers: people without parents in the tree are generation 1. */
export function generations(people: LifePerson[]): Map<string, number> {
  const byId = new Map(people.map((p) => [p.id, p]));
  const gen = new Map<string, number>();
  const visit = (id: string, seen: Set<string>): number => {
    const known = gen.get(id);
    if (known !== undefined) return known;
    if (seen.has(id)) return 1; // a loop in the data; don't recurse forever
    seen.add(id);
    const p = byId.get(id);
    const parents = (p?.parents ?? []).filter((x) => byId.has(x));
    const g = parents.length ? Math.max(...parents.map((x) => visit(x, seen))) + 1 : 1;
    gen.set(id, g);
    return g;
  };
  for (const p of people) visit(p.id, new Set());
  return gen;
}

/** A person, their ancestors and their descendants. */
export function directLine(people: LifePerson[], focus: string): Set<string> {
  const byId = new Map(people.map((p) => [p.id, p]));
  const children = new Map<string, string[]>();
  for (const p of people)
    for (const parent of p.parents) children.set(parent, [...(children.get(parent) ?? []), p.id]);
  const out = new Set<string>([focus]);
  const up = [focus];
  while (up.length) {
    const id = up.pop()!;
    for (const parent of byId.get(id)?.parents ?? [])
      if (!out.has(parent)) {
        out.add(parent);
        up.push(parent);
      }
  }
  const down = [focus];
  while (down.length) {
    const id = down.pop()!;
    for (const child of children.get(id) ?? [])
      if (!out.has(child)) {
        out.add(child);
        down.push(child);
      }
  }
  return out;
}

/** The years to draw: a little before the earliest life, up to this year. */
export function yearRange(data: LifelineData): [number, number] {
  let lo = Infinity;
  for (const p of data.people) {
    const s = spans(p).possibleFrom;
    if (s !== null) lo = Math.min(lo, s);
  }
  for (const o of data.overlays) if (o.kind === "custom") lo = Math.min(lo, o.year_from);
  if (!Number.isFinite(lo)) lo = data.this_year - 150;
  return [Math.floor((lo - 5) / 10) * 10, data.this_year];
}
