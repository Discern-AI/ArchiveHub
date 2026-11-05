/** Accounts via django-allauth's headless API (browser client, session cookies). */
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, csrfToken } from "./api";

const BASE = "/_allauth/browser/v1";

export interface User {
  id: string;
  email: string;
  display: string;
}

async function allauth(method: string, path: string, body?: unknown) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-CSRFToken": await csrfToken(),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  return { res, data };
}

function firstError(data: { errors?: { message: string }[] }, fallback: string): string {
  return data?.errors?.[0]?.message ?? fallback;
}

/** The signed-in user, or null. 401 from allauth means "not signed in", not an error. */
export async function fetchSession(): Promise<User | null> {
  const res = await fetch(`${BASE}/auth/session`, { credentials: "same-origin" });
  if (res.status === 401) return null;
  const data = await res.json();
  if (!res.ok) throw new ApiError(res.status, "Couldn't check your session.");
  return data.data.user as User;
}

export async function signIn(email: string, password: string): Promise<void> {
  const { res, data } = await allauth("POST", "/auth/login", { email, password });
  if (!res.ok) throw new ApiError(res.status, firstError(data, "Couldn't sign you in."));
}

export async function signUp(email: string, password: string): Promise<void> {
  const { res, data } = await allauth("POST", "/auth/signup", { email, password });
  if (!res.ok) throw new ApiError(res.status, firstError(data, "Couldn't create your account."));
}

export async function signOut(): Promise<void> {
  await allauth("DELETE", "/auth/session");
}

export function useSession() {
  return useQuery({ queryKey: ["session"], queryFn: fetchSession, staleTime: 60_000 });
}

export function useRefreshSession() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries({ queryKey: ["session"] });
}
