import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { SaveToProject } from "../../components/SaveToProject";
import { mapApi, type SearchGroup, type SearchResult } from "../../lib/map";

function ResultItem({ r }: { r: SearchResult }) {
  const meta = [r.date, r.place, r.source, r.project_title && `Project: ${r.project_title}`].filter(
    Boolean,
  );
  const lat = r.extra.latitude;
  const lng = r.extra.longitude;
  const mapLink =
    !r.link && typeof lat === "number" && typeof lng === "number"
      ? `/map?lat=${lat}&lng=${lng}&year=1900`
      : "";
  // The title opens our own page, else the original, else the map.
  const titleToMap = !r.link && !r.url && !!mapLink;
  return (
    <li className="flex flex-col gap-0.5 border-t border-line-soft py-2 first:border-t-0">
      {r.link || titleToMap ? (
        <Link to={r.link || mapLink} className="font-medium">
          {r.title}
        </Link>
      ) : r.url ? (
        <a href={r.url} target="_blank" rel="noreferrer" className="font-medium">
          {r.title} ↗
        </a>
      ) : (
        <span className="font-medium">{r.title}</span>
      )}
      {meta.length > 0 && <span className="text-sm text-muted">{meta.join(" · ")}</span>}
      {r.snippet && <span className="text-sm">{r.snippet}</span>}
      {(r.link && r.url) || (mapLink && !titleToMap) ? (
        <span className="flex flex-wrap gap-3 text-sm">
          {r.link && r.url && (
            <a href={r.url} target="_blank" rel="noreferrer">
              See the original ↗
            </a>
          )}
          {mapLink && !titleToMap && <Link to={mapLink}>Show on the time map</Link>}
        </span>
      ) : null}
      {typeof r.extra.connector === "string" && typeof r.extra.record_id === "string" && (
        <SaveToProject connector={r.extra.connector} recordId={r.extra.record_id} />
      )}
    </li>
  );
}

function GroupCard({ g }: { g: SearchGroup }) {
  const isPrivate = g.layer === "private";
  return (
    <section
      aria-label={g.label}
      className={`flex flex-col gap-1 rounded-lg border p-4 ${
        isPrivate ? "border-private bg-private-tint" : "border-line bg-surface"
      }`}
    >
      <h3 className="m-0 flex flex-wrap items-baseline gap-2 text-base font-semibold">
        {g.label}
        <span className="font-normal text-muted">
          {g.count >= 50 ? "50+" : g.count} {g.count === 1 ? "match" : "matches"}
        </span>
        {isPrivate && (
          <span className="rounded-full bg-private px-2 py-0.5 text-xs font-semibold text-white">
            Private
          </span>
        )}
        {g.live && (
          <span className="rounded-full bg-tint px-2 py-0.5 text-xs font-semibold">
            Searched live
          </span>
        )}
      </h3>
      <ul className="m-0 list-none p-0">
        {g.results.map((r) => (
          <ResultItem key={r.id} r={r} />
        ))}
      </ul>
      {g.more && (
        <p className="m-0 text-sm text-muted">
          Showing the first {g.results.length}. Add a word to narrow it down.
        </p>
      )}
    </section>
  );
}

export function SearchPage() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const live = params.get("live") === "1";
  const [text, setText] = useState(q);
  const [outside, setOutside] = useState(live);
  const results = useQuery({
    queryKey: ["search", q, live],
    queryFn: () => mapApi.search(q, live),
    enabled: q.trim().length > 0,
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    const next: Record<string, string> = {};
    if (text.trim()) next.q = text.trim();
    if (outside) next.live = "1";
    setParams(next);
  }

  const data = results.data;
  const found = data?.groups.filter((g) => g.count > 0) ?? [];
  const empty = data?.groups.filter((g) => g.count === 0) ?? [];
  const publicFound = found.filter((g) => g.layer === "public" && !g.live);
  const liveGroups = data?.groups.filter((g) => g.live) ?? [];
  const liveFound = liveGroups.filter((g) => g.count > 0);
  const liveProblems = liveGroups.filter((g) => g.error);
  const privateFound = found.filter((g) => g.layer === "private");

  return (
    <div className="mx-auto flex w-full max-w-[960px] flex-col gap-5 px-4 py-8 sm:px-12">
      <div>
        <h1 className="m-0 font-serif text-[34px] font-semibold">Search</h1>
        <p className="mt-1 mb-0 text-muted">
          Places, records, old map names, the source directory, and your own files, interviews,
          memories and family trees. Your private things are only ever shown to you and the people
          in your projects.
        </p>
      </div>
      <form onSubmit={submit} role="search" className="flex gap-2">
        <label htmlFor="search-q" className="sr-only">
          Search for
        </label>
        <input
          id="search-q"
          type="search"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. Pigeons, Cheap Street, Spracklen"
          className="min-h-11 flex-1 rounded-lg border border-control bg-surface px-3"
        />
        <button
          type="submit"
          className="min-h-11 cursor-pointer rounded-lg border-0 bg-accent px-4 font-medium text-white"
        >
          Search
        </button>
      </form>
      <label className="-mt-3 flex min-h-11 items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={outside}
          onChange={(e) => setOutside(e.target.checked)}
          className="size-5"
        />
        <span>
          Also search outside sources (The Gazette, Historic England, OpenAlex and others).{" "}
          <span className="text-muted">
            Your search words are sent to them, so leave out the names of living people.
          </span>
        </span>
      </label>

      {results.isPending && q && <p className="m-0 text-muted">Searching…</p>}
      {results.isError && <p className="m-0 text-warning">{(results.error as Error).message}</p>}
      {data && data.words.length === 0 && (
        <p className="m-0 text-muted">Try a more specific word: a name, a street or a pub.</p>
      )}

      {data && data.words.length > 0 && (
        <>
          {found.length === 0 && (
            <p className="m-0 rounded-lg border border-line bg-surface p-4">
              <strong>No matches in what we searched.</strong> That doesn't mean it isn't in the
              historical record, only that it isn't in anything below. The{" "}
              <Link to="/chat">assistant</Link> can suggest where else to look.
            </p>
          )}
          {publicFound.length > 0 && (
            <div className="flex flex-col gap-3">
              <h2 className="m-0 text-lg font-semibold">Public records</h2>
              {publicFound.map((g) => (
                <GroupCard key={g.key} g={g} />
              ))}
            </div>
          )}
          {liveFound.length > 0 && (
            <div className="flex flex-col gap-3">
              <h2 className="m-0 text-lg font-semibold">Outside sources, searched live</h2>
              <p className="m-0 text-sm text-muted">
                A name match is a possible match, not the same person. Open each result to check it.
              </p>
              {liveFound.map((g) => (
                <GroupCard key={g.key} g={g} />
              ))}
            </div>
          )}
          {liveProblems.length > 0 && (
            <p className="m-0 text-sm text-warning">
              {liveProblems.map((g) => `${g.label}: ${g.error}`).join(" ")}
            </p>
          )}
          {privateFound.length > 0 && (
            <div className="flex flex-col gap-3">
              <h2 className="m-0 text-lg font-semibold">Your private material</h2>
              {privateFound.map((g) => (
                <GroupCard key={g.key} g={g} />
              ))}
            </div>
          )}

          <section
            aria-label="What was searched"
            className="rounded-lg border border-line bg-surface p-4"
          >
            <h2 className="m-0 mb-2 text-lg font-semibold">What was searched</h2>
            <ul className="m-0 flex flex-col gap-1 pl-5">
              {data.groups.map((g) => (
                <li key={g.key}>
                  <strong>{g.label}</strong>
                  {g.layer === "private" ? " (yours)" : ""}: {g.searched}.{" "}
                  <span className="text-muted">
                    {g.error
                      ? `Couldn't be searched: ${g.error}`
                      : g.count === 0
                        ? "No matches."
                        : `${g.count >= 50 ? "50+" : g.count} found.`}
                  </span>
                </li>
              ))}
            </ul>
            <h2 className="mt-4 mb-2 text-lg font-semibold">Not searched</h2>
            <ul className="m-0 flex flex-col gap-1 pl-5">
              {data.not_searched.map((n) => (
                <li key={n.label}>
                  <strong>{n.label}:</strong> {n.reason}
                </li>
              ))}
            </ul>
            {empty.length > 0 && found.length > 0 && (
              <p className="mt-3 mb-0 text-sm text-muted">
                No matches in: {empty.map((g) => g.label.toLowerCase()).join(", ")}.
              </p>
            )}
          </section>
        </>
      )}
    </div>
  );
}
