/**
 * Life and times: prices, weather and what was happening in a chosen year, clearly
 * labelled as context about the world, not a fact about the person.
 */
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { explainApi } from "../../lib/explain";

function Credit({ text, url }: { text?: string; url?: string }) {
  if (!text) return null;
  return (
    <span className="block text-xs text-muted">
      {url ? (
        <a href={url} target="_blank" rel="noreferrer">
          {text} ↗
        </a>
      ) : (
        text
      )}
    </span>
  );
}

export function LifeAndTimes({
  from,
  to,
  initial,
  projectId,
  who,
}: {
  from: number;
  to: number;
  initial?: number;
  projectId?: string;
  who?: string;
}) {
  const [year, setYear] = useState(initial ?? from);
  const data = useQuery({
    queryKey: ["life-and-times", year, projectId],
    queryFn: () => explainApi.lifeAndTimes(year, projectId),
  });
  const d = data.data;
  const age = who && year >= from ? year - from : null;
  return (
    <section
      aria-label="Life and times"
      className="flex flex-col gap-3 rounded-lg border border-line bg-surface p-4"
    >
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h2 className="m-0 text-lg font-semibold">Life and times in {year}</h2>
        <label className="flex min-w-[220px] flex-1 flex-col gap-1 text-sm font-medium">
          <span>
            Choose a year{" "}
            {who && age !== null && (
              <span className="font-normal text-muted">
                ({who} was about {age})
              </span>
            )}
          </span>
          <input
            type="range"
            min={from}
            max={to}
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            aria-label="Year for life and times"
            className="min-h-11"
          />
        </label>
      </div>
      <p className="m-0 text-sm text-muted">
        {d?.label ?? "Context about the world, not a fact about them."}
      </p>
      {data.isPending && <p className="m-0 text-muted">Loading…</p>}
      {d && (
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="flex flex-col gap-1">
            <h3 className="m-0 text-base font-semibold">Money</h3>
            <p className="m-0">{d.money.available ? d.money.sentence : d.money.note}</p>
            {d.money.available && <p className="m-0 text-sm text-muted">{d.money.note}</p>}
            <Credit text={d.money.source} url={d.money.source_url} />
          </div>
          <div className="flex flex-col gap-1">
            <h3 className="m-0 text-base font-semibold">Weather</h3>
            <p className="m-0">{d.weather.available ? d.weather.sentence : d.weather.note}</p>
            {d.weather.rank && <p className="m-0 font-medium">{d.weather.rank}</p>}
            {d.weather.available && <p className="m-0 text-sm text-muted">{d.weather.note}</p>}
            <Credit text={d.weather.source} url={d.weather.source_url} />
          </div>
          <div className="flex flex-col gap-1">
            <h3 className="m-0 text-base font-semibold">What was happening</h3>
            {d.happening.length === 0 ? (
              <p className="m-0 text-muted">
                Nothing from the checked list of wars, laws and censuses.
              </p>
            ) : (
              <ul className="m-0 flex flex-col gap-1 pl-5">
                {d.happening.map((h) => (
                  <li key={h.title + h.date_text}>
                    {h.title} ({h.date_text}){h.area ? `, ${h.area}` : ""}: {h.when}.{" "}
                    {h.source_url && (
                      <a href={h.source_url} target="_blank" rel="noreferrer" className="text-sm">
                        Source ↗
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="flex flex-col gap-1">
            <h3 className="m-0 text-base font-semibold">How people described it</h3>
            <p className="m-0">{d.accounts.note}</p>
            <Link to={`/search?q=${encodeURIComponent(d.accounts.search)}`} className="text-sm">
              Find diaries and oral histories
            </Link>
          </div>
        </div>
      )}
    </section>
  );
}
