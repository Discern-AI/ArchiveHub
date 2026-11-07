/** Time map and Search API (mirrors services/api/timemap and services/api/search). */
import { request } from "./api";

export interface HistoricLayer {
  id: string;
  title: string;
  years: [number, number];
  min_zoom: number;
  attribution: string;
  available: boolean;
  tilejson?: string;
  unavailable_reason?: string;
}

export interface MapLayers {
  today: { title: string; style: string; attribution: string };
  historic: HistoricLayer[];
}

export type DateRole = "event" | "made" | "record_covers" | "map_survey" | "listed" | "undated";

export interface MapFeature {
  id: string;
  layer: "public" | "private";
  kind: string;
  title: string;
  summary: string;
  date_display: string;
  year_from: number | null;
  year_to: number | null;
  date_role: DateRole;
  latitude: number;
  longitude: number;
  precision: string;
  place: string;
  source: string;
  url: string;
  link: string;
  project_id: string | null;
  project_title: string;
  extra: Record<string, unknown>;
}

export interface MapFeatures {
  public: MapFeature[];
  private: MapFeature[];
  map_names: MapFeature[];
  /** Listed buildings standing today (Historic England); not filtered by year. */
  listed_buildings: MapFeature[];
  notes: string[];
}

export interface MapPlace {
  id: string;
  key: string;
  name: string;
  kind: string;
  latitude: number;
  longitude: number;
  precision: string;
  geocode_source: string;
  note: string;
}

export interface NewMapItem {
  kind: "memory" | "photo" | "document" | "interview";
  title: string;
  text: string;
  latitude: number;
  longitude: number;
  location_note: string;
  precision: string;
  date_text: string;
  year_from: number | null;
  year_to: number | null;
  date_role: "event" | "made";
  file_id?: string | null;
  place_id?: string | null;
}

/** west, south, east, north */
export type BBox = [number, number, number, number];

export interface SearchResult {
  id: string;
  title: string;
  snippet: string;
  date: string;
  place: string;
  source: string;
  link: string;
  url: string;
  project_title: string;
  extra: Record<string, unknown>;
}

export interface SearchGroup {
  key: string;
  label: string;
  layer: "public" | "private";
  searched: string;
  results: SearchResult[];
  count: number;
  more: boolean;
}

export interface SearchResponse {
  query: string;
  words: string[];
  groups: SearchGroup[];
  not_searched: { label: string; reason: string }[];
}

export const DATE_ROLE_LABELS: Record<DateRole, string> = {
  event: "Happened",
  made: "Made or taken",
  record_covers: "Record covers",
  listed: "Listed",
  map_survey: "Map surveyed",
  undated: "Undated",
};

export const PRECISION_LABELS: Record<string, string> = {
  exact: "Exact location",
  street: "Street-level location",
  parish: "Parish-level location",
  town: "Town-level location",
  inferred: "Approximate location",
  unknown: "Location uncertain",
};

export const mapApi = {
  layers: () => request<MapLayers>("GET", "/api/v1/map/layers"),
  places: (q = "") =>
    request<MapPlace[]>("GET", `/api/v1/map/places${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  features: (
    bbox: BBox,
    years: { from: number | null; to: number | null },
    undated: boolean,
    projectId?: string | null,
    listed = false,
  ) => {
    const params = new URLSearchParams({ bbox: bbox.map((n) => n.toFixed(5)).join(",") });
    if (years.from !== null) params.set("year_from", String(years.from));
    if (years.to !== null) params.set("year_to", String(years.to));
    if (undated) params.set("undated", "true");
    if (listed) params.set("listed", "true");
    if (projectId) params.set("project_id", projectId);
    return request<MapFeatures>("GET", `/api/v1/map/features?${params}`);
  },
  addItem: (projectId: string, item: NewMapItem) =>
    request<MapFeature>("POST", `/api/v1/projects/${projectId}/map-items`, item),
  deleteItem: (itemId: string) => request<void>("DELETE", `/api/v1/map-items/${itemId}`),
  search: (q: string) =>
    request<SearchResponse>("GET", `/api/v1/search?q=${encodeURIComponent(q)}`),
};

/** The historic layer to show for a year: the one whose years contain it, if any. */
export function layerForYear(layers: HistoricLayer[], year: number): HistoricLayer | null {
  const fits = layers.filter((l) => l.years[0] <= year && year <= l.years[1]);
  // Prefer the most detailed (highest minimum zoom), then the narrowest period.
  fits.sort(
    (a, b) => b.min_zoom - a.min_zoom || a.years[1] - a.years[0] - (b.years[1] - b.years[0]),
  );
  return fits[0] ?? null;
}

/** A small box around a point, for before the map has measured itself. */
export function boxAround(lat: number, lng: number, halfLat = 0.008, halfLng = 0.013): BBox {
  return [lng - halfLng, lat - halfLat, lng + halfLng, lat + halfLat];
}

/**
 * Items at exactly the same spot and layer share one pin (records placed at street
 * level all sit on the street's point). Public groups first, so private pins draw on top.
 */
export function groupPins(features: MapFeature[]): MapFeature[][] {
  const groups = new Map<string, MapFeature[]>();
  for (const f of features) {
    const kind = f.kind === "listed_building" ? "listed" : f.layer;
    const key = `${kind}|${f.latitude.toFixed(6)}|${f.longitude.toFixed(6)}`;
    const g = groups.get(key);
    if (g) g.push(f);
    else groups.set(key, [f]);
  }
  return [...groups.values()].sort((a, b) =>
    a[0].layer === b[0].layer ? 0 : a[0].layer === "private" ? 1 : -1,
  );
}
