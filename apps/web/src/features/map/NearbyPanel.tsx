/** "What else is known here?": evidence near a spot on the time map, never a guess. */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { DATE_ROLE_LABELS, mapApi, type MapFeature } from "../../lib/map";

function EvidenceLine({ f }: { f: MapFeature }) {
  const date = f.date_display ? `${DATE_ROLE_LABELS[f.date_role]} ${f.date_display}` : "Undated";
  return (
    <li className="flex flex-col">
      {f.url ? (
        <a href={f.url} target="_blank" rel="noreferrer">
          {f.title} ↗
        </a>
      ) : (
        <span>{f.title}</span>
      )}
      <span className="text-sm text-muted">{date}</span>
    </li>
  );
}

export function NearbyPanel({ f }: { f: MapFeature }) {
  const [open, setOpen] = useState(false);
  const nearby = useQuery({
    queryKey: ["map-nearby", f.latitude, f.longitude, f.title],
    queryFn: () => mapApi.nearby(f.latitude, f.longitude, f.title),
    enabled: open,
    staleTime: 10 * 60 * 1000,
  });

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="min-h-11 cursor-pointer self-start rounded-lg border border-control bg-surface px-3"
      >
        What else is known here?
      </button>
    );
  }

  const d = nearby.data;
  return (
    <section
      aria-label="What else is known here"
      className="flex flex-col gap-3 rounded-lg border border-line bg-surface p-3"
    >
      <h3 className="m-0 text-base font-semibold">What else is known here</h3>
      {nearby.isPending && <p className="m-0 text-sm text-muted">Looking…</p>}
      {nearby.isError && (
        <p className="m-0 text-sm text-warning">{(nearby.error as Error).message}</p>
      )}
      {d && (
        <>
          <div>
            <h4 className="m-0 text-sm font-semibold">On the c.1900 map nearby</h4>
            {d.map_names.length === 0 ? (
              <p className="m-0 text-sm text-muted">
                No names written on the map within 150 m (or the old map names aren't loaded).
              </p>
            ) : (
              <ul className="m-0 flex flex-col gap-0.5 pl-5 text-sm">
                {d.map_names.map((n) => (
                  <li key={n.record_id}>
                    <strong>{n.title}</strong>
                    {n.meaning ? ` (${n.meaning})` : ""}, {n.distance_m} m away
                  </li>
                ))}
              </ul>
            )}
          </div>

          {d.street ? (
            <div>
              <h4 className="m-0 text-sm font-semibold">Records for {d.street}</h4>
              {d.public.length === 0 ? (
                <p className="m-0 text-sm text-muted">None held yet.</p>
              ) : (
                <ul className="m-0 flex flex-col gap-1 pl-5 text-sm">
                  {d.public.map((r) => (
                    <EvidenceLine key={r.id} f={r} />
                  ))}
                </ul>
              )}
              {d.private.length > 0 && (
                <div className="mt-2 rounded-lg bg-private-tint p-2">
                  <h4 className="m-0 text-sm font-semibold">From your projects (private)</h4>
                  <ul className="m-0 flex flex-col gap-1 pl-5 text-sm">
                    {d.private.map((r) => (
                      <EvidenceLine key={r.id} f={r} />
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : null}

          {d.gazette && (
            <div>
              <h4 className="m-0 flex flex-wrap items-center gap-2 text-sm font-semibold">
                The Gazette
                <span className="rounded-full bg-tint px-2 py-0.5 text-xs">Searched live</span>
              </h4>
              {d.gazette.error ? (
                <p className="m-0 text-sm text-warning">{d.gazette.error}</p>
              ) : d.gazette.results.length === 0 ? (
                <p className="m-0 text-sm text-muted">No notices found.</p>
              ) : (
                <ul className="m-0 flex flex-col gap-1 pl-5 text-sm">
                  {d.gazette.results.map((g) => (
                    <li key={g.id}>
                      <a href={g.url} target="_blank" rel="noreferrer">
                        {g.title} ↗
                      </a>
                      <span className="text-muted"> {g.date}</span>
                      {g.snippet && <span className="block text-muted">{g.snippet}</span>}
                    </li>
                  ))}
                </ul>
              )}
              <p className="m-0 text-xs text-muted">{d.gazette.searched}</p>
            </div>
          )}

          {d.notes.map((n) => (
            <p key={n} className="m-0 text-sm text-muted">
              {n}
            </p>
          ))}
        </>
      )}
    </section>
  );
}
