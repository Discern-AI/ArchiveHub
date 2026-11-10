/** Thin client for the ArchiveHub API. Same-origin; the session cookie authenticates. */

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

let csrfReady: Promise<void> | null = null;

/** Make sure the csrftoken cookie exists, then return it. */
export async function csrfToken(): Promise<string> {
  let token = readCookie("csrftoken");
  if (!token) {
    csrfReady ??= fetch("/api/v1/csrf", { credentials: "same-origin" }).then(() => undefined);
    await csrfReady;
    csrfReady = null;
    token = readCookie("csrftoken");
  }
  return token ?? "";
}

export async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  init: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") headers["X-CSRFToken"] = await csrfToken();

  const res = await fetch(path, {
    method,
    credentials: "same-origin",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    ...init,
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail =
      typeof data?.detail === "string"
        ? data.detail
        : (data?.errors?.[0]?.message ?? `Request failed (${res.status})`);
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

// --- Types (mirror services/api/projects/api.py) ---------------------------

export interface Project {
  id: string;
  title: string;
  summary: string;
  visibility: string;
  is_owner: boolean;
  created_at: string;
  updated_at: string;
}

export interface Chat {
  id: string;
  project_id: string | null;
  title: string;
  created_at: string;
  updated_at: string;
}

export type MessageStatus = "streaming" | "complete" | "incomplete" | "refused" | "error";

/** One line of "What I checked", built by the server from actual tool calls. */
export interface CheckedItem {
  status: string;
  text: string;
}

/** A citation the server resolved from tool results; the model can't invent these. */
export interface SourceRef {
  n: number;
  kind: "record" | "source";
  id: string;
  label: string;
  url: string;
  source: string;
}

/** A question where the sources disagreed, which the Evidence panel can open. */
export interface Dispute {
  subject_type: string;
  subject_id: string;
  subject: string;
  predicate: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  status: MessageStatus;
  checked?: CheckedItem[];
  sources?: SourceRef[];
  disputes?: Dispute[];
  created_at: string;
}

// --- Explorer, basket and evidence ----------------------------------------------

export interface ExplorerSource {
  key: string;
  name: string;
  description: string;
  access_type: "hosted" | "live_api" | "metadata" | "external_only";
  capabilities: string[];
  licence: string;
  attribution: string;
  storage: string;
  available: boolean;
  note?: string;
}

export interface ConnectorRecord {
  connector: string;
  id: string;
  title: string;
  description: string;
  record_type: string;
  url: string;
  date_text: string;
  latitude: number | null;
  longitude: number | null;
  fields: Record<string, unknown>;
  rights: string;
  attribution: string;
  citation?: string;
  storage?: string;
  source_name?: string;
}

export interface ExplorerPage {
  records: ConnectorRecord[];
  next_cursor: string | null;
  searched: string;
}

export interface BasketItem {
  id: string;
  connector: string;
  external_id: string;
  title: string;
  url: string;
  storage: string;
  note: string;
  created_at: string;
}

export interface EvidenceItem {
  record_title: string;
  record_key: string;
  source: string;
  url: string;
  what_it_says: string;
  stance: string;
  suggested_weight: string | null;
  weight_suggested_by: string | null;
}

export interface Claim {
  id: string;
  value: string;
  date: string | null;
  status: string;
  method: string;
  note: string;
  evidence: EvidenceItem[];
}

export interface Evidence {
  subject: { type: string; id: string; name: string };
  predicate: string;
  disputed: boolean;
  claims: Claim[];
  decision: {
    chosen_id: string | null;
    keep_disputed: boolean;
    reason: string;
    decided_at: string;
  } | null;
}

// --- Archive and family --------------------------------------------------------

export interface Folder {
  id: string;
  name: string;
}

export interface Job {
  id: string;
  kind: string;
  status: "awaiting_confirmation" | "queued" | "running" | "done" | "failed" | "cancelled";
  estimate_credits: number;
  credits_used: number;
  error: string;
  result: Record<string, unknown>;
  created_at: string;
}

export interface ArchiveFile {
  id: string;
  name: string;
  folder_id: string | null;
  kind: string;
  size: number;
  status: string;
  status_detail: string;
  scan_note: string;
  page_count: number | null;
  has_preview: boolean;
  created_at: string;
}

export interface ArchiveFileDetail extends ArchiveFile {
  sha256: string;
  metadata: Record<string, unknown>;
  texts: { id: string; method: string; engine: string; note: string; text: string }[];
  jobs: Job[];
  can_process: { kind: string; label: string }[];
}

export interface PersonBrief {
  id: string;
  name: string;
  living: boolean;
  birth: string;
  death: string;
}

export interface PersonDetail extends PersonBrief {
  parents: PersonBrief[];
  partners: PersonBrief[];
  children: PersonBrief[];
  facts: {
    question: string;
    disputed: boolean;
    answers: {
      id: string;
      value: string;
      status: string;
      method: string;
      note: string;
      in_use: boolean;
      evidence: {
        title: string;
        url: string;
        what_it_says: string;
        source?: string;
        stance?: string;
      }[];
    }[];
  }[];
}

export async function uploadFile(
  projectId: string,
  file: File,
  folderId?: string | null,
): Promise<ArchiveFile> {
  const form = new FormData();
  form.append("file", file);
  if (folderId) form.append("folder_id", folderId);
  const res = await fetch(`/api/v1/projects/${projectId}/files`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-CSRFToken": await csrfToken(), Accept: "application/json" },
    body: form,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, data?.detail ?? `Upload failed (${res.status})`);
  return data as ArchiveFile;
}

export const archiveApi = {
  folders: (projectId: string) => request<Folder[]>("GET", `/api/v1/projects/${projectId}/folders`),
  createFolder: (projectId: string, name: string) =>
    request<Folder>("POST", `/api/v1/projects/${projectId}/folders`, { name }),
  files: (projectId: string, folderId?: string | null) =>
    request<ArchiveFile[]>(
      "GET",
      `/api/v1/projects/${projectId}/files${folderId ? `?folder_id=${folderId}` : ""}`,
    ),
  file: (id: string) => request<ArchiveFileDetail>("GET", `/api/v1/files/${id}`),
  deleteFile: (id: string) => request<void>("DELETE", `/api/v1/files/${id}`),
  requestJob: (fileId: string, kind: string) =>
    request<Job>("POST", `/api/v1/files/${fileId}/jobs`, { kind }),
  confirmJob: (jobId: string) => request<Job>("POST", `/api/v1/jobs/${jobId}/confirm`),
  cancelJob: (jobId: string) => request<Job>("POST", `/api/v1/jobs/${jobId}/cancel`),
  people: (projectId: string, q = "") =>
    request<PersonBrief[]>(
      "GET",
      `/api/v1/projects/${projectId}/people${q ? `?q=${encodeURIComponent(q)}` : ""}`,
    ),
  person: (projectId: string, personId: string) =>
    request<PersonDetail>("GET", `/api/v1/projects/${projectId}/people/${personId}`),
  addClaim: (
    projectId: string,
    personId: string,
    body: { predicate: string; value: string; status: string; note: string },
  ) =>
    request<{ id: string }>(
      "POST",
      `/api/v1/projects/${projectId}/people/${personId}/claims`,
      body,
    ),
};

export const ACCESS_LABELS: Record<ExplorerSource["access_type"], string> = {
  hosted: "Hosted here",
  live_api: "Searched live",
  metadata: "Metadata only",
  external_only: "Link-out only",
};

export const api = {
  projects: () => request<Project[]>("GET", "/api/v1/projects"),
  project: (id: string) => request<Project>("GET", `/api/v1/projects/${id}`),
  createProject: (title: string, summary = "") =>
    request<Project>("POST", "/api/v1/projects", { title, summary }),
  deleteProject: (id: string) => request<void>("DELETE", `/api/v1/projects/${id}`),
  chats: (projectId?: string) =>
    request<Chat[]>("GET", projectId ? `/api/v1/chats?project_id=${projectId}` : "/api/v1/chats"),
  createChat: (projectId?: string | null) =>
    request<Chat>("POST", "/api/v1/chats", { project_id: projectId ?? null }),
  messages: (chatId: string) => request<Message[]>("GET", `/api/v1/chats/${chatId}/messages`),
  chat: (chatId: string) => request<Chat>("GET", `/api/v1/chats/${chatId}`),

  explorerSources: () => request<ExplorerSource[]>("GET", "/api/v1/explorer/sources"),
  explorerSearch: (key: string, q: string, cursor?: string | null) => {
    const params = new URLSearchParams({ q, page_size: "25" });
    if (cursor) params.set("cursor", cursor);
    return request<ExplorerPage>("GET", `/api/v1/explorer/${key}/search?${params}`);
  },
  explorerRecord: (key: string, id: string) =>
    request<ConnectorRecord>("GET", `/api/v1/explorer/${key}/records/${encodeURIComponent(id)}`),

  basket: (projectId: string) =>
    request<BasketItem[]>("GET", `/api/v1/projects/${projectId}/basket`),
  addToBasket: (projectId: string, connector: string, recordId: string) =>
    request<BasketItem>("POST", `/api/v1/projects/${projectId}/basket`, {
      connector,
      record_id: recordId,
    }),
  removeFromBasket: (projectId: string, itemId: string) =>
    request<void>("DELETE", `/api/v1/projects/${projectId}/basket/${itemId}`),

  evidence: (d: Dispute, projectId?: string | null) => {
    const params = new URLSearchParams({ predicate: d.predicate });
    if (projectId) params.set("project_id", projectId);
    return request<Evidence>("GET", `/api/v1/evidence/${d.subject_type}/${d.subject_id}?${params}`);
  },
  saveDecision: (
    projectId: string,
    d: Dispute,
    choice: { chosen_id?: string; keep_disputed?: boolean; reason: string },
  ) =>
    request<{ ok: boolean }>("PUT", `/api/v1/projects/${projectId}/decisions`, {
      subject_type: d.subject_type,
      subject_id: d.subject_id,
      predicate: d.predicate,
      ...choice,
    }),
};
