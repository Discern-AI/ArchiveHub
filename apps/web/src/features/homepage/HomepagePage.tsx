/**
 * Your homepage: its address and about page, your posts, a WordPress import and a full
 * export. Nothing is public until the homepage is switched on and each post is checked
 * and approved.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { ApiError } from "../../lib/api";
import {
  homepageApi,
  importWordPress,
  SOURCE_LABELS,
  STATUS_LABELS,
  type Homepage,
  type ImportResult,
} from "../../lib/homepage";

const input = "min-h-11 rounded-lg border border-control bg-surface px-2 font-normal";
const primary = "min-h-11 cursor-pointer rounded-lg bg-accent px-4 font-semibold text-white";
const secondary = "min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3";

export function HomepagePage() {
  const home = useQuery({ queryKey: ["homepage"], queryFn: homepageApi.get });
  if (home.isPending) return <p className="p-8 text-muted">Loading your homepage…</p>;
  if (home.isError) return <p className="p-8 text-warning">Your homepage couldn&apos;t load.</p>;
  return (
    <div className="mx-auto flex w-full max-w-[860px] flex-col gap-6 px-4 py-8 sm:px-10">
      <header className="flex flex-col gap-1">
        <h1 className="m-0 font-serif text-[32px] font-semibold">Your homepage</h1>
        <p className="m-0 text-muted">
          A public place for your history writing. Nothing shows until you switch the homepage on
          and approve each post.
        </p>
      </header>
      <HomeSettings home={home.data} />
      {home.data && (
        <>
          <Posts />
          <ImportAndExport />
        </>
      )}
    </div>
  );
}

function HomeSettings({ home }: { home: Homepage | null }) {
  const qc = useQueryClient();
  const blank = { slug: "", title: "", tagline: "", about: "", live: false };
  const [edits, setEdits] = useState<Omit<Homepage, "url"> | null>(null);
  const form = edits ?? (home ? { ...home } : blank);
  const set = (k: keyof typeof form, v: string | boolean) => setEdits({ ...form, [k]: v });
  const save = useMutation({
    mutationFn: () => homepageApi.save(form),
    onSuccess: (h) => {
      setEdits(null);
      qc.setQueryData(["homepage"], h);
    },
  });
  return (
    <section
      aria-label="Homepage settings"
      className="flex flex-col gap-3 rounded-lg border border-line bg-surface p-4"
    >
      <h2 className="m-0 text-lg font-semibold">{home ? "Settings" : "Set up your homepage"}</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Title
          <input
            className={input}
            value={form.title}
            onChange={(e) => set("title", e.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Web address
          <span className="flex items-center gap-1">
            <span className="text-muted">/h/</span>
            <input
              aria-label="Web address"
              className={`${input} flex-1`}
              value={form.slug}
              onChange={(e) => set("slug", e.target.value)}
              placeholder="your-name"
            />
          </span>
        </label>
      </div>
      <label className="flex flex-col gap-1 text-sm font-medium">
        Tagline
        <input
          className={input}
          value={form.tagline}
          onChange={(e) => set("tagline", e.target.value)}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium">
        About you
        <textarea
          className={`${input} min-h-28 p-2`}
          value={form.about}
          onChange={(e) => set("about", e.target.value)}
        />
      </label>
      <label className="flex items-center gap-2 font-medium">
        <input
          type="checkbox"
          className="size-5"
          checked={form.live}
          onChange={(e) => set("live", e.target.checked)}
        />
        Switch my homepage on, so published posts can be seen by anyone
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          className={primary}
          disabled={save.isPending}
          onClick={() => save.mutate()}
        >
          {home ? "Save settings" : "Create homepage"}
        </button>
        {home?.live && (
          <a href={home.url} target="_blank" rel="noreferrer" className="font-medium">
            View your homepage
          </a>
        )}
        {home && !home.live && (
          <span className="text-sm text-muted">Switched off: only you can see it here.</span>
        )}
        {save.isError && (
          <span role="alert" className="text-sm text-warning">
            {save.error instanceof ApiError ? save.error.message : "Couldn't save."}
          </span>
        )}
      </div>
    </section>
  );
}

function Posts() {
  const navigate = useNavigate();
  const posts = useQuery({ queryKey: ["homepage-posts"], queryFn: homepageApi.posts });
  const create = useMutation({
    mutationFn: () => homepageApi.create({ title: "Untitled" }),
    onSuccess: (p) => navigate(`/homepage/posts/${p.id}`),
  });
  return (
    <section aria-label="Posts" className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h2 className="m-0 text-lg font-semibold">Posts</h2>
        <button type="button" className={primary} onClick={() => create.mutate()}>
          New post
        </button>
      </div>
      {posts.data?.length === 0 && (
        <p className="m-0 text-muted">
          No posts yet. Write one here, import your WordPress blog, or ask in chat to write
          something up as a draft.
        </p>
      )}
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {posts.data?.map((p) => (
          <li
            key={p.id}
            className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-surface p-3"
          >
            <span className="flex flex-col">
              <Link to={`/homepage/posts/${p.id}`} className="font-semibold">
                {p.title}
              </Link>
              <span className="text-sm text-muted">
                {SOURCE_LABELS[p.source]}
                {p.first_published &&
                  ` · first published ${new Date(p.first_published).toLocaleDateString("en-GB")}`}
              </span>
            </span>
            <span
              className={`rounded-full px-2.5 py-0.5 text-sm font-medium ${
                p.status === "published" ? "bg-selected text-accent" : "bg-tint text-muted"
              }`}
            >
              {STATUS_LABELS[p.status]}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ImportAndExport() {
  const qc = useQueryClient();
  const [result, setResult] = useState<ImportResult | null>(null);
  const run = useMutation({
    mutationFn: importWordPress,
    onSuccess: (r) => {
      setResult(r);
      qc.invalidateQueries({ queryKey: ["homepage-posts"] });
    },
  });
  return (
    <section
      aria-label="Import and export"
      className="flex flex-col gap-3 rounded-lg border border-line bg-surface p-4"
    >
      <h2 className="m-0 text-lg font-semibold">
        Bring a blog across, or take everything with you
      </h2>
      <label className="flex flex-col gap-1 text-sm font-medium">
        Import a WordPress export file (Tools › Export › Posts in WordPress)
        <input
          type="file"
          accept=".xml,application/xml,text/xml"
          className="text-sm"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) run.mutate(f);
            e.target.value = "";
          }}
        />
      </label>
      {run.isPending && <p className="m-0 text-muted">Importing…</p>}
      {run.isError && (
        <p role="alert" className="m-0 text-warning">
          {run.error instanceof ApiError ? run.error.message : "The import failed."}
        </p>
      )}
      {result && (
        <div role="status" className="flex flex-col gap-1 rounded-lg bg-tint p-3 text-sm">
          <strong>
            {result.count} {result.count === 1 ? "post" : "posts"} imported as drafts
          </strong>
          <span>
            {result.redirects} old{" "}
            {result.redirects === 1 ? "address redirects" : "addresses redirect"} here once
            published. {result.images_not_copied} pictures weren&apos;t copied
            {result.skipped ? `; ${result.skipped} pages and other items were skipped` : ""}.
          </span>
          <span className="text-muted">{result.note}</span>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <a
          href={homepageApi.exportUrl}
          className={`${secondary} inline-flex items-center no-underline`}
        >
          Download everything (.zip)
        </a>
        <span className="text-sm text-muted">
          Posts as Markdown with their details, your original pictures and the redirects.
        </span>
      </div>
    </section>
  );
}
