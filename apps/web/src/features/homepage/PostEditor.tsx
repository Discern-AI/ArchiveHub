/**
 * Write a post, add pictures with their rights, check it and publish it. Publishing needs
 * every blocker fixed, and each warning (a living person named, a private picture)
 * confirmed by you. Chat can draft a post, but only you can publish it.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { api, ApiError, archiveApi } from "../../lib/api";
import {
  homepageApi,
  previewHtml,
  RIGHTS_LABELS,
  SOURCE_LABELS,
  STATUS_LABELS,
  type CheckResult,
  type Post,
  type PostImage,
  type Rights,
} from "../../lib/homepage";

const input = "min-h-11 rounded-lg border border-control bg-surface px-2 font-normal";
const primary = "min-h-11 cursor-pointer rounded-lg bg-accent px-4 font-semibold text-white";
const secondary = "min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3";
const errorText = (e: unknown, fallback: string) => (e instanceof ApiError ? e.message : fallback);

type Fields = { title: string; summary: string; body: string; original_url: string };

export function PostEditorPage() {
  const { postId = "" } = useParams();
  const post = useQuery({
    queryKey: ["homepage-post", postId],
    queryFn: () => homepageApi.post(postId),
  });
  if (post.isPending) return <p className="p-8 text-muted">Loading the post…</p>;
  if (post.isError) return <p className="p-8 text-warning">This post couldn&apos;t load.</p>;
  return <Editor key={post.data.id} post={post.data} />;
}

function Editor({ post }: { post: Post }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [edits, setEdits] = useState<Fields | null>(null);
  const [preview, setPreview] = useState(false);
  const [check, setCheck] = useState<CheckResult | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [note, setNote] = useState("");
  const form: Fields = edits ?? {
    title: post.title,
    summary: post.summary,
    body: post.body ?? "",
    original_url: post.original_url,
  };
  const set = (k: keyof Fields, v: string) => setEdits({ ...form, [k]: v });
  const images = post.images ?? [];
  const refresh = (p?: Post) => {
    if (p) qc.setQueryData(["homepage-post", post.id], p);
    else qc.invalidateQueries({ queryKey: ["homepage-post", post.id] });
    qc.invalidateQueries({ queryKey: ["homepage-posts"] });
    setCheck(null);
    setConfirmed(false);
  };

  const save = useMutation({
    mutationFn: () => homepageApi.edit(post.id, form),
    onSuccess: (p) => {
      setEdits(null);
      refresh(p);
    },
  });
  const runCheck = useMutation({
    mutationFn: async () => {
      if (edits) {
        refresh(await homepageApi.edit(post.id, form));
        setEdits(null);
      }
      return homepageApi.check(post.id);
    },
    onSuccess: setCheck,
  });
  const publish = useMutation({
    mutationFn: () => homepageApi.publish(post.id, confirmed),
    onSuccess: (p) => {
      refresh(p);
      setNote(p.note ?? "Published.");
    },
  });
  const unpublish = useMutation({
    mutationFn: () => homepageApi.unpublish(post.id),
    onSuccess: (p) => {
      refresh(p);
      setNote("Taken down. Its address no longer shows the post.");
    },
  });
  const remove = useMutation({
    mutationFn: () => homepageApi.remove(post.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["homepage-posts"] });
      navigate("/homepage");
    },
  });
  const insert = (markdown: string) => set("body", `${form.body.trimEnd()}\n\n${markdown}\n`);

  return (
    <div className="mx-auto flex w-full max-w-[860px] flex-col gap-4 px-4 py-8 sm:px-10">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Link to="/homepage">‹ Your homepage</Link>
        <span className="text-sm text-muted">
          {STATUS_LABELS[post.status]} · {SOURCE_LABELS[post.source]}
          {post.status === "published" && (
            <>
              {" · "}
              <a href={post.url} target="_blank" rel="noreferrer">
                View
              </a>
            </>
          )}
        </span>
      </div>
      <label className="flex flex-col gap-1 text-sm font-medium">
        Title
        <input
          className={`${input} font-serif text-xl`}
          value={form.title}
          onChange={(e) => set("title", e.target.value)}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm font-medium">
        Summary (shown on your homepage and when shared)
        <input
          className={input}
          value={form.summary}
          onChange={(e) => set("summary", e.target.value)}
        />
      </label>
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-medium">{preview ? "Preview" : "Post"}</span>
          <button type="button" className={secondary} onClick={() => setPreview(!preview)}>
            {preview ? "Edit" : "Preview"}
          </button>
        </div>
        {preview ? (
          <article
            aria-label="Preview"
            className="post-preview rounded-lg border border-line bg-surface p-4 [&_blockquote]:border-l-4 [&_blockquote]:border-line [&_blockquote]:pl-3 [&_figure]:m-0 [&_img]:max-w-full"
            // previewHtml escapes everything first and only adds the subset's tags
            dangerouslySetInnerHTML={{ __html: previewHtml(form.body, images) }}
          />
        ) : (
          <textarea
            aria-label="Post"
            className={`${input} min-h-72 p-3 leading-relaxed`}
            value={form.body}
            onChange={(e) => set("body", e.target.value)}
          />
        )}
        <p className="m-0 text-xs text-muted">
          ## Heading · ### Smaller heading · &gt; Quotation · - List item · **bold** · *italic* ·
          [link text](https://…)
        </p>
      </div>
      <label className="flex flex-col gap-1 text-sm font-medium">
        If this was first published elsewhere, its address there
        <input
          className={input}
          value={form.original_url}
          placeholder="https://"
          onChange={(e) => set("original_url", e.target.value)}
        />
        <span className="font-normal text-muted">
          Search engines are then told the original is the main copy.
        </span>
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          className={secondary}
          disabled={!edits || save.isPending}
          onClick={() => save.mutate()}
        >
          {edits ? "Save draft" : "Saved"}
        </button>
        {save.isError && (
          <span role="alert" className="text-sm text-warning">
            {errorText(save.error, "Couldn't save.")}
          </span>
        )}
      </div>

      <Pictures post={post} images={images} onInsert={insert} onChange={() => refresh()} />

      <section
        aria-label="Check and publish"
        className="flex flex-col gap-3 rounded-lg border border-line bg-surface p-4"
      >
        <h2 className="m-0 text-lg font-semibold">Check and publish</h2>
        {post.status === "published" ? (
          <>
            <p className="m-0">
              This post is public. Editing it takes it back to a draft, so changes are checked too.
            </p>
            <div className="flex flex-wrap gap-3">
              <button type="button" className={secondary} onClick={() => unpublish.mutate()}>
                Take it down
              </button>
            </div>
            <SocialText postId={post.id} />
          </>
        ) : (
          <>
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                className={secondary}
                disabled={runCheck.isPending}
                onClick={() => runCheck.mutate()}
              >
                Check before publishing
              </button>
            </div>
            {runCheck.isError && (
              <p role="alert" className="m-0 text-warning">
                {errorText(runCheck.error, "The check failed.")}
              </p>
            )}
            {check && <CheckList check={check} confirmed={confirmed} onConfirm={setConfirmed} />}
            {check?.ok && (
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  className={primary}
                  disabled={(check.warnings.length > 0 && !confirmed) || publish.isPending}
                  onClick={() => publish.mutate()}
                >
                  Approve and publish
                </button>
              </div>
            )}
            {publish.isError && (
              <p role="alert" className="m-0 text-warning">
                {errorText(publish.error, "Couldn't publish.")}
              </p>
            )}
          </>
        )}
        {note && (
          <p role="status" className="m-0 font-medium text-accent">
            {note}
          </p>
        )}
      </section>

      <div>
        <button
          type="button"
          className={`${secondary} text-warning`}
          onClick={() => {
            if (window.confirm("Delete this post? This can't be undone.")) remove.mutate();
          }}
        >
          Delete post
        </button>
      </div>
    </div>
  );
}

function CheckList({
  check,
  confirmed,
  onConfirm,
}: {
  check: CheckResult;
  confirmed: boolean;
  onConfirm: (v: boolean) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      {check.blockers.length === 0 && check.warnings.length === 0 && (
        <p className="m-0 font-medium text-accent">Nothing to fix. Ready to publish.</p>
      )}
      {check.blockers.length > 0 && (
        <div>
          <h3 className="m-0 text-base font-semibold text-warning">Fix before publishing</h3>
          <ul className="m-0 pl-5">
            {check.blockers.map((b, i) => (
              <li key={i}>{b.text}</li>
            ))}
          </ul>
        </div>
      )}
      {check.warnings.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="m-0 text-base font-semibold">Check these</h3>
          <ul className="m-0 pl-5">
            {check.warnings.map((w, i) => (
              <li key={i}>{w.text}</li>
            ))}
          </ul>
          {check.ok && (
            <label className="flex items-center gap-2 font-medium">
              <input
                type="checkbox"
                className="size-5"
                checked={confirmed}
                onChange={(e) => onConfirm(e.target.checked)}
              />
              I&apos;ve checked these and want to publish
            </label>
          )}
        </div>
      )}
    </div>
  );
}

function Pictures({
  post,
  images,
  onInsert,
  onChange,
}: {
  post: Post;
  images: PostImage[];
  onInsert: (markdown: string) => void;
  onChange: () => void;
}) {
  const [choosing, setChoosing] = useState(false);
  return (
    <section
      aria-label="Pictures"
      className="flex flex-col gap-3 rounded-lg border border-line bg-surface p-4"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="m-0 text-lg font-semibold">Pictures</h2>
        <button type="button" className={secondary} onClick={() => setChoosing(!choosing)}>
          {choosing ? "Done" : "Add a picture from your Archive"}
        </button>
      </div>
      <p className="m-0 text-sm text-muted">
        Say whose each picture is before publishing. Pictures are shown from a smaller copy with
        camera details (including any location) removed.
      </p>
      {images.map((i) => (
        <ImageRow key={i.id} postId={post.id} image={i} onInsert={onInsert} onChange={onChange} />
      ))}
      {choosing && (
        <Chooser
          attached={new Set(images.map((i) => i.file_id))}
          onPick={async (fileId, name) => {
            const r = await homepageApi.attach(post.id, {
              file_id: fileId,
              caption: "",
              rights: "unclear",
              credit: "",
            });
            onInsert(r.markdown.replace(/^!\[[^\]]*\]/, `![${name}]`));
            onChange();
          }}
        />
      )}
    </section>
  );
}

function ImageRow({
  postId,
  image,
  onInsert,
  onChange,
}: {
  postId: string;
  image: PostImage;
  onInsert: (markdown: string) => void;
  onChange: () => void;
}) {
  const [edits, setEdits] = useState<{ caption: string; rights: Rights; credit: string } | null>(
    null,
  );
  const form = edits ?? { caption: image.caption, rights: image.rights, credit: image.credit };
  const save = useMutation({
    mutationFn: () => homepageApi.attach(postId, { file_id: image.file_id, ...form }),
    onSuccess: () => {
      setEdits(null);
      onChange();
    },
  });
  const detach = useMutation({
    mutationFn: () => homepageApi.detach(postId, image.id),
    onSuccess: onChange,
  });
  const needsCredit = form.rights === "permission" || form.rights === "public_domain";
  return (
    <div className="flex flex-wrap gap-3 border-t border-line-soft pt-3">
      <img
        src={`/api/v1/files/${image.file_id}/preview`}
        alt=""
        className="h-24 w-24 rounded object-cover"
      />
      <div className="flex min-w-60 flex-1 flex-col gap-2">
        <span className="text-sm font-medium">
          {image.file_name}
          {image.visibility === "private" && (
            <span className="ml-2 text-private">Private in your Archive</span>
          )}
        </span>
        <input
          aria-label={`Caption for ${image.file_name}`}
          className={input}
          placeholder="Caption"
          value={form.caption}
          onChange={(e) => setEdits({ ...form, caption: e.target.value })}
        />
        <select
          aria-label={`Rights for ${image.file_name}`}
          className={input}
          value={form.rights}
          onChange={(e) => setEdits({ ...form, rights: e.target.value as Rights })}
        >
          {(Object.keys(RIGHTS_LABELS) as Rights[]).map((r) => (
            <option key={r} value={r}>
              {RIGHTS_LABELS[r]}
            </option>
          ))}
        </select>
        {needsCredit && (
          <input
            aria-label={`Credit for ${image.file_name}`}
            className={input}
            placeholder="Credit: who made it, and where it's from"
            value={form.credit}
            onChange={(e) => setEdits({ ...form, credit: e.target.value })}
          />
        )}
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className={secondary}
            disabled={!edits}
            onClick={() => save.mutate()}
          >
            Save picture details
          </button>
          <button
            type="button"
            className={secondary}
            onClick={() =>
              onInsert(`![${form.caption || image.file_name}](image:${image.file_id})`)
            }
          >
            Put in post
          </button>
          <button type="button" className={secondary} onClick={() => detach.mutate()}>
            Remove
          </button>
        </div>
      </div>
    </div>
  );
}

function Chooser({
  attached,
  onPick,
}: {
  attached: Set<string>;
  onPick: (fileId: string, name: string) => Promise<void>;
}) {
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const [chosen, setChosen] = useState("");
  const projectId = chosen || projects.data?.[0]?.id || "";
  const files = useQuery({
    queryKey: ["archive-files", projectId, "all"],
    queryFn: () => archiveApi.files(projectId),
    enabled: !!projectId,
  });
  const pictures = (files.data ?? []).filter(
    (f) => f.has_preview && f.kind === "image" && !attached.has(f.id),
  );
  const [error, setError] = useState("");
  return (
    <div className="flex flex-col gap-2 rounded-lg bg-tint p-3">
      {(projects.data?.length ?? 0) > 1 && (
        <label className="flex flex-col gap-1 text-sm font-medium">
          Project
          <select className={input} value={projectId} onChange={(e) => setChosen(e.target.value)}>
            {projects.data?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>
        </label>
      )}
      {files.isSuccess && pictures.length === 0 && (
        <p className="m-0 text-sm text-muted">
          {(files.data ?? []).some((f) => attached.has(f.id))
            ? "Every picture here is already in this post."
            : "No pictures here yet. Upload them in the Archive first."}
        </p>
      )}
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
        {pictures.map((f) => (
          <button
            key={f.id}
            type="button"
            className="cursor-pointer rounded border border-line bg-surface p-1 text-left text-xs"
            onClick={() =>
              onPick(f.id, f.name).catch((e) => setError(errorText(e, "Couldn't add it.")))
            }
          >
            <img
              src={`/api/v1/files/${f.id}/preview`}
              alt=""
              className="aspect-square w-full rounded object-cover"
            />
            <span className="block truncate">{f.name}</span>
          </button>
        ))}
      </div>
      {error && (
        <p role="alert" className="m-0 text-sm text-warning">
          {error}
        </p>
      )}
    </div>
  );
}

function SocialText({ postId }: { postId: string }) {
  const social = useQuery({
    queryKey: ["homepage-social", postId],
    queryFn: () => homepageApi.social(postId),
  });
  const [copied, setCopied] = useState("");
  if (!social.data) return null;
  return (
    <div className="flex flex-col gap-2">
      <h3 className="m-0 text-base font-semibold">Share it</h3>
      <p className="m-0 text-sm text-muted">{social.data.note}</p>
      {social.data.posts.map((s) => (
        <div key={s.for} className="flex flex-col gap-1">
          <span className="text-sm font-medium">
            {s.for}
            {s.limit && (
              <span className="font-normal text-muted">
                {" "}
                · {s.text.length} of {s.limit} characters
              </span>
            )}
          </span>
          <textarea
            readOnly
            aria-label={s.for}
            className={`${input} min-h-20 p-2`}
            value={s.text}
          />
          <div>
            <button
              type="button"
              className={secondary}
              onClick={() => navigator.clipboard?.writeText(s.text).then(() => setCopied(s.for))}
            >
              {copied === s.for ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
