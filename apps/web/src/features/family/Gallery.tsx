/**
 * Galleries. A person's gallery shows every picture tagged to them, by decade, saying
 * whether it shows them, is about them, or shows their world. The family gallery has
 * everything, and helps sort photos from the Archive by suggesting who's in them.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router";
import { api, ApiError, archiveApi } from "../../lib/api";
import {
  RELATION_LABEL,
  storyApi,
  type GalleryItem,
  type PhotoSuggestion,
  type Relation,
} from "../../lib/story";

function Picture({
  item,
  alt,
}: {
  item: { file_id: string; has_preview: boolean; file_name: string };
  alt: string;
}) {
  return item.has_preview ? (
    <img
      src={`/api/v1/files/${item.file_id}/preview`}
      alt={alt}
      className="aspect-[4/3] w-full rounded-lg bg-tint object-cover"
      loading="lazy"
    />
  ) : (
    <div className="flex aspect-[4/3] w-full items-center justify-center rounded-lg bg-tint p-2 text-center text-sm text-muted">
      {item.file_name}
    </div>
  );
}

function byDecade(items: GalleryItem[]): [string, GalleryItem[]][] {
  const groups = new Map<string, GalleryItem[]>();
  for (const i of items) groups.set(i.decade, [...(groups.get(i.decade) ?? []), i]);
  return [...groups.entries()];
}

function invalidate(qc: ReturnType<typeof useQueryClient>, projectId: string) {
  qc.invalidateQueries({ queryKey: ["gallery", projectId] });
  qc.invalidateQueries({ queryKey: ["family-gallery", projectId] });
  qc.invalidateQueries({ queryKey: ["photo-suggestions", projectId] });
}

export function PersonGallery({ projectId, personId }: { projectId: string; personId: string }) {
  const qc = useQueryClient();
  const [filter, setFilter] = useState<Relation | "all">("all");
  const [editing, setEditing] = useState<string | null>(null);
  const items = useQuery({
    queryKey: ["gallery", projectId, personId],
    queryFn: () => storyApi.gallery(projectId, personId),
  });
  const order = useMutation({
    mutationFn: (ids: string[]) => storyApi.order(projectId, personId, ids),
    onSuccess: (data) => qc.setQueryData(["gallery", projectId, personId], data),
  });
  const untag = useMutation({
    mutationFn: (item: string) => storyApi.untag(projectId, item, personId),
    onSuccess: () => invalidate(qc, projectId),
  });
  const all = items.data ?? [];
  const shown = all.filter((i) => filter === "all" || i.relation === filter);
  const move = (id: string, by: number) => {
    const ids = all.map((i) => i.id);
    const at = ids.indexOf(id);
    const to = at + by;
    if (to < 0 || to >= ids.length) return;
    [ids[at], ids[to]] = [ids[to], ids[at]];
    order.mutate(ids);
  };

  return (
    <section aria-label="Gallery" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <label className="flex flex-col gap-1 text-sm font-medium">
          Show
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as Relation | "all")}
            className="min-h-11 rounded-lg border border-control bg-surface px-2"
          >
            <option value="all">Everything ({all.length})</option>
            <option value="shows">Pictures of them</option>
            <option value="about">Documents about them</option>
            <option value="context">Their world</option>
          </select>
        </label>
        <Link to={`/projects/${projectId}/gallery`}>Family gallery and sorting photos →</Link>
      </div>
      {items.isPending && <p className="m-0 text-muted">Loading…</p>}
      {items.data?.length === 0 && (
        <p className="m-0">
          No pictures yet. Upload photos to the Archive, then sort them in the{" "}
          <Link to={`/projects/${projectId}/gallery`}>family gallery</Link>.
        </p>
      )}
      {byDecade(shown).map(([decade, group]) => (
        <section key={decade} aria-label={decade} className="flex flex-col gap-2">
          <h3 className="m-0 text-base font-semibold">{decade}</h3>
          <ul className="m-0 grid list-none grid-cols-2 gap-3 p-0 sm:grid-cols-3 lg:grid-cols-4">
            {group.map((i) => (
              <li key={i.id} className="flex flex-col gap-1 text-sm">
                <Picture item={i} alt={i.caption || i.file_name} />
                <span
                  className={`self-start rounded-full px-2 py-0.5 text-xs font-semibold ${i.relation === "context" ? "bg-tint text-muted" : "bg-selected"}`}
                >
                  {RELATION_LABEL[i.relation ?? "shows"]}
                </span>
                {i.caption && <span>{i.caption}</span>}
                <span className="text-muted">
                  {[i.date_text, i.place_text].filter(Boolean).join(" · ")}
                </span>
                {i.people.length > 1 && (
                  <span className="text-muted">
                    With{" "}
                    {i.people
                      .filter((p) => p.id !== personId)
                      .map((p, n) => (
                        <span key={p.id}>
                          {n > 0 && ", "}
                          <Link to={`/projects/${projectId}/people/${p.id}?view=gallery`}>
                            {p.name}
                          </Link>
                        </span>
                      ))}
                  </span>
                )}
                {editing === i.id ? (
                  <EditCaption projectId={projectId} item={i} onDone={() => setEditing(null)} />
                ) : (
                  <span className="flex flex-wrap gap-1">
                    <button
                      type="button"
                      aria-label={`Move ${i.file_name} earlier`}
                      onClick={() => move(i.id, -1)}
                      className="min-h-9 min-w-9 cursor-pointer rounded border border-control bg-surface"
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      aria-label={`Move ${i.file_name} later`}
                      onClick={() => move(i.id, 1)}
                      className="min-h-9 min-w-9 cursor-pointer rounded border border-control bg-surface"
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditing(i.id)}
                      className="min-h-9 cursor-pointer rounded border border-control bg-surface px-2"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => untag.mutate(i.id)}
                      className="min-h-9 cursor-pointer rounded border border-control bg-surface px-2"
                    >
                      Not them
                    </button>
                  </span>
                )}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </section>
  );
}

function EditCaption({
  projectId,
  item,
  onDone,
}: {
  projectId: string;
  item: GalleryItem;
  onDone: () => void;
}) {
  const qc = useQueryClient();
  const [caption, setCaption] = useState(item.caption);
  const [date, setDate] = useState(item.date_text);
  const [place, setPlace] = useState(item.place_text);
  const save = useMutation({
    mutationFn: () =>
      storyApi.edit(projectId, item.id, { caption, date_text: date, place_text: place }),
    onSuccess: () => {
      invalidate(qc, projectId);
      onDone();
    },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate();
  };
  return (
    <form onSubmit={submit} className="flex flex-col gap-1">
      <label className="flex flex-col text-xs font-medium">
        Caption
        <input
          value={caption}
          onChange={(e) => setCaption(e.target.value)}
          className="min-h-9 rounded border border-control px-2 font-normal"
        />
      </label>
      <label className="flex flex-col text-xs font-medium">
        When (as known)
        <input
          value={date}
          onChange={(e) => setDate(e.target.value)}
          placeholder="about 1920"
          className="min-h-9 rounded border border-control px-2 font-normal"
        />
      </label>
      <label className="flex flex-col text-xs font-medium">
        Where
        <input
          value={place}
          onChange={(e) => setPlace(e.target.value)}
          className="min-h-9 rounded border border-control px-2 font-normal"
        />
      </label>
      <span className="flex gap-1">
        <button
          type="submit"
          className="min-h-9 cursor-pointer rounded bg-accent px-3 font-semibold text-white"
        >
          Save
        </button>
        <button
          type="button"
          onClick={onDone}
          className="min-h-9 cursor-pointer rounded border border-control bg-surface px-2"
        >
          Cancel
        </button>
      </span>
    </form>
  );
}

export function FamilyGalleryPage() {
  const { projectId = "" } = useParams();
  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.project(projectId),
  });
  const items = useQuery({
    queryKey: ["family-gallery", projectId],
    queryFn: () => storyApi.familyGallery(projectId),
  });
  return (
    <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-5 px-4 py-8 sm:px-12">
      <div>
        <div className="text-[13px] font-semibold text-muted uppercase">
          <Link to={`/projects/${projectId}/people`}>Family tree</Link> · Gallery
        </div>
        <h1 className="m-0 font-serif text-[32px] font-semibold">{project.data?.title ?? "…"}</h1>
        <p className="mt-1 mb-0 text-muted">
          Every picture in the family&apos;s galleries. A group photo appears in each tagged
          person&apos;s gallery.
        </p>
      </div>
      <SortPhotos projectId={projectId} />
      <section aria-label="Family gallery" className="flex flex-col gap-3">
        <h2 className="m-0 text-xl font-semibold">In the galleries</h2>
        {items.data?.length === 0 && <p className="m-0">Nothing yet.</p>}
        {byDecade(items.data ?? []).map(([decade, group]) => (
          <section key={decade} aria-label={decade} className="flex flex-col gap-2">
            <h3 className="m-0 text-base font-semibold">{decade}</h3>
            <ul className="m-0 grid list-none grid-cols-2 gap-3 p-0 sm:grid-cols-3 lg:grid-cols-4">
              {group.map((i) => (
                <li key={i.id} className="flex flex-col gap-1 text-sm">
                  <Picture item={i} alt={i.caption || i.file_name} />
                  {i.caption && <span>{i.caption}</span>}
                  <span className="flex flex-wrap gap-x-2">
                    {i.people.map((p) => (
                      <Link key={p.id} to={`/projects/${projectId}/people/${p.id}?view=gallery`}>
                        {p.name}
                        {p.relation === "context"
                          ? " (their world)"
                          : p.relation === "about"
                            ? " (about them)"
                            : ""}
                      </Link>
                    ))}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </section>
    </div>
  );
}

function SortPhotos({ projectId }: { projectId: string }) {
  const suggestions = useQuery({
    queryKey: ["photo-suggestions", projectId],
    queryFn: () => storyApi.suggestions(projectId),
    retry: false,
  });
  if (suggestions.isError) return null; // only editors can sort photos
  const rows = suggestions.data ?? [];
  return (
    <section
      aria-label="Sort your photos"
      className="flex flex-col gap-2 rounded-lg border border-line bg-surface p-4"
    >
      <h2 className="m-0 text-xl font-semibold">Sort your photos</h2>
      <p className="m-0 text-sm text-muted">
        Pictures in your Archive that aren&apos;t in a gallery yet. Suggestions come from the file
        and folder names and the camera&apos;s date, checked against when people were alive. Nothing
        is tagged until you choose.
      </p>
      {suggestions.isPending && <p className="m-0 text-muted">Looking at your pictures…</p>}
      {suggestions.data && rows.length === 0 && (
        <p className="m-0">
          Every picture is sorted.{" "}
          <Link to={`/archive?project=${projectId}`}>Upload more to the Archive</Link>.
        </p>
      )}
      <ul className="m-0 flex list-none flex-col gap-3 p-0">
        {rows.map((r) => (
          <SortRow key={r.file_id} projectId={projectId} row={r} />
        ))}
      </ul>
    </section>
  );
}

function SortRow({ projectId, row }: { projectId: string; row: PhotoSuggestion }) {
  const qc = useQueryClient();
  const [relation, setRelation] = useState<Relation>("shows");
  const [q, setQ] = useState("");
  const people = useQuery({
    queryKey: ["people", projectId, q],
    queryFn: () => archiveApi.people(projectId, q),
    enabled: q.trim().length > 1,
  });
  const add = useMutation({
    mutationFn: (personId: string) =>
      storyApi.add(projectId, {
        file_id: row.file_id,
        date_text: row.year_hint ? `${row.year_hint}` : "",
        tags: [{ person_id: personId, relation }],
      }),
    onSuccess: () => invalidate(qc, projectId),
  });
  return (
    <li className="grid grid-cols-[120px_1fr] gap-3 border-t border-line-soft pt-3">
      <Picture item={row} alt={row.file_name} />
      <div className="flex flex-col gap-1 text-sm">
        <strong>{row.file_name}</strong>
        <span className="text-muted">
          {[
            row.folder && `In ${row.folder}`,
            row.year_hint && `${row.year_hint}, from ${row.year_from}`,
          ]
            .filter(Boolean)
            .join(" · ")}
        </span>
        <label className="flex items-center gap-2">
          This picture
          <select
            value={relation}
            onChange={(e) => setRelation(e.target.value as Relation)}
            className="min-h-9 rounded border border-control bg-surface px-1"
          >
            <option value="shows">shows</option>
            <option value="about">is a document about</option>
            <option value="context">shows the world of</option>
          </select>
        </label>
        {row.suggestions.length > 0 && (
          <ul
            aria-label={`Suggested for ${row.file_name}`}
            className="m-0 flex list-none flex-wrap gap-2 p-0"
          >
            {row.suggestions.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => add.mutate(s.id)}
                  title={s.reason}
                  className="min-h-11 cursor-pointer rounded-lg border border-accent bg-surface px-3 text-left"
                >
                  {s.name}
                  <span className="block text-xs text-muted">{s.reason}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <label className="flex flex-col gap-1">
          <span>{row.suggestions.length ? "Or someone else" : "Who is it?"}</span>
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="min-h-11 rounded-lg border border-control bg-surface px-3"
          />
        </label>
        {(people.data ?? []).slice(0, 6).map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => add.mutate(p.id)}
            className="min-h-11 cursor-pointer self-start rounded-lg border border-control bg-surface px-3"
          >
            {p.name}
          </button>
        ))}
        {add.isError && (
          <p className="m-0 text-warning">
            {add.error instanceof ApiError ? add.error.message : "It couldn't be added."}
          </p>
        )}
      </div>
    </li>
  );
}
