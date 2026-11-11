/** Your homepage and posts (mirror services/api/publishing/api.py). */
import { ApiError, csrfToken, request } from "./api";

export interface Homepage {
  slug: string;
  title: string;
  tagline: string;
  about: string;
  live: boolean;
  url: string;
}

export type PostStatus = "draft" | "published" | "unpublished";
export type Rights = "own" | "permission" | "public_domain" | "unclear";

export interface PostImage {
  id: string;
  file_id: string;
  file_name: string;
  caption: string;
  rights: Rights;
  credit: string;
  visibility: string;
}

export interface Post {
  id: string;
  title: string;
  slug: string;
  summary: string;
  status: PostStatus;
  source: "written" | "chat" | "wordpress";
  published_at: string | null;
  original_url: string;
  first_published: string | null;
  url: string;
  updated_at: string;
  body?: string;
  images?: PostImage[];
  note?: string;
}

export interface CheckItem {
  kind: string;
  text: string;
}

export interface CheckResult {
  ok: boolean;
  blockers: CheckItem[];
  warnings: CheckItem[];
}

export interface Social {
  link: string;
  posts: { for: string; text: string; limit: number | null }[];
  note: string;
}

export interface ImportResult {
  count: number;
  skipped: number;
  images_not_copied: number;
  redirects: number;
  note: string;
  posts: { title: string; slug: string; was_published: boolean }[];
}

export const RIGHTS_LABELS: Record<Rights, string> = {
  own: "I took or made it",
  permission: "I have permission",
  public_domain: "Public domain or openly licensed",
  unclear: "Not sure",
};

export const STATUS_LABELS: Record<PostStatus, string> = {
  draft: "Draft",
  published: "Published",
  unpublished: "Taken down",
};

export const SOURCE_LABELS: Record<Post["source"], string> = {
  written: "Written here",
  chat: "Drafted in chat",
  wordpress: "Imported from WordPress",
};

type PostFields = { title: string; summary: string; body: string; original_url?: string };

export const homepageApi = {
  get: () => request<Homepage | null>("GET", "/api/v1/home"),
  save: (h: Omit<Homepage, "url">) => request<Homepage>("PUT", "/api/v1/home", h),
  posts: () => request<Post[]>("GET", "/api/v1/home/posts"),
  post: (id: string) => request<Post>("GET", `/api/v1/home/posts/${id}`),
  create: (p: Partial<PostFields>) => request<Post>("POST", "/api/v1/home/posts", p),
  edit: (id: string, p: PostFields) => request<Post>("PATCH", `/api/v1/home/posts/${id}`, p),
  remove: (id: string) => request<void>("DELETE", `/api/v1/home/posts/${id}`),
  attach: (id: string, img: { file_id: string; caption: string; rights: Rights; credit: string }) =>
    request<{ id: string; markdown: string }>("POST", `/api/v1/home/posts/${id}/images`, img),
  detach: (id: string, imageId: string) =>
    request<void>("DELETE", `/api/v1/home/posts/${id}/images/${imageId}`),
  check: (id: string) => request<CheckResult>("POST", `/api/v1/home/posts/${id}/check`),
  publish: (id: string, confirmWarnings: boolean) =>
    request<Post>("POST", `/api/v1/home/posts/${id}/publish`, {
      confirm_warnings: confirmWarnings,
    }),
  unpublish: (id: string) => request<Post>("POST", `/api/v1/home/posts/${id}/unpublish`),
  social: (id: string) => request<Social>("GET", `/api/v1/home/posts/${id}/social`),
  exportUrl: "/api/v1/home/export",
};

export async function importWordPress(file: File): Promise<ImportResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/v1/home/import/wordpress", {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRFToken": await csrfToken(), Accept: "application/json" },
    body: form,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, data?.detail ?? `Import failed (${res.status})`);
  return data as ImportResult;
}

/** A rough preview of the Markdown subset; the server's render is what's published. */
export function previewHtml(body: string, images: PostImage[]): string {
  const esc = (s: string) =>
    s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#x27;");
  const inline = (s: string) =>
    esc(s)
      .replace(
        /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
        '<a href="$2" rel="nofollow noopener" target="_blank">$1</a>',
      )
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");
  const byId = new Map(images.map((i) => [i.file_id, i]));
  const out: string[] = [];
  for (const block of body
    .replace(/\r\n/g, "\n")
    .trim()
    .split(/\n\s*\n/)) {
    let lines = block
      .split("\n")
      .map((l) => l.trimEnd())
      .filter((l) => l.trim());
    if (!lines.length) continue;
    const img =
      lines.length === 1 && /^!\[([^\]]*)\]\(image:([0-9a-f-]{36})\)$/.exec(lines[0].trim());
    if (img) {
      const meta = byId.get(img[2]);
      if (meta) {
        const cap = esc(meta.caption || img[1]);
        const credit = meta.credit ? ` <span class="text-muted">${esc(meta.credit)}</span>` : "";
        out.push(
          `<figure><img src="/api/v1/files/${meta.file_id}/preview" alt="${cap}"><figcaption>${cap}${credit}</figcaption></figure>`,
        );
      } else {
        out.push(`<p class="text-warning">[A picture that isn't attached to this post]</p>`);
      }
      continue;
    }
    const first = lines[0];
    if (first.startsWith("### ")) {
      out.push(`<h3>${inline(first.slice(4))}</h3>`);
      lines = lines.slice(1);
    } else if (first.startsWith("## ")) {
      out.push(`<h2>${inline(first.slice(3))}</h2>`);
      lines = lines.slice(1);
    }
    if (!lines.length) continue;
    if (lines.every((l) => l.startsWith("> ") || l === ">")) {
      out.push(`<blockquote>${lines.map((l) => inline(l.slice(2))).join("<br>")}</blockquote>`);
    } else if (lines.every((l) => l.startsWith("- "))) {
      out.push(`<ul>${lines.map((l) => `<li>${inline(l.slice(2))}</li>`).join("")}</ul>`);
    } else {
      out.push(`<p>${lines.map(inline).join("<br>")}</p>`);
    }
  }
  return out.join("\n");
}
