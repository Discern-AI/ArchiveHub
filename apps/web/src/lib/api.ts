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

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  status: MessageStatus;
  checked?: CheckedItem[];
  sources?: SourceRef[];
  created_at: string;
}

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
};
