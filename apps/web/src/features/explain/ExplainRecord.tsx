/**
 * Explain this record: what it says, what its words meant then, what it may mean for the
 * person (labelled as a careful reading), and where to find out more. Only checked
 * explanations are used; anyone can offer one for others, with credit, once reviewed.
 */
import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { ApiError } from "../../lib/api";
import { explainApi, type Explained, type Src } from "../../lib/explain";

function Sources({ items }: { items: Src[] }) {
  if (!items.length) return null;
  return (
    <span className="block text-xs text-muted">
      Source:{" "}
      {items.map((s, i) => (
        <span key={i}>
          {i > 0 && "; "}
          {s.url ? (
            <a href={s.url} target="_blank" rel="noreferrer">
              {s.title} ↗
            </a>
          ) : (
            s.title
          )}
        </span>
      ))}
    </span>
  );
}

function Layer({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section
      aria-label={title}
      className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-4"
    >
      <h3 className="m-0 flex items-center gap-2 text-lg font-semibold">
        <span
          aria-hidden="true"
          className="flex size-7 items-center justify-center rounded-full bg-accent text-sm text-white"
        >
          {n}
        </span>
        {title}
      </h3>
      {children}
    </section>
  );
}

export function ExplainResult({ r }: { r: Explained }) {
  return (
    <div className="flex flex-col gap-3">
      {r.sensitive_note && <p className="m-0 rounded-lg bg-tint p-3 text-sm">{r.sensitive_note}</p>}
      <Layer n={1} title="What it says">
        <blockquote className="m-0 border-l-4 border-line pl-3 whitespace-pre-wrap">
          {r.says.text}
        </blockquote>
        <span className="text-sm text-muted">
          {[r.says.year && `Dated ${r.says.year}`, r.says.place].filter(Boolean).join(" · ") ||
            "Add the year and place for a better explanation."}
        </span>
      </Layer>
      <Layer n={2} title="What the words mean">
        {r.nothing_found ? (
          <p className="m-0">{r.note}</p>
        ) : (
          <ul className="m-0 flex list-none flex-col gap-3 p-0">
            {r.words.map((w) => (
              <li key={w.term} className="flex flex-col gap-1">
                <strong>
                  {w.term}
                  {w.area && <span className="font-normal text-muted"> · {w.area}</span>}
                </strong>
                {w.period_note ? (
                  <p className="m-0 rounded-lg border border-warning p-2">{w.period_note}</p>
                ) : null}
                <p className={`m-0 ${w.applies ? "" : "text-muted"}`}>{w.meaning}</p>
                {w.contributed_by && (
                  <span className="text-xs text-muted">Explained by {w.contributed_by}</span>
                )}
                <Sources items={w.sources} />
              </li>
            ))}
          </ul>
        )}
      </Layer>
      <Layer n={3} title="What it may mean for them">
        <p className="m-0 text-sm text-muted">{r.may_mean_label}</p>
        {r.may_mean.length === 0 ? (
          <p className="m-0">No careful reading to offer for these words yet.</p>
        ) : (
          <ul className="m-0 flex flex-col gap-2 pl-5">
            {r.may_mean.map((m) => (
              <li key={m.term}>
                {m.text}
                <Sources items={m.sources} />
              </li>
            ))}
          </ul>
        )}
      </Layer>
      <Layer n={4} title="Where to find out more">
        {r.find_out_more.length === 0 ? (
          <p className="m-0">Add the place to see which record office to start with.</p>
        ) : (
          <ul className="m-0 flex flex-col gap-2 pl-5">
            {r.find_out_more.map((m) => (
              <li key={m.text}>
                {m.text}
                <Sources items={m.sources} />
              </li>
            ))}
          </ul>
        )}
      </Layer>
    </div>
  );
}

export function ExplainRecord({
  initialText = "",
  initialYear = "",
  initialPlace = "",
}: {
  initialText?: string;
  initialYear?: string;
  initialPlace?: string;
}) {
  const [text, setText] = useState(initialText);
  const [year, setYear] = useState(initialYear);
  const [place, setPlace] = useState(initialPlace);
  const explain = useMutation({
    mutationFn: () => explainApi.explain({ text, year: year ? Number(year) : null, place }),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (text.trim()) explain.mutate();
  };
  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={submit} className="flex flex-col gap-2">
        <label className="flex flex-col gap-1 font-medium">
          The record&apos;s wording
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={4}
            placeholder="1881. William Smith, aged 9, admitted to the Union Workhouse."
            className="rounded-lg border border-control bg-surface p-3 font-normal"
          />
        </label>
        <div className="flex flex-wrap gap-2">
          <label className="flex flex-col gap-1 text-sm font-medium">
            Year
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              className="min-h-11 w-28 rounded-lg border border-control bg-surface px-3 font-normal"
            />
          </label>
          <label className="flex flex-1 flex-col gap-1 text-sm font-medium">
            Place
            <input
              value={place}
              onChange={(e) => setPlace(e.target.value)}
              placeholder="Hungerford, Berkshire"
              className="min-h-11 rounded-lg border border-control bg-surface px-3 font-normal"
            />
          </label>
        </div>
        <button
          type="submit"
          disabled={explain.isPending}
          className="min-h-11 cursor-pointer self-start rounded-lg bg-accent px-4 font-semibold text-white"
        >
          {explain.isPending ? "Explaining…" : "Explain this record"}
        </button>
      </form>
      {explain.isError && (
        <p className="m-0 text-warning">
          {explain.error instanceof ApiError
            ? explain.error.message
            : "It couldn't be explained just now."}
        </p>
      )}
      {explain.data && <ExplainResult r={explain.data} />}
      {explain.data && <OfferExplanation />}
    </div>
  );
}

function OfferExplanation() {
  const [form, setForm] = useState({ term: "", meaning: "", source: "", url: "", credit: "" });
  const offer = useMutation({
    mutationFn: () =>
      explainApi.offer({
        term: form.term,
        meaning: form.meaning,
        sources: [{ title: form.source, url: form.url }],
        credit: form.credit,
      }),
  });
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [k]: e.target.value });
  const field = "min-h-11 rounded-lg border border-control bg-surface px-3 font-normal";
  return (
    <details className="rounded-lg border border-line bg-surface p-3">
      <summary className="min-h-11 cursor-pointer py-2 font-medium">
        Know what a word means? Explain it for others
      </summary>
      {offer.isSuccess ? (
        <p className="m-0" role="status">
          {offer.data.note}
        </p>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            offer.mutate();
          }}
          className="flex flex-col gap-2"
        >
          <label className="flex flex-col gap-1 text-sm font-medium">
            The word or term
            <input value={form.term} onChange={set("term")} className={field} />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            What it meant, in your words
            <textarea
              value={form.meaning}
              onChange={set("meaning")}
              rows={3}
              className="rounded-lg border border-control bg-surface p-3 font-normal"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Where it comes from (a book, archive guide or record)
            <input value={form.source} onChange={set("source")} className={field} />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Link (optional)
            <input value={form.url} onChange={set("url")} className={field} />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Credit it to
            <input
              value={form.credit}
              onChange={set("credit")}
              placeholder="Your name, or your society"
              className={field}
            />
          </label>
          <button
            type="submit"
            className="min-h-11 cursor-pointer self-start rounded-lg border border-accent bg-surface px-3 font-medium text-accent"
          >
            Offer this explanation
          </button>
          <p className="m-0 text-xs text-muted">
            An editor checks it before it&apos;s shown, with your credit.
          </p>
          {offer.isError && (
            <p className="m-0 text-warning">
              {offer.error instanceof ApiError ? offer.error.message : "It couldn't be sent."}
            </p>
          )}
        </form>
      )}
    </details>
  );
}

export function ExplainPage() {
  return (
    <div className="mx-auto flex w-full max-w-[900px] flex-col gap-4 px-4 py-8 sm:px-12">
      <div>
        <div className="text-[13px] font-semibold text-muted uppercase">Research</div>
        <h1 className="m-0 font-serif text-[32px] font-semibold">Explain this record</h1>
        <p className="mt-1 mb-0 text-muted">
          Paste the wording of a record (a census line, a workhouse register entry, a will) to see
          what it says, what its words meant at the time, what it may mean, and where to find out
          more. Or open a file in your <Link to="/archive">Archive</Link> and choose &quot;Explain
          this record&quot;.
        </p>
      </div>
      <ExplainRecord />
    </div>
  );
}
