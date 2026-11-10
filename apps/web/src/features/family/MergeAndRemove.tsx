/**
 * Tidying a tree: merge a duplicate into this person (choosing which of its facts to bring
 * across), or remove this person, seeing first who would be cut off. Both are previewed,
 * nothing happens automatically, and both can be undone from "Changes and undo".
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router";
import { ApiError, archiveApi, request } from "../../lib/api";

interface Fact {
  id: string;
  value: string;
  date_text: string;
  status: string;
  method: string;
  in_use: boolean;
  evidence: number;
}

interface MergePreview {
  keep: { id: string; name: string; living: string };
  other: { id: string; name: string; living: string };
  questions: { question: string; keep: Fact[]; other: Fact[]; differs: boolean }[];
  relatives_moving: Record<"parents" | "children" | "partners", { id: string; name: string }[]>;
  residences_moving: number;
  warnings: string[];
  note: string;
}

interface DeletePreview {
  person: { id: string; name: string };
  facts: number;
  relationships: number;
  residences: number;
  stranded: { id: string; name: string }[][];
  note: string;
}

function invalidateTree(qc: ReturnType<typeof useQueryClient>, projectId: string) {
  for (const key of [
    "people",
    "person",
    "tree-graph",
    "tree-health",
    "lifeline",
    "changes",
    "trees",
  ])
    qc.invalidateQueries({ queryKey: [key, projectId] });
}

export function MergePanel({
  projectId,
  personId,
  initialOther = "",
}: {
  projectId: string;
  personId: string;
  initialOther?: string;
}) {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [other, setOther] = useState(initialOther);
  const [leaveOut, setLeaveOut] = useState<Set<string>>(new Set());
  const people = useQuery({
    queryKey: ["people", projectId, q],
    queryFn: () => archiveApi.people(projectId, q),
  });
  const preview = useQuery({
    queryKey: ["merge-preview", projectId, personId, other],
    queryFn: () =>
      request<MergePreview>(
        "GET",
        `/api/v1/projects/${projectId}/people/${personId}/merge-preview?other=${other}`,
      ),
    enabled: !!other,
    retry: false,
  });
  const merge = useMutation({
    mutationFn: () =>
      request<{ summary: string }>(
        "POST",
        `/api/v1/projects/${projectId}/people/${personId}/merge`,
        {
          other,
          leave_out: [...leaveOut],
        },
      ),
    onSuccess: () => {
      setOther("");
      setLeaveOut(new Set());
      invalidateTree(qc, projectId);
    },
  });
  const toggle = (id: string) =>
    setLeaveOut((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  const p = preview.data;

  return (
    <section aria-label="Merge with another person" className="flex flex-col gap-2">
      {merge.isSuccess && (
        <p className="m-0" role="status">
          {merge.data.summary}. You can undo it from &quot;Changes and undo&quot; on the family
          page.
        </p>
      )}
      {!other && (
        <>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Find the other record
            <input
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="min-h-11 rounded-lg border border-control bg-surface px-3 font-normal"
            />
          </label>
          <ul className="m-0 flex max-h-48 list-none flex-col gap-1 overflow-y-auto p-0">
            {(people.data ?? [])
              .filter((x) => x.id !== personId)
              .slice(0, 30)
              .map((x) => (
                <li key={x.id}>
                  <button
                    type="button"
                    onClick={() => setOther(x.id)}
                    className="min-h-11 w-full cursor-pointer rounded-lg border border-line bg-surface px-3 text-left"
                  >
                    {x.name}
                    <span className="text-muted">
                      {x.living
                        ? " · living"
                        : ` · ${[x.birth, x.death].filter(Boolean).join(" – ")}`}
                    </span>
                  </button>
                </li>
              ))}
          </ul>
        </>
      )}
      {other && preview.isPending && <p className="m-0 text-muted">Comparing…</p>}
      {other && preview.isError && (
        <p className="m-0 text-warning">
          {preview.error instanceof ApiError ? preview.error.message : "They couldn't be compared."}
        </p>
      )}
      {p && (
        <div role="region" aria-label="Merge preview" className="flex flex-col gap-2 text-sm">
          <p className="m-0">
            Keeping <strong>{p.keep.name}</strong> and bringing across what you tick from{" "}
            <strong>{p.other.name}</strong>. Their other record is then removed.
          </p>
          {p.warnings.map((w) => (
            <p key={w} className="m-0 rounded-lg border border-warning p-2">
              {w}
            </p>
          ))}
          <table className="w-full border-collapse">
            <thead>
              <tr className="text-left">
                <th className="border-b border-line p-1">Question</th>
                <th className="border-b border-line p-1">This person</th>
                <th className="border-b border-line p-1">
                  The other record (tick to bring across)
                </th>
              </tr>
            </thead>
            <tbody>
              {p.questions.map((qq) => (
                <tr key={qq.question} className={qq.differs ? "bg-tint" : ""}>
                  <td className="border-b border-line-soft p-1 align-top">
                    {qq.question}
                    {qq.differs && <span className="block text-xs text-warning">They differ</span>}
                  </td>
                  <td className="border-b border-line-soft p-1 align-top">
                    {qq.keep.map((f) => (
                      <div key={f.id}>
                        {f.value}
                        {!f.in_use && <span className="text-muted"> (not in use)</span>}
                      </div>
                    ))}
                  </td>
                  <td className="border-b border-line-soft p-1 align-top">
                    {qq.other.map((f) => (
                      <label key={f.id} className="flex min-h-11 items-center gap-2">
                        <input
                          type="checkbox"
                          checked={!leaveOut.has(f.id)}
                          onChange={() => toggle(f.id)}
                          aria-label={`Bring across ${qq.question}: ${f.value}`}
                        />
                        <span>
                          {f.value}
                          {f.evidence > 0 && (
                            <span className="text-muted"> · {f.evidence} evidence</span>
                          )}
                        </span>
                      </label>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {(["parents", "partners", "children"] as const).map((k) =>
            p.relatives_moving[k].length ? (
              <p key={k} className="m-0">
                {k[0].toUpperCase() + k.slice(1)} moving across:{" "}
                {p.relatives_moving[k].map((x) => x.name).join(", ")}
              </p>
            ) : null,
          )}
          {p.residences_moving > 0 && (
            <p className="m-0">{p.residences_moving} residences moving across.</p>
          )}
          <p className="m-0 text-muted">{p.note}</p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => merge.mutate()}
              disabled={merge.isPending}
              className="min-h-11 cursor-pointer rounded-lg bg-accent px-4 font-semibold text-white"
            >
              Merge
            </button>
            <button
              type="button"
              onClick={() => {
                setOther("");
                setLeaveOut(new Set());
              }}
              className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3"
            >
              Choose someone else
            </button>
          </div>
          {merge.isError && (
            <p className="m-0 text-warning">
              {merge.error instanceof ApiError ? merge.error.message : "They couldn't be merged."}
            </p>
          )}
        </div>
      )}
    </section>
  );
}

export function RemovePanel({ projectId, personId }: { projectId: string; personId: string }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [also, setAlso] = useState<Set<string>>(new Set());
  const preview = useQuery({
    queryKey: ["delete-preview", projectId, personId],
    queryFn: () =>
      request<DeletePreview>(
        "GET",
        `/api/v1/projects/${projectId}/people/${personId}/delete-preview`,
      ),
  });
  const remove = useMutation({
    mutationFn: () =>
      request<{ summary: string }>(
        "POST",
        `/api/v1/projects/${projectId}/people/${personId}/delete`,
        {
          also: [...also],
        },
      ),
    onSuccess: () => {
      invalidateTree(qc, projectId);
      navigate(`/projects/${projectId}/people`);
    },
  });
  const p = preview.data;
  if (!p)
    return preview.isError ? (
      <p className="m-0 text-warning">This couldn&apos;t be checked.</p>
    ) : null;
  return (
    <section aria-label="Remove this person" className="flex flex-col gap-2 text-sm">
      <h3 className="m-0 text-base font-semibold">Remove {p.person.name}</h3>
      <p className="m-0">
        This removes {p.facts} facts, {p.relationships} family links
        {p.residences ? ` and ${p.residences} residences` : ""}. The original files stay.
      </p>
      {p.stranded.length === 0 ? (
        <p className="m-0">Nobody else would be cut off from the tree.</p>
      ) : (
        <div className="flex flex-col gap-1 rounded-lg border border-warning p-2">
          <strong>These people are only connected to the tree through {p.person.name}.</strong>
          <span>
            They&apos;ll be kept, as a separate branch, unless you tick them to remove too.
          </span>
          {p.stranded.flat().map((x) => (
            <label key={x.id} className="flex min-h-11 items-center gap-2">
              <input
                type="checkbox"
                checked={also.has(x.id)}
                onChange={() =>
                  setAlso((s) => {
                    const n = new Set(s);
                    if (n.has(x.id)) n.delete(x.id);
                    else n.add(x.id);
                    return n;
                  })
                }
              />
              Remove {x.name} too
            </label>
          ))}
        </div>
      )}
      <p className="m-0 text-muted">{p.note}</p>
      <button
        type="button"
        onClick={() => remove.mutate()}
        disabled={remove.isPending}
        className="min-h-11 cursor-pointer self-start rounded-lg border-2 border-warning bg-surface px-4 font-semibold text-warning"
      >
        {also.size ? `Remove ${p.person.name} and ${also.size} more` : `Remove ${p.person.name}`}
      </button>
      {remove.isError && <p className="m-0 text-warning">This couldn&apos;t be removed.</p>}
    </section>
  );
}
