/** Tree health check: things in the tree worth a second look. Nothing is changed. */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { request } from "../../lib/api";

interface Finding {
  kind: "dates" | "parents" | "duplicates" | "branches" | "gaps";
  title: string;
  detail: string;
  people: { id: string; name: string }[];
}

interface Health {
  people: number;
  branches: number;
  findings: Finding[];
  note: string;
}

const KIND: Record<Finding["kind"], string> = {
  dates: "Dates",
  parents: "Parents and children",
  duplicates: "Possibly the same person",
  branches: "Separate branches",
  gaps: "Missing dates",
};

export function TreeHealth({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false);
  const health = useQuery({
    queryKey: ["tree-health", projectId],
    queryFn: () => request<Health>("GET", `/api/v1/projects/${projectId}/tree-health`),
    enabled: open,
  });

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="min-h-11 cursor-pointer self-start rounded-lg border border-control bg-surface px-3 font-medium"
      >
        Check this tree
      </button>
    );
  }
  const h = health.data;
  return (
    <section
      aria-label="Tree health check"
      className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-4"
    >
      <h2 className="m-0 text-lg font-semibold">Tree health check</h2>
      {health.isPending && <p className="m-0 text-muted">Checking…</p>}
      {health.isError && <p className="m-0 text-warning">{(health.error as Error).message}</p>}
      {h && (
        <>
          <p className="m-0 text-sm text-muted">
            {h.people} people in {h.branches} {h.branches === 1 ? "connected tree" : "groups"}.{" "}
            {h.note}
          </p>
          {h.findings.length === 0 ? (
            <p className="m-0">Nothing stood out.</p>
          ) : (
            <ul className="m-0 flex list-none flex-col gap-2 p-0">
              {h.findings.map((f, i) => (
                <li key={i} className="flex flex-col gap-0.5 border-t border-line-soft pt-2">
                  <span className="text-xs font-semibold text-muted uppercase">{KIND[f.kind]}</span>
                  <strong>{f.title}</strong>
                  <span className="text-sm">{f.detail}</span>
                  <span className="flex flex-wrap gap-3 text-sm">
                    {f.people.map((p) => (
                      <Link key={p.id} to={`/projects/${projectId}/people/${p.id}`}>
                        {p.name}
                      </Link>
                    ))}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
