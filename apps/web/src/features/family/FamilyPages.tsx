import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router";
import { api, archiveApi, type PersonBrief } from "../../lib/api";
import { AnswerEvidence } from "./AnswerEvidence";
import { ChangeHistory } from "./ChangeHistory";
import { FamilyPlaces } from "./FamilyPlaces";
import { TreeChart } from "./TreeChart";
import { TreeHealth } from "./TreeHealth";
import { WhereToLook } from "./WhereToLook";

function PersonCard({
  p,
  projectId,
  current,
}: {
  p: PersonBrief;
  projectId: string;
  current?: boolean;
}) {
  return (
    <Link
      to={`/projects/${projectId}/people/${p.id}`}
      aria-current={current ? "page" : undefined}
      className={`flex min-h-11 flex-col rounded-lg border px-3 py-2 text-ink no-underline ${current ? "border-accent bg-selected" : "border-line bg-surface hover:bg-tint"}`}
    >
      <strong>{p.name}</strong>
      <span className="sr-only">, </span>
      <span className="text-[13px] text-muted">
        {p.living
          ? "Living (private)"
          : [p.birth && `b. ${p.birth}`, p.death && `d. ${p.death}`].filter(Boolean).join(" · ") ||
            "Dates unknown"}
      </span>
    </Link>
  );
}

export function FamilyPage() {
  const { projectId } = useParams();
  const [q, setQ] = useState("");
  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.project(projectId!),
  });
  const people = useQuery({
    queryKey: ["people", projectId, q],
    queryFn: () => archiveApi.people(projectId!, q),
  });

  return (
    <div className="mx-auto flex w-full max-w-[1040px] flex-col gap-4 px-4 py-8 sm:px-12">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[13px] font-semibold text-muted uppercase">Family tree</div>
          <h1 className="m-0 font-serif text-[34px] font-semibold">{project.data?.title ?? "…"}</h1>
          <p className="mt-1 mb-0 text-muted">
            Living people are private. Imported facts stay on file; your corrections sit beside
            them.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {!!people.data?.length && (
            <Link
              to={`/projects/${projectId}/lifeline`}
              className="flex min-h-11 items-center rounded-lg border border-accent px-4 font-semibold no-underline"
            >
              Lifeline
            </Link>
          )}
          <Link to={`/archive?project=${projectId}`} className="flex min-h-11 items-center">
            Import a GEDCOM file
          </Link>
          {!!people.data?.length && (
            <a
              href={`/api/v1/projects/${projectId}/gedcom`}
              className="flex min-h-11 items-center rounded-lg bg-accent px-4 font-semibold text-white no-underline hover:text-white"
            >
              Export GEDCOM
            </a>
          )}
          {!!people.data?.length && (
            <a
              href={`/api/v1/projects/${projectId}/gedcom?version=7.0`}
              className="flex min-h-11 items-center"
              title="The newer GEDCOM standard, for software that reads it"
            >
              GEDCOM 7
            </a>
          )}
          {!!people.data?.length && (
            <a
              href={`/api/v1/projects/${projectId}/gedzip`}
              className="flex min-h-11 items-center"
              title="GEDCOM 7 with the files used as evidence for people who have died, in one zip (.gdz)"
            >
              GEDCOM 7 with files
            </a>
          )}
        </div>
      </div>
      <label className="flex flex-col gap-1 font-medium">
        Find a person
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="min-h-11 rounded-lg border border-control bg-surface px-3 font-normal"
        />
      </label>
      {projectId && !!people.data?.length && <TreeChart projectId={projectId} />}
      {projectId && !!people.data?.length && <TreeHealth projectId={projectId} />}
      {projectId && <ChangeHistory projectId={projectId} />}
      {projectId && <FamilyPlaces projectId={projectId} />}
      {people.isError && <p className="text-warning">This family tree couldn't be loaded.</p>}
      {people.data?.length === 0 && (
        <p className="text-muted">
          No people yet. Upload a GEDCOM file to the Archive and choose “Import family tree”.
        </p>
      )}
      <div className="grid gap-2 [grid-template-columns:repeat(auto-fill,minmax(220px,1fr))]">
        {people.data?.map((p) => (
          <PersonCard key={p.id} p={p} projectId={projectId!} />
        ))}
      </div>
    </div>
  );
}

const STATUS_LABEL: Record<string, string> = {
  documented: "Documented",
  remembered: "Remembered",
  inferred: "Inferred",
};

export function PersonPage() {
  const { projectId, personId } = useParams();
  const qc = useQueryClient();
  const person = useQuery({
    queryKey: ["person", projectId, personId],
    queryFn: () => archiveApi.person(projectId!, personId!),
  });
  const [form, setForm] = useState({
    predicate: "birth date",
    value: "",
    status: "remembered",
    note: "",
  });
  const [msg, setMsg] = useState<string | null>(null);

  async function correct(e: FormEvent) {
    e.preventDefault();
    try {
      await archiveApi.addClaim(projectId!, personId!, form);
      setMsg("Saved. The earlier version stays on file beside yours.");
      setForm({ ...form, value: "", note: "" });
      await qc.invalidateQueries({ queryKey: ["person", projectId, personId] });
      await qc.invalidateQueries({ queryKey: ["people", projectId] });
    } catch (err) {
      setMsg((err as Error).message);
    }
  }

  if (person.isPending) return <p className="p-8 text-muted">Loading…</p>;
  if (person.isError) return <p className="p-8 text-warning">This person couldn't be found.</p>;
  const p = person.data;

  return (
    <div className="mx-auto flex w-full max-w-[1040px] flex-col gap-5 px-4 py-8 sm:px-12">
      <Link to={`/projects/${projectId}/people`}>← Everyone in this tree</Link>

      <section aria-label="Family" className="flex flex-col items-stretch gap-3">
        {p.parents.length > 0 && (
          <div className="flex flex-wrap justify-center gap-2" aria-label="Parents">
            {p.parents.map((x) => (
              <PersonCard key={x.id} p={x} projectId={projectId!} />
            ))}
          </div>
        )}
        <div className="flex flex-wrap justify-center gap-2">
          <PersonCard p={p} projectId={projectId!} current />
          {p.partners.map((x) => (
            <PersonCard key={x.id} p={x} projectId={projectId!} />
          ))}
        </div>
        {p.children.length > 0 && (
          <div className="flex flex-wrap justify-center gap-2" aria-label="Children">
            {p.children.map((x) => (
              <PersonCard key={x.id} p={x} projectId={projectId!} />
            ))}
          </div>
        )}
      </section>

      <h1 className="m-0 font-serif text-[34px] font-semibold">{p.name}</h1>
      {p.living && (
        <p className="m-0 rounded-lg bg-tint p-3">
          Treated as living, so private: no death is recorded and they may have been born within the
          last 110 years.
        </p>
      )}

      <section aria-label="Facts" className="flex flex-col gap-2">
        {p.facts.map((f) => (
          <div key={f.question} className="rounded-lg border border-line bg-surface p-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="m-0 text-base font-semibold capitalize">{f.question}</h2>
              {f.disputed && (
                <span className="text-sm font-semibold text-warning">Versions differ</span>
              )}
            </div>
            <ul className="m-0 mt-1 flex list-none flex-col gap-1 p-0">
              {f.answers.map((a) => (
                <li key={a.id} className={a.in_use ? "font-semibold" : ""}>
                  {a.value}{" "}
                  <span className="text-[13px] font-normal text-muted">
                    ({STATUS_LABEL[a.status] ?? a.status}
                    {a.method === "import"
                      ? ", from the imported tree"
                      : a.method === "user"
                        ? ", your entry"
                        : ""}
                    {a.in_use ? ", used" : ""})
                  </span>
                  {a.note && <div className="text-sm font-normal text-muted">{a.note}</div>}
                  <AnswerEvidence
                    projectId={projectId!}
                    personId={personId!}
                    claimId={a.id}
                    evidence={a.evidence}
                  />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      <form
        onSubmit={correct}
        className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-4"
      >
        <h2 className="m-0 text-lg font-semibold">Add or correct a fact</h2>
        <p className="m-0 text-sm text-muted">
          Nothing is overwritten: your version is kept beside the original.
        </p>
        <div className="flex flex-wrap gap-2">
          <label className="flex flex-col gap-1 text-sm font-medium">
            Fact
            <select
              value={form.predicate}
              onChange={(e) => setForm({ ...form, predicate: e.target.value })}
              className="min-h-11 rounded-lg border border-control px-2 font-normal"
            >
              {["name", "birth date", "birth place", "death date", "death place", "occupation"].map(
                (x) => (
                  <option key={x} value={x}>
                    {x}
                  </option>
                ),
              )}
            </select>
          </label>
          <label className="flex min-w-48 flex-1 flex-col gap-1 text-sm font-medium">
            Value
            <input
              required
              value={form.value}
              onChange={(e) => setForm({ ...form, value: e.target.value })}
              className="min-h-11 rounded-lg border border-control px-3 font-normal"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            This is
            <select
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value })}
              className="min-h-11 rounded-lg border border-control px-2 font-normal"
            >
              <option value="remembered">Remembered</option>
              <option value="documented">Documented</option>
              <option value="inferred">Inferred</option>
            </select>
          </label>
        </div>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Where it comes from (optional)
          <input
            value={form.note}
            onChange={(e) => setForm({ ...form, note: e.target.value })}
            className="min-h-11 rounded-lg border border-control px-3 font-normal"
          />
        </label>
        <button
          type="submit"
          className="min-h-11 cursor-pointer self-start rounded-lg bg-accent px-4 font-semibold text-white"
        >
          Save
        </button>
        {msg && (
          <p role="status" className="m-0 font-medium text-accent">
            {msg}
          </p>
        )}
      </form>
      {projectId && personId && <WhereToLook projectId={projectId} personId={personId} />}
    </div>
  );
}
