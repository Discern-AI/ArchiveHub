/** A tiny in-memory stand-in for the API, installed as `fetch`. */
import { vi } from "vitest";

type Handler = (url: URL, init: RequestInit) => Response | Promise<Response>;

export function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function sseResponse(events: [string, unknown][]) {
  const body = events.map(([e, d]) => `event: ${e}\ndata: ${JSON.stringify(d)}\n\n`).join("");
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      // Deliver in small chunks to exercise the incremental parser.
      for (let i = 0; i < body.length; i += 17)
        controller.enqueue(encoder.encode(body.slice(i, i + 17)));
      controller.close();
    },
  });
  return new Response(stream, { headers: { "Content-Type": "text/event-stream" } });
}

export function installFetch(routes: Record<string, Handler>) {
  document.cookie = "csrftoken=test-token";
  const calls: { method: string; path: string; body?: unknown; headers: Headers }[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = new URL(String(input), "http://localhost");
    const method = (init.method ?? "GET").toUpperCase();
    calls.push({
      method,
      path: url.pathname + url.search,
      body: init.body ? JSON.parse(String(init.body)) : undefined,
      headers: new Headers(init.headers),
    });
    const handler = routes[`${method} ${url.pathname}`];
    if (!handler) return json({ detail: "Not Found" }, 404);
    return handler(url, init);
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}
