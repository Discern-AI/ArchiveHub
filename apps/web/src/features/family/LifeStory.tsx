/**
 * A life told in order, from the tree's own facts. Each sentence can show where it comes
 * from, in the same source card whatever site the record came from. Remembered or
 * inferred facts say so. What was happening in the world is kept apart, as context.
 */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { storyApi, type StoryEvent, type StorySource } from "../../lib/story";

const STATUS: Record<StoryEvent["status"], string> = {
  documented: "",
  remembered: "Remembered",
  inferred: "Inferred",
  disputed: "Sources disagree",
};

export function SourceCard({ s }: { s: StorySource }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-lg border border-line-soft bg-page px-3 py-2 text-sm">
      <span className="text-xs font-semibold text-muted uppercase">{s.source || "Source"}</span>
      {s.url ? (
        s.url.startsWith("/") ? (
          <Link to={s.url}>{s.title}</Link>
        ) : (
          <a href={s.url} target="_blank" rel="noreferrer">
            {s.title} ↗
          </a>
        )
      ) : (
        <span>{s.title}</span>
      )}
      {s.what_it_says && <span className="text-muted">“{s.what_it_says}”</span>}
    </div>
  );
}

function Event({ e, projectId }: { e: StoryEvent; projectId: string }) {
  const [open, setOpen] = useState(false);
  return (
    <li className="flex flex-col gap-1">
      <p className="m-0 text-[17px] leading-relaxed">
        {e.sentence}{" "}
        {STATUS[e.status] && (
          <span className="rounded-full bg-tint px-2 py-0.5 text-xs font-semibold text-muted">
            {STATUS[e.status]}
          </span>
        )}{" "}
        {e.sources.length > 0 && (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="min-h-8 cursor-pointer border-0 bg-transparent p-0 text-sm text-accent underline"
          >
            {open ? "Hide sources" : `Sources (${e.sources.length})`}
          </button>
        )}
      </p>
      {e.people.length > 0 && (
        <span className="flex flex-wrap gap-3 text-sm">
          {e.people.map((p) => (
            <Link key={p.id} to={`/projects/${projectId}/people/${p.id}`}>
              {p.name}
            </Link>
          ))}
        </span>
      )}
      {open && (
        <div className="flex flex-col gap-1">
          {e.sources.map((s, i) => (
            <SourceCard key={i} s={s} />
          ))}
        </div>
      )}
    </li>
  );
}

export function LifeStoryView({
  projectId,
  personId,
  onFacts,
}: {
  projectId: string;
  personId: string;
  onFacts: () => void;
}) {
  const story = useQuery({
    queryKey: ["life-story", projectId, personId],
    queryFn: () => storyApi.lifeStory(projectId, personId),
  });
  if (story.isPending) return <p className="text-muted">Loading their story…</p>;
  if (story.isError) return <p className="text-warning">Their story couldn&apos;t be loaded.</p>;
  const s = story.data;
  if (s.private) return <p className="rounded-lg bg-tint p-3">{s.note}</p>;
  const g = s.at_a_glance!;
  return (
    <div className="flex flex-col gap-5">
      <section
        aria-label="At a glance"
        className="grid grid-cols-2 gap-3 rounded-lg border border-line bg-surface p-4 sm:grid-cols-4"
      >
        {[
          ["Born", g.born || "Not recorded"],
          ["Died", g.died || "Not recorded"],
          ["Work", g.occupation || "Not recorded"],
          [
            "Family",
            `${g.partners} partner${g.partners === 1 ? "" : "s"}, ${g.children} child${g.children === 1 ? "" : "ren"}`,
          ],
        ].map(([k, v]) => (
          <div key={k}>
            <div className="text-xs font-semibold text-muted uppercase">{k}</div>
            <div>{v}</div>
          </div>
        ))}
      </section>
      {s.chapters!.map((c) => (
        <section key={c.key} aria-label={c.title} className="flex flex-col gap-2">
          <h2 className="m-0 font-serif text-2xl font-semibold">{c.title}</h2>
          <ul className="m-0 flex list-none flex-col gap-3 p-0">
            {c.events.map((e, i) => (
              <Event key={i} e={e} projectId={projectId} />
            ))}
          </ul>
        </section>
      ))}
      {s.context!.length > 0 && (
        <section
          aria-label="The world around them"
          className="flex flex-col gap-2 rounded-lg bg-tint p-4"
        >
          <h2 className="m-0 text-lg font-semibold">The world around them</h2>
          <p className="m-0 text-sm text-muted">{s.context_note}</p>
          <ul className="m-0 flex flex-col gap-1 pl-5">
            {s.context!.map((c) => (
              <li key={c.title + c.date_text}>
                {c.title}, {c.date_text}
                {c.area ? ` (${c.area})` : ""}: they were {c.age}.{c.note ? ` ${c.note}` : ""}{" "}
                <a href={c.source_url} target="_blank" rel="noreferrer" className="text-sm">
                  Source ↗
                </a>
              </li>
            ))}
          </ul>
          <Link to={`/projects/${projectId}/lifeline`} className="text-sm">
            See their family on the Lifeline
          </Link>
        </section>
      )}
      {s.gaps!.length > 0 && (
        <section aria-label="What isn't known yet" className="flex flex-col gap-1">
          <h2 className="m-0 text-lg font-semibold">What isn&apos;t known yet</h2>
          <ul className="m-0 pl-5">
            {s.gaps!.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
          <button
            type="button"
            onClick={onFacts}
            className="min-h-11 cursor-pointer self-start border-0 bg-transparent p-0 text-accent underline"
          >
            See the facts, and where to look next
          </button>
        </section>
      )}
      <p className="m-0 text-sm text-muted">
        Told only from what&apos;s recorded in this tree. Nothing has been added or guessed.
      </p>
    </div>
  );
}
