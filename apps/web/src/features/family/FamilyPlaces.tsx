/** Where the places in a family tree are: suggested from named sources, checked by people. */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { familyPlacesApi, PRECISION_LABELS, type FamilyPlace } from "../../lib/map";

const STATUS: Record<FamilyPlace["status"], string> = {
  suggested: "Suggested, not yet checked",
  confirmed: "Checked",
  rejected: "Marked as the wrong place",
  not_found: "Not found",
};

const small =
  "min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3 text-sm font-medium";

export function FamilyPlaces({ projectId }: { projectId: string }) {
  const qc = useQueryClient();
  const places = useQuery({
    queryKey: ["family-places", projectId],
    queryFn: () => familyPlacesApi.list(projectId),
  });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function refresh() {
    await qc.invalidateQueries({ queryKey: ["family-places", projectId] });
    await qc.invalidateQueries({ queryKey: ["map-features"] });
  }

  async function locate() {
    setBusy(true);
    setMessage(null);
    try {
      const r = await familyPlacesApi.locate(projectId);
      setMessage(
        `Suggested ${r.suggested} location${r.suggested === 1 ? "" : "s"}; ${r.not_found} not found.`,
      );
      await refresh();
    } catch (err) {
      setMessage((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function decide(p: FamilyPlace, status: "confirmed" | "rejected") {
    try {
      await familyPlacesApi.update(p.id, { status });
      await refresh();
    } catch (err) {
      setMessage((err as Error).message);
    }
  }

  const data = places.data;
  if (!data || (data.places.length === 0 && data.not_looked_up === 0)) return null;
  const back = `/projects/${projectId}/people`;

  return (
    <section
      aria-label="Places in this tree"
      className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-4"
    >
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="m-0 text-lg font-semibold">Places in this tree</h2>
          <p className="m-0 text-sm text-muted">
            Births, baptisms, deaths and burials appear on the time map once a place has a location,
            privately for this project. Living people never appear.
          </p>
        </div>
        {data.not_looked_up > 0 && (
          <button
            type="button"
            onClick={locate}
            disabled={busy}
            className="min-h-11 cursor-pointer rounded-lg border-0 bg-accent px-4 font-medium text-white disabled:opacity-60"
          >
            {busy
              ? "Looking…"
              : `Find locations for ${data.not_looked_up} place${data.not_looked_up === 1 ? "" : "s"}`}
          </button>
        )}
      </div>
      {message && <p className="m-0 text-sm">{message}</p>}
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {data.places.map((p) => (
          <li key={p.id} className="flex flex-col gap-1 border-t border-line-soft pt-2">
            <div className="flex flex-wrap items-baseline gap-2">
              <strong>{p.text}</strong>
              <span className="text-sm text-muted">
                {p.uses} event{p.uses === 1 ? "" : "s"} · {STATUS[p.status]}
              </span>
            </div>
            {p.latitude !== null && p.status !== "rejected" && (
              <span className="text-sm text-muted">
                {PRECISION_LABELS[p.precision] ?? p.precision}. From: {p.source}
              </span>
            )}
            {p.candidates > 1 && p.status === "suggested" && (
              <span className="text-sm text-warning">
                {p.candidates} places have this name; check it's the right one.
              </span>
            )}
            <div className="flex flex-wrap gap-2">
              {p.status === "suggested" && (
                <>
                  <button type="button" className={small} onClick={() => decide(p, "confirmed")}>
                    Right place
                  </button>
                  <button type="button" className={small} onClick={() => decide(p, "rejected")}>
                    Wrong place
                  </button>
                </>
              )}
              {p.latitude !== null && p.status !== "rejected" && (
                <Link
                  to={`/map?lat=${p.latitude}&lng=${p.longitude}`}
                  className="flex min-h-11 items-center text-sm"
                >
                  Show on the time map
                </Link>
              )}
              <Link
                to={`/map?fix=${p.id}&label=${encodeURIComponent(p.text)}&back=${encodeURIComponent(back)}${
                  p.latitude !== null ? `&lat=${p.latitude}&lng=${p.longitude}` : ""
                }`}
                className="flex min-h-11 items-center text-sm"
              >
                {p.latitude === null || p.status === "rejected" ? "Place it on the map" : "Move it"}
              </Link>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
