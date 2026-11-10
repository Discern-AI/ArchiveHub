/**
 * Where people were recorded, up to the chosen year. Points are the last recorded place
 * for each person; dashed lines join their recorded places in date order. The map is
 * made once and its data swapped as the year moves, so it never reloads.
 */
import type { Map as MlMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { useEffect, useRef, useState } from "react";
import { lastPlace, placesBy, type LifePerson } from "../../lib/lifeline";

interface Props {
  styleUrl: string;
  people: LifePerson[];
  year: number;
  onSelect: (id: string) => void;
}

type Feature = {
  type: "Feature";
  geometry: { type: "Point" | "LineString"; coordinates: number[] | number[][] };
  properties: Record<string, string | number>;
};

export function lifelineFeatures(people: LifePerson[], year: number) {
  const points: Feature[] = [];
  const lines: Feature[] = [];
  for (const p of people) {
    const here = lastPlace(p, year);
    if (!here) continue;
    points.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [here.longitude!, here.latitude!] },
      properties: {
        id: p.id,
        name: p.name,
        place: here.place,
        when: here.date_text,
        suggested: here.located === "suggested" ? 1 : 0,
      },
    });
    const seen = placesBy(p, year);
    const coords = seen.map((pl) => [pl.longitude!, pl.latitude!]);
    const distinct = coords.filter(
      (c, i) => i === 0 || c[0] !== coords[i - 1][0] || c[1] !== coords[i - 1][1],
    );
    if (distinct.length > 1)
      lines.push({
        type: "Feature",
        geometry: { type: "LineString", coordinates: distinct },
        properties: { id: p.id },
      });
  }
  return {
    points: { type: "FeatureCollection" as const, features: points },
    lines: { type: "FeatureCollection" as const, features: lines },
  };
}

export default function LifelineMap({ styleUrl, people, year, onSelect }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(false);
  const onSelectRef = useRef(onSelect);
  useEffect(() => {
    onSelectRef.current = onSelect;
  });

  useEffect(() => {
    let cancelled = false;
    import("maplibre-gl")
      .then((ml) => {
        if (cancelled || !container.current) return;
        ml.setWorkerUrl(workerUrl);
        const map = new ml.Map({
          container: container.current,
          style: styleUrl,
          center: [-2.6, 54.2],
          zoom: 4.6,
          attributionControl: { compact: true },
        });
        mapRef.current = map;
        map.addControl(new ml.NavigationControl({ showCompass: false }), "top-right");
        map.on("load", () => {
          map.addSource("moves", {
            type: "geojson",
            data: { type: "FeatureCollection", features: [] },
          });
          map.addSource("people", {
            type: "geojson",
            data: { type: "FeatureCollection", features: [] },
          });
          map.addLayer({
            id: "moves",
            type: "line",
            source: "moves",
            paint: {
              "line-color": "#6b3fa0",
              "line-width": 2,
              "line-dasharray": [2, 2],
              "line-opacity": 0.7,
            },
          });
          map.addLayer({
            id: "people",
            type: "circle",
            source: "people",
            paint: {
              "circle-radius": 7,
              "circle-color": "#6b3fa0",
              "circle-stroke-color": "#ffffff",
              "circle-stroke-width": 2,
              "circle-opacity": ["case", ["==", ["get", "suggested"], 1], 0.55, 1],
            },
          });
          map.on("click", "people", (e) => {
            const id = e.features?.[0]?.properties?.id;
            if (typeof id === "string") onSelectRef.current(id);
          });
          map.on("mouseenter", "people", () => (map.getCanvas().style.cursor = "pointer"));
          map.on("mouseleave", "people", () => (map.getCanvas().style.cursor = ""));
          setReady(true);
        });
      })
      .catch(() => setError(true));
    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [styleUrl]);

  // Frame everyone's recorded places once; moving the year doesn't move the view.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const coords = people.flatMap((p) =>
      p.places
        .filter((pl) => pl.latitude !== null && pl.longitude !== null)
        .map((pl) => [pl.longitude!, pl.latitude!] as [number, number]),
    );
    if (!coords.length) return;
    const lngs = coords.map((c) => c[0]);
    const lats = coords.map((c) => c[1]);
    map.fitBounds(
      [
        [Math.min(...lngs), Math.min(...lats)],
        [Math.max(...lngs), Math.max(...lats)],
      ],
      { padding: 48, maxZoom: 9, duration: 0 },
    );
  }, [ready, people]);

  // Swap the data when the year or people change: no reload.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const { points, lines } = lifelineFeatures(people, year);
    (map.getSource("people") as { setData: (d: unknown) => void } | undefined)?.setData(points);
    (map.getSource("moves") as { setData: (d: unknown) => void } | undefined)?.setData(lines);
  }, [ready, people, year]);

  if (error) return <p className="m-0 text-sm text-warning">The map couldn't load.</p>;
  return (
    <div className="h-72 w-full overflow-hidden rounded-lg border border-line">
      {/* Sized by height, not inset: MapLibre makes its element position: relative. */}
      <div ref={container} className="h-full w-full" />
    </div>
  );
}
