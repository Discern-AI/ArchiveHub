/** Where to look next for a person: records that could exist, who holds them, cost. */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { request } from "../../lib/api";

interface Route {
  title: string;
  holder: string;
  what_it_gives: string;
  access: "free" | "paid" | "visit" | "ask";
  cost: string;
  url: string;
  source: string;
  checked: boolean;
}

interface Step {
  event: string;
  year: string;
  why: string;
  routes: Route[];
}

const ACCESS: Record<Route["access"], string> = {
  free: "Free",
  paid: "Paid",
  visit: "Visit or order",
  ask: "Ask",
};

export function WhereToLook({ projectId, personId }: { projectId: string; personId: string }) {
  const [open, setOpen] = useState(false);
  const guide = useQuery({
    queryKey: ["where-to-look", projectId, personId],
    queryFn: () =>
      request<{ steps: Step[]; note: string }>(
        "GET",
        `/api/v1/projects/${projectId}/people/${personId}/where-to-look`,
      ),
    enabled: open,
  });

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="min-h-11 cursor-pointer self-start rounded-lg border border-control bg-surface px-3 font-medium"
      >
        Where to look next
      </button>
    );
  }
  const d = guide.data;
  return (
    <section
      aria-label="Where to look next"
      className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-4"
    >
      <h2 className="m-0 text-lg font-semibold">Where to look next</h2>
      {guide.isPending && <p className="m-0 text-muted">Working it out…</p>}
      {guide.isError && <p className="m-0 text-warning">{(guide.error as Error).message}</p>}
      {d && (
        <>
          <p className="m-0 text-sm text-muted">{d.note}</p>
          {d.steps.length === 0 && <p className="m-0">Nothing to suggest yet.</p>}
          <ol className="m-0 flex flex-col gap-3 pl-5">
            {d.steps.map((s, i) => (
              <li key={i}>
                <strong className="capitalize">{s.event}</strong>{" "}
                <span className="text-muted">({s.year})</span>
                <p className="m-0 text-sm">{s.why}</p>
                <ul className="m-0 mt-1 flex flex-col gap-1 pl-4 text-sm">
                  {s.routes.map((r) => (
                    <li key={r.title}>
                      <span className="mr-1 rounded-full bg-tint px-2 py-0.5 text-xs font-semibold">
                        {ACCESS[r.access]}
                      </span>
                      {r.url ? (
                        <a href={r.url} target="_blank" rel="noreferrer">
                          {r.title} ↗
                        </a>
                      ) : (
                        r.title
                      )}{" "}
                      <span className="text-muted">· {r.holder}</span>
                      <span className="block">{r.what_it_gives}</span>
                      {r.cost && <span className="block text-muted">{r.cost}</span>}
                      {!r.checked && (
                        <span className="block text-xs text-warning">
                          A lead: not yet checked against official guidance.
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  );
}
