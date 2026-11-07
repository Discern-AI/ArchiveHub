import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { lazy, Suspense, useCallback, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import {
  boxAround,
  DATE_ROLE_LABELS,
  layerForYear,
  familyPlacesApi,
  mapApi,
  PRECISION_LABELS,
  type BBox,
  type HistoricLayer,
  type MapFeature,
} from "../../lib/map";
import { SaveToProject } from "../../components/SaveToProject";
import { AddItemForm } from "./AddItemForm";
import { NearbyPanel } from "./NearbyPanel";
import type { View } from "./MapView";

const MapView = lazy(() => import("./MapView"));

const THIS_YEAR = new Date().getFullYear();
const FIRST_YEAR = 1700;
const SPANS: [string, number | null][] = [
  ["± 5 years", 5],
  ["± 10 years", 10],
  ["± 25 years", 25],
  ["Any date", null],
];
// Cheap Street, Newbury: where the pilot starts (SPEC §5).
const START = { lat: 51.400484, lng: -1.323134, zoom: 16 };

const select = "min-h-11 rounded-lg border border-control bg-surface px-2 font-normal";

function newPin(p: { lat: number; lng: number }): MapFeature {
  return {
    id: "new",
    layer: "private",
    kind: "memory",
    title: "Where the new item will go",
    summary: "",
    date_display: "",
    year_from: null,
    year_to: null,
    date_role: "undated",
    latitude: p.lat,
    longitude: p.lng,
    precision: "inferred",
    place: "",
    source: "",
    url: "",
    link: "",
    project_id: null,
    project_title: "",
    extra: {},
  };
}

function DateLine({ f }: { f: MapFeature }) {
  return (
    <span className="text-sm text-muted">
      <strong className="font-semibold text-ink">{DATE_ROLE_LABELS[f.date_role]}</strong>
      {f.date_display ? ` ${f.date_display}` : ""}
    </span>
  );
}

function FeatureList({
  title,
  note,
  items,
  layer,
  onSelect,
}: {
  title: string;
  note: string;
  items: MapFeature[];
  layer: "public" | "private";
  onSelect: (id: string) => void;
}) {
  const isPrivate = layer === "private";
  return (
    <section
      aria-label={title}
      className={`flex flex-col gap-1.5 rounded-lg border p-3 ${
        isPrivate ? "border-private bg-private-tint" : "border-line bg-surface"
      }`}
    >
      <h2 className="m-0 flex items-center gap-2 text-base font-semibold">
        <span
          aria-hidden="true"
          className={`inline-block ${isPrivate ? "size-3.5 rounded-[3px] bg-private" : "size-3.5 rounded-full bg-accent"}`}
        />
        {title} <span className="font-normal text-muted">({items.length})</span>
      </h2>
      <p className="m-0 text-sm text-muted">{note}</p>
      {items.length === 0 ? (
        <p className="m-0 text-sm text-muted">Nothing here for these years.</p>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-1 p-0">
          {items.map((f) => (
            <li key={f.id}>
              <button
                type="button"
                onClick={() => onSelect(f.id)}
                className="flex min-h-11 w-full cursor-pointer flex-col items-start rounded-lg border-0 bg-transparent px-2 py-1 text-left hover:bg-tint"
              >
                <span className="font-medium">{f.title}</span>
                <DateLine f={f} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function FeatureDetail({
  f,
  onBack,
  onRemoved,
}: {
  f: MapFeature;
  onBack: () => void;
  onRemoved: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isPrivate = f.layer === "private";
  const itemId = typeof f.extra.item_id === "string" ? f.extra.item_id : null;
  const fileId = typeof f.extra.file_id === "string" ? f.extra.file_id : null;

  async function remove() {
    try {
      await mapApi.deleteItem(itemId!);
      onRemoved();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <article className="flex flex-col gap-2">
      <button
        type="button"
        onClick={onBack}
        className="min-h-11 cursor-pointer self-start rounded-lg border-0 bg-transparent px-0 text-accent"
      >
        ← Back to the list
      </button>
      <span
        className={`self-start rounded-full px-2.5 py-0.5 text-sm font-semibold ${
          isPrivate ? "bg-private text-white" : "bg-tint text-ink"
        }`}
      >
        {isPrivate ? `Private: ${f.project_title}` : "Public record"}
      </span>
      <h2 className="m-0 font-serif text-2xl font-semibold">{f.title}</h2>
      <DateLine f={f} />
      {f.kind === "listed_building" && (
        <p className="m-0 text-sm text-muted">
          The date it was listed, not built. The listing entry often describes its age.
        </p>
      )}
      <p className="m-0 text-sm text-muted">
        {[f.place, PRECISION_LABELS[f.precision] ?? ""].filter(Boolean).join(" · ")}
      </p>
      {fileId && f.kind === "photo" && (
        <img
          src={`/api/v1/files/${fileId}/preview`}
          alt={f.title}
          className="max-h-60 self-start rounded-lg border border-line object-contain"
          onError={(e) => (e.currentTarget.style.display = "none")}
        />
      )}
      {f.summary && <p className="m-0 whitespace-pre-wrap">{f.summary}</p>}
      {f.source && <p className="m-0 text-sm text-muted">Source: {f.source}</p>}
      <div className="flex flex-wrap gap-3">
        {f.link && <Link to={f.link}>Open it</Link>}
        {f.url && (
          <a href={f.url} target="_blank" rel="noreferrer">
            See the original ↗
          </a>
        )}
      </div>
      {typeof f.extra.connector === "string" && typeof f.extra.record_id === "string" && (
        <SaveToProject connector={f.extra.connector} recordId={f.extra.record_id} />
      )}
      <NearbyPanel key={f.id} f={f} />
      {itemId &&
        (confirming ? (
          <div className="flex flex-wrap items-center gap-2 rounded-lg border border-line bg-surface p-3">
            <span>Take this off the map? Files and interviews stay in your project.</span>
            <button
              type="button"
              onClick={remove}
              className="min-h-11 cursor-pointer rounded-lg border-0 bg-warning px-3 font-medium text-white"
            >
              Remove from map
            </button>
            <button
              type="button"
              onClick={() => setConfirming(false)}
              className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3"
            >
              Keep it
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className="min-h-11 cursor-pointer self-start rounded-lg border border-control bg-surface px-3"
          >
            Remove from map…
          </button>
        ))}
      {error && <p className="m-0 text-warning">{error}</p>}
    </article>
  );
}

export function MapPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const layers = useQuery({ queryKey: ["map-layers"], queryFn: mapApi.layers });
  const places = useQuery({ queryKey: ["map-places"], queryFn: () => mapApi.places() });

  const urlLat = Number(params.get("lat"));
  const urlLng = Number(params.get("lng"));
  const [view, setView] = useState<View>(() =>
    params.get("lat") && params.get("lng") && Number.isFinite(urlLat) && Number.isFinite(urlLng)
      ? { lat: urlLat, lng: urlLng, zoom: 17 }
      : START,
  );
  const [bbox, setBbox] = useState<BBox>(() => boxAround(view.lat, view.lng));
  const [year, setYear] = useState(() => {
    const y = Number(params.get("year"));
    return y >= FIRST_YEAR && y <= THIS_YEAR ? y : 1900;
  });
  const [span, setSpan] = useState<number | null>(10);
  const [undated, setUndated] = useState(false);
  const [listed, setListed] = useState(true);
  const [showAreas, setShowAreas] = useState(true);
  const [layerChoice, setLayerChoice] = useState<string>("auto");
  const [opacity, setOpacity] = useState(0.85);
  const [alongside, setAlongside] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(() =>
    params.get("item") ? `item:${params.get("item")}` : null,
  );
  const [adding, setAdding] = useState(false);
  // Placing a family-tree place by hand (from the family page).
  const fixId = params.get("fix");
  const backParam = params.get("back") ?? "";
  const fixBack = backParam.startsWith("/projects/") ? backParam : "/map";
  const [fixError, setFixError] = useState<string | null>(null);
  async function saveFix(lat: number, lng: number) {
    try {
      await familyPlacesApi.update(fixId!, { latitude: lat, longitude: lng, precision: "town" });
      await qc.invalidateQueries({ queryKey: ["family-places"] });
      await qc.invalidateQueries({ queryKey: ["map-features"] });
      navigate(fixBack);
    } catch (err) {
      setFixError((err as Error).message);
    }
  }
  // Items sharing one pin, chosen on the map: the lists show just those.
  const [here, setHere] = useState<string[] | null>(null);
  const [point, setPoint] = useState<{ lat: number; lng: number } | null>(null);

  // A place chosen from search or the list (e.g. /map?place=cheap-street).
  const placeKey = params.get("place");
  const [placeApplied, setPlaceApplied] = useState<string | null>(null);
  if (placeKey && placeKey !== placeApplied && places.data) {
    const p = places.data.find((x) => x.key === placeKey);
    setPlaceApplied(placeKey);
    if (p) {
      const next = { lat: p.latitude, lng: p.longitude, zoom: p.kind === "town" ? 15 : 16.5 };
      setView(next);
      setBbox(boxAround(next.lat, next.lng));
    }
  }

  const years = span === null ? { from: null, to: null } : { from: year - span, to: year + span };
  const rounded = bbox.map((n) => Math.round(n * 1000) / 1000) as BBox;
  const features = useQuery({
    queryKey: ["map-features", rounded, years.from, years.to, undated, listed],
    queryFn: () => mapApi.features(rounded, years, undated, null, listed),
    placeholderData: keepPreviousData,
  });
  // Protected areas change slowly: ask per rough area, and keep them a while.
  const areaBox = bbox.map((n) => Math.round(n * 100) / 100) as BBox;
  const areas = useQuery({
    queryKey: ["map-areas", areaBox],
    queryFn: () => mapApi.areas(areaBox),
    enabled: showAreas,
    staleTime: 60 * 60 * 1000,
    placeholderData: keepPreviousData,
  });

  const historicLayers = layers.data?.historic ?? [];
  const historic: HistoricLayer | null =
    layerChoice === "none"
      ? null
      : layerChoice === "auto"
        ? layerForYear(historicLayers, year)
        : (historicLayers.find((l) => l.id === layerChoice) ?? null);

  const all = useMemo(
    () => [
      ...(features.data?.public ?? []),
      ...(features.data?.private ?? []),
      ...(features.data?.listed_buildings ?? []),
    ],
    [features.data],
  );
  const selected = all.find((f) => f.id === selectedId) ?? null;

  const onViewChange = useCallback((v: View, b: BBox) => {
    setView((old) =>
      Math.abs(old.lat - v.lat) < 1e-7 &&
      Math.abs(old.lng - v.lng) < 1e-7 &&
      Math.abs(old.zoom - v.zoom) < 0.001
        ? old
        : v,
    );
    setBbox(b);
  }, []);

  function chooseYear(y: number) {
    setYear(y);
    const next = new URLSearchParams(params);
    next.set("year", String(y));
    setParams(next, { replace: true });
  }

  const styleUrl = layers.data?.today.style;
  const mapProps = {
    styleUrl: styleUrl ?? "",
    view,
    onViewChange,
    features: adding && point ? [...all, newPin(point)] : all,
    selectedId,
    onSelect: (id: string) => {
      setAdding(false);
      setHere(null);
      setSelectedId(id);
    },
    onSelectMany: (ids: string[]) => {
      setAdding(false);
      setSelectedId(null);
      setHere(ids);
    },
    placing: adding || !!fixId,
    onPlace: (lat: number, lng: number) => (fixId ? saveFix(lat, lng) : setPoint({ lat, lng })),
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap items-end gap-x-4 gap-y-2 border-b border-line bg-surface px-4 py-3">
        <h1 className="m-0 mr-2 font-serif text-[28px] font-semibold">Time map</h1>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Place
          <select
            value={placeKey ?? ""}
            onChange={(e) => {
              const next = new URLSearchParams(params);
              next.set("place", e.target.value);
              setParams(next);
            }}
            className={select}
          >
            <option value="" disabled>
              Choose a place
            </option>
            {places.data?.map((p) => (
              <option key={p.key} value={p.key}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex min-w-[220px] flex-1 flex-col gap-1 text-sm font-medium">
          <span>
            Year: <output className="font-serif text-lg font-semibold">{year}</output>
            {span !== null && (
              <span className="font-normal text-muted">
                {" "}
                ({year - span}–{year + span})
              </span>
            )}
          </span>
          <input
            type="range"
            min={FIRST_YEAR}
            max={THIS_YEAR}
            value={year}
            onChange={(e) => chooseYear(Number(e.target.value))}
            className="min-h-11 accent-accent"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Years either side
          <select
            value={span === null ? "any" : String(span)}
            onChange={(e) => setSpan(e.target.value === "any" ? null : Number(e.target.value))}
            className={select}
          >
            {SPANS.map(([label, n]) => (
              <option key={label} value={n === null ? "any" : String(n)}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Old map
          <select
            value={layerChoice}
            onChange={(e) => setLayerChoice(e.target.value)}
            className={select}
          >
            <option value="auto">Matching the year</option>
            <option value="none">None, today's map only</option>
            {historicLayers.map((l) => (
              <option key={l.id} value={l.id} disabled={!l.available}>
                {l.title}
                {l.available ? "" : " (not available)"}
              </option>
            ))}
          </select>
        </label>
        {historic?.available && (
          <label className="flex flex-col gap-1 text-sm font-medium">
            Old map strength
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={opacity}
              onChange={(e) => setOpacity(Number(e.target.value))}
              className="min-h-11 w-28 accent-accent"
            />
          </label>
        )}
        <label className="flex min-h-11 items-center gap-2 text-sm font-medium">
          <input
            type="checkbox"
            checked={alongside}
            onChange={(e) => setAlongside(e.target.checked)}
            className="size-5"
          />
          Today alongside
        </label>
        <label className="flex min-h-11 items-center gap-2 text-sm font-medium">
          <input
            type="checkbox"
            checked={undated}
            onChange={(e) => setUndated(e.target.checked)}
            className="size-5"
          />
          Include undated
        </label>
        <label className="flex min-h-11 items-center gap-2 text-sm font-medium">
          <input
            type="checkbox"
            checked={listed}
            onChange={(e) => setListed(e.target.checked)}
            className="size-5"
          />
          Listed buildings
        </label>
        <label className="flex min-h-11 items-center gap-2 text-sm font-medium">
          <input
            type="checkbox"
            checked={showAreas}
            onChange={(e) => setShowAreas(e.target.checked)}
            className="size-5"
          />
          Protected areas
        </label>
      </div>

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <div
          className={`grid min-h-[50vh] flex-1 ${alongside ? "grid-cols-1 sm:grid-cols-2" : "grid-cols-1"}`}
        >
          {styleUrl ? (
            <Suspense fallback={<p className="p-4 text-muted">Loading the map…</p>}>
              <div className="relative flex flex-col">
                {alongside && (
                  <p className="m-0 bg-tint px-3 py-1 text-sm font-semibold">
                    {historic?.available
                      ? historic.title
                      : historic
                        ? `${year}: ${historic.title} isn't available here, so this is today's map`
                        : `${year}: no old map for this year, so this is today's map`}
                  </p>
                )}
                <div className="flex-1">
                  <MapView
                    {...mapProps}
                    label={`Map of ${year}`}
                    historic={historic}
                    historicOpacity={opacity}
                    names={features.data?.map_names ?? []}
                    areas={showAreas ? (areas.data ?? null) : null}
                  />
                </div>
              </div>
              {alongside && (
                <div className="relative flex flex-col border-t border-line sm:border-t-0 sm:border-l">
                  <p className="m-0 bg-tint px-3 py-1 text-sm font-semibold">Today</p>
                  <div className="flex-1">
                    <MapView
                      {...mapProps}
                      label="Map of today"
                      historic={null}
                      historicOpacity={0}
                      names={[]}
                    />
                  </div>
                </div>
              )}
            </Suspense>
          ) : (
            <p className="p-4 text-muted">
              {layers.isError ? "The map settings couldn't load." : "Loading the map…"}
            </p>
          )}
        </div>

        <aside
          aria-label="What's here"
          className="flex w-full flex-col gap-3 overflow-y-auto border-t border-line bg-page p-4 md:w-[380px] md:shrink-0 md:border-t-0 md:border-l"
        >
          {fixId ? (
            <div className="flex flex-col gap-3" aria-live="polite">
              <h2 className="m-0 font-serif text-2xl font-semibold">Place it on the map</h2>
              <p className="m-0">
                Click the map where <strong>{params.get("label") ?? "this place"}</strong> is. It's
                saved as your project's own placement, at town level, and its family events move
                there.
              </p>
              {fixError && <p className="m-0 text-warning">{fixError}</p>}
              <button
                type="button"
                onClick={() => saveFix(view.lat, view.lng)}
                className="min-h-11 cursor-pointer self-start rounded-lg border border-control bg-surface px-3"
              >
                Use the middle of the map
              </button>
              <button
                type="button"
                onClick={() => navigate(fixBack)}
                className="min-h-11 cursor-pointer self-start rounded-lg border-0 bg-transparent px-0 text-accent"
              >
                Cancel
              </button>
            </div>
          ) : adding ? (
            <AddItemForm
              point={point}
              view={view}
              onUseCentre={setPoint}
              onCancel={() => {
                setAdding(false);
                setPoint(null);
              }}
              onAdded={async (f) => {
                setAdding(false);
                setPoint(null);
                await qc.invalidateQueries({ queryKey: ["map-features"] });
                setSelectedId(f.id);
              }}
            />
          ) : selected ? (
            <FeatureDetail
              f={selected}
              onBack={() => setSelectedId(null)}
              onRemoved={async () => {
                setSelectedId(null);
                await qc.invalidateQueries({ queryKey: ["map-features"] });
              }}
            />
          ) : (
            <>
              <button
                type="button"
                onClick={() => {
                  setSelectedId(null);
                  setAdding(true);
                }}
                className="min-h-11 cursor-pointer self-start rounded-lg border-0 bg-accent px-4 font-medium text-white"
              >
                Add a memory or photo
              </button>
              {historic && !historic.available && (
                <p className="m-0 rounded-lg border border-line bg-surface p-3 text-sm">
                  <strong>{historic.title}:</strong> {historic.unavailable_reason} You're seeing
                  today's map, with names from the c.1900 map where they apply.
                </p>
              )}
              {!historic && layerChoice === "auto" && (
                <p className="m-0 text-sm text-muted">
                  No old map covers {year}; showing today's map.
                </p>
              )}
              {features.isError && (
                <p className="m-0 text-warning">
                  Couldn't load what's here. {(features.error as Error).message}
                </p>
              )}
              {here && (
                <div className="flex flex-wrap items-center gap-2 rounded-lg bg-tint p-3 text-sm">
                  <span>Showing the {here.length} items at the pin you chose.</span>
                  <button
                    type="button"
                    onClick={() => setHere(null)}
                    className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3"
                  >
                    Show everything in view
                  </button>
                </div>
              )}
              <FeatureList
                title="Public records"
                note="Checked records and claims anyone signed in can see."
                items={(features.data?.public ?? []).filter((f) => !here || here.includes(f.id))}
                layer="public"
                onSelect={setSelectedId}
              />
              <FeatureList
                title="Private: your projects"
                note="Only people in each project can see these."
                items={(features.data?.private ?? []).filter((f) => !here || here.includes(f.id))}
                layer="private"
                onSelect={setSelectedId}
              />
              {showAreas && (areas.data?.features.length ?? 0) > 0 && (
                <details className="rounded-lg border border-line bg-surface p-3">
                  <summary className="cursor-pointer font-semibold">
                    Protected areas nearby ({areas.data!.features.length})
                  </summary>
                  <p className="mt-1 mb-1 text-sm text-muted">
                    Dashed outlines on the map: conservation areas (blue), scheduled monuments
                    (brown), parks and gardens (green), battlefields (red). The year is when each
                    was designated. From Historic England, Open Government Licence.
                  </p>
                  <ul className="m-0 flex flex-col gap-1 pl-5 text-sm">
                    {areas.data!.features.map((a) => (
                      <li key={a.id}>
                        {a.properties.url ? (
                          <a href={a.properties.url} target="_blank" rel="noreferrer">
                            {a.properties.name} ↗
                          </a>
                        ) : (
                          a.properties.name
                        )}
                        <span className="text-muted">
                          {" "}
                          · {a.properties.label}
                          {a.properties.designated ? `, ${a.properties.designated}` : ""}
                        </span>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
              {showAreas &&
                areas.data?.notes.map((n) => (
                  <p key={n} className="m-0 text-sm text-muted">
                    {n}
                  </p>
                ))}
              {listed && (features.data?.listed_buildings?.length ?? 0) > 0 && (
                <details className="rounded-lg border border-line bg-surface p-3">
                  <summary className="cursor-pointer font-semibold">
                    <span
                      aria-hidden="true"
                      className="mr-2 inline-block size-3 rounded-full bg-listed align-middle"
                    />
                    Listed buildings standing today ({features.data!.listed_buildings!.length})
                  </summary>
                  <p className="mt-1 mb-1 text-sm text-muted">
                    From Historic England's National Heritage List. Shown for every year: the date
                    is when a building was listed, not when it was built, so check whether it stood
                    in {year}.
                  </p>
                  <ul className="m-0 flex list-none flex-col gap-1 p-0">
                    {features
                      .data!.listed_buildings!.filter((f) => !here || here.includes(f.id))
                      .map((f) => (
                        <li key={f.id}>
                          <button
                            type="button"
                            onClick={() => setSelectedId(f.id)}
                            className="flex min-h-11 w-full cursor-pointer flex-col items-start rounded-lg border-0 bg-transparent px-2 py-1 text-left hover:bg-tint"
                          >
                            <span className="font-medium">{f.title}</span>
                            <DateLine f={f} />
                          </button>
                        </li>
                      ))}
                  </ul>
                </details>
              )}
              {(features.data?.map_names.length ?? 0) > 0 && (
                <p className="m-0 text-sm text-muted">
                  {features.data!.map_names.length} names from the OS six-inch map (c.1888–1913) are
                  shown as brown labels.
                </p>
              )}
              {features.data?.notes.map((n) => (
                <p key={n} className="m-0 text-sm text-muted">
                  {n}
                </p>
              ))}
              <p className="m-0 text-sm text-muted">
                A missing pin doesn't mean nothing happened here, only that we don't hold a dated,
                placed record of it yet. <Link to="/search">Search</Link> looks further.
              </p>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
