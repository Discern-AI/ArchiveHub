/**
 * One MapLibre map. Public items are round pins; private items are square pins marked
 * "Private" (ADR-032). Pins are real buttons, so they work with a keyboard and screen
 * reader. Old map names are drawn as labels, like the words on the old map itself.
 */
import { useEffect, useRef, useState } from "react";
import type { Map as MlMap, Marker as MlMarker } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// MapLibre finds its worker relative to its own file, which bundling breaks, so Vite
// bundles the worker and we pass its URL.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { groupPins, type BBox, type HistoricLayer, type MapFeature } from "../../lib/map";

export interface View {
  lat: number;
  lng: number;
  zoom: number;
}

export interface MapViewProps {
  label: string;
  styleUrl: string;
  historic: HistoricLayer | null;
  historicOpacity: number;
  view: View;
  onViewChange: (view: View, bbox: BBox) => void;
  features: MapFeature[];
  names: MapFeature[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  /** Several items share one spot (e.g. records placed at street level). */
  onSelectMany: (ids: string[]) => void;
  placing: boolean;
  onPlace: (lat: number, lng: number) => void;
}

const PIN =
  "flex cursor-pointer items-center justify-center border-2 border-white text-[11px] font-bold text-white shadow-[0_1px_4px_rgba(0,0,0,0.45)]";

function pinElement(group: MapFeature[], selectedId: string | null): HTMLButtonElement {
  const f = group[0];
  const el = document.createElement("button");
  el.type = "button";
  const isPrivate = f.layer === "private";
  const isListed = f.kind === "listed_building";
  const many = group.length > 1;
  const what = isPrivate ? "private" : isListed ? "listed building" : "public record";
  const label = many
    ? `${group.length} ${isPrivate ? "private items" : isListed ? "listed buildings" : "public records"} here`
    : `${f.title}${f.date_display ? `, ${isListed ? "listed " : ""}${f.date_display}` : ""} (${what})`;
  el.setAttribute("aria-label", label);
  el.title = label;
  el.dataset.layer = f.layer;
  const selected = group.some((g) => g.id === selectedId);
  el.className = `${PIN} ${
    isPrivate
      ? "size-7 rounded-[5px] bg-private"
      : isListed
        ? "size-5 rounded-full bg-listed text-[10px]"
        : "size-7 rounded-full bg-accent"
  } ${selected ? "outline-3 outline-focus" : ""}`;
  el.textContent = many
    ? String(group.length)
    : f.kind === "family_event"
      ? "F"
      : isPrivate
        ? "P"
        : isListed
          ? "L"
          : "";
  return el;
}

function namesGeoJson(names: MapFeature[]) {
  return {
    type: "FeatureCollection" as const,
    features: names.map((n) => ({
      type: "Feature" as const,
      properties: { title: n.title },
      geometry: { type: "Point" as const, coordinates: [n.longitude, n.latitude] },
    })),
  };
}

function bboxOf(map: MlMap): BBox {
  const b = map.getBounds();
  return [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()];
}

export default function MapView(props: MapViewProps) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const markers = useRef<MlMarker[]>([]);
  const latest = useRef(props);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    latest.current = props;
  });

  // Create the map once.
  useEffect(() => {
    let cancelled = false;
    let map: MlMap | null = null;
    import("maplibre-gl")
      .then((ml) => {
        if (cancelled || !container.current) return;
        ml.setWorkerUrl(workerUrl);
        const v = latest.current.view;
        map = new ml.Map({
          container: container.current,
          style: latest.current.styleUrl,
          center: [v.lng, v.lat],
          zoom: v.zoom,
          attributionControl: { compact: false },
        });
        mapRef.current = map;
        map.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
        map.addControl(new ml.ScaleControl({ unit: "metric" }), "bottom-left");
        map.on("load", () => {
          setReady(true);
          const m = mapRef.current!;
          latest.current.onViewChange(
            { lat: m.getCenter().lat, lng: m.getCenter().lng, zoom: m.getZoom() },
            bboxOf(m),
          );
        });
        map.on("moveend", () => {
          const m = mapRef.current!;
          latest.current.onViewChange(
            { lat: m.getCenter().lat, lng: m.getCenter().lng, zoom: m.getZoom() },
            bboxOf(m),
          );
        });
        map.on("click", (e) => {
          if (latest.current.placing) latest.current.onPlace(e.lngLat.lat, e.lngLat.lng);
        });
        map.on("error", (e) => {
          // Tile hiccups are normal; only say so if the map itself didn't start.
          if (!map?.isStyleLoaded()) setError(e.error?.message ?? "The map couldn't load.");
        });
      })
      .catch(() => setError("The map couldn't load in this browser."));
    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = null;
    };
  }, []);

  // Follow the shared view (the other map, or a place chosen in the controls).
  const { lat, lng, zoom } = props.view;
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const c = map.getCenter();
    if (
      Math.abs(c.lat - lat) > 1e-6 ||
      Math.abs(c.lng - lng) > 1e-6 ||
      Math.abs(map.getZoom() - zoom) > 0.01
    ) {
      map.jumpTo({ center: [lng, lat], zoom });
    }
  }, [lat, lng, zoom, ready]);

  // Historic tiles.
  const tilejson = props.historic?.available ? props.historic.tilejson : undefined;
  const attribution = props.historic?.attribution;
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    if (map.getLayer("historic")) map.removeLayer("historic");
    if (map.getSource("historic")) map.removeSource("historic");
    if (!tilejson) return;
    map.addSource("historic", { type: "raster", url: tilejson, tileSize: 256, attribution });
    map.addLayer(
      {
        id: "historic",
        type: "raster",
        source: "historic",
        paint: { "raster-opacity": latest.current.historicOpacity },
      },
      map.getLayer("old-map-names") ? "old-map-names" : undefined,
    );
  }, [tilejson, attribution, ready]);

  useEffect(() => {
    const map = mapRef.current;
    if (map && ready && map.getLayer("historic")) {
      map.setPaintProperty("historic", "raster-opacity", props.historicOpacity);
    }
  }, [props.historicOpacity, ready]);

  // Old map names as labels.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const data = namesGeoJson(props.names);
    const source = map.getSource("old-map-names") as { setData?: (d: unknown) => void } | undefined;
    if (source?.setData) {
      source.setData(data);
      return;
    }
    map.addSource("old-map-names", { type: "geojson", data });
    map.addLayer({
      id: "old-map-names",
      type: "symbol",
      source: "old-map-names",
      layout: {
        "text-field": ["get", "title"],
        "text-size": 11,
        "text-font": ["Noto Sans Italic"],
      },
      paint: { "text-color": "#5b3a12", "text-halo-color": "#fffaf0", "text-halo-width": 1.5 },
    });
  }, [props.names, ready]);

  // Pins.
  const { features, selectedId } = props;
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    let cancelled = false;
    import("maplibre-gl").then((ml) => {
      if (cancelled) return;
      markers.current.forEach((m) => m.remove());
      // Private pins go on top, so a family item is never hidden under a public one.
      markers.current = groupPins(features).map((group) => {
        const el = pinElement(group, selectedId);
        el.addEventListener("click", (e) => {
          e.stopPropagation();
          if (group.length > 1) latest.current.onSelectMany(group.map((g) => g.id));
          else latest.current.onSelect(group[0].id);
        });
        return new ml.Marker({ element: el })
          .setLngLat([group[0].longitude, group[0].latitude])
          .addTo(map);
      });
    });
    return () => {
      cancelled = true;
    };
  }, [features, selectedId, ready]);

  useEffect(() => {
    const canvas = mapRef.current?.getCanvas();
    if (canvas) canvas.style.cursor = props.placing ? "crosshair" : "";
  }, [props.placing]);

  return (
    <div className="relative h-full min-h-[320px] w-full">
      {/* MapLibre's CSS makes its container position: relative, so position a wrapper. */}
      <div className="absolute inset-0">
        <div ref={container} role="region" aria-label={props.label} className="h-full w-full" />
      </div>
      {error && (
        <p className="absolute inset-x-4 top-4 m-0 rounded-lg bg-surface p-3 text-warning shadow">
          {error} The lists beside the map still show everything here.
        </p>
      )}
    </div>
  );
}
