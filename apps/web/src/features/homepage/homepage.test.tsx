import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { AppRoutes } from "../../app/routes";
import { previewHtml, type Post } from "../../lib/homepage";
import { installFetch, json } from "../../test/fakeServer";

const USER = { id: "u1", email: "alice@example.com", display: "alice" };
const base = {
  "GET /_allauth/browser/v1/auth/session": () => json({ data: { user: USER } }),
  "GET /api/v1/projects": () => json([]),
  "GET /api/v1/chats": () => json([]),
};
const HOME = {
  slug: "janes-history",
  title: "Jane's history",
  tagline: "",
  about: "",
  live: true,
  url: "/h/janes-history/",
};
const POST: Post = {
  id: "post1",
  title: "The mill fire",
  slug: "the-mill-fire",
  summary: "",
  status: "draft",
  source: "chat",
  published_at: null,
  original_url: "",
  first_published: null,
  url: "/h/janes-history/the-mill-fire/",
  updated_at: "",
  body: "It burned in 1887. Mary Smith saw it.",
  images: [],
};

function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Homepage", () => {
  it("sets up a homepage", async () => {
    const calls = installFetch({
      ...base,
      "GET /api/v1/home": () => json(null),
      "PUT /api/v1/home": (_u, init) => json({ ...JSON.parse(String(init.body)), url: "/h/x/" }),
      "GET /api/v1/home/posts": () => json([]),
    });
    renderAt("/homepage");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Title"), "Jane's history");
    await user.type(screen.getByLabelText("Web address"), "janes-history");
    await user.click(screen.getByRole("button", { name: "Create homepage" }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === "PUT")?.body).toMatchObject({
        slug: "janes-history",
        title: "Jane's history",
        live: false,
      }),
    );
    expect(await screen.findByRole("heading", { name: "Posts" })).toBeTruthy();
  }, 10000);

  it("lists posts with where they came from", async () => {
    installFetch({
      ...base,
      "GET /api/v1/home": () => json(HOME),
      "GET /api/v1/home/posts": () =>
        json([
          POST,
          { ...POST, id: "p2", title: "Old one", source: "wordpress", status: "published" },
        ]),
    });
    renderAt("/homepage");
    expect(await screen.findByRole("link", { name: "The mill fire" })).toBeTruthy();
    expect(screen.getByText("Drafted in chat")).toBeTruthy();
    expect(screen.getByText("Imported from WordPress")).toBeTruthy();
    expect(screen.getByRole("link", { name: "View your homepage" })).toBeTruthy();
  });

  it("needs warnings confirmed before publishing", async () => {
    const calls = installFetch({
      ...base,
      "GET /api/v1/home/posts/post1": () => json(POST),
      "POST /api/v1/home/posts/post1/check": () =>
        json({
          ok: true,
          blockers: [],
          warnings: [{ kind: "living", text: "Mary Smith may be living." }],
        }),
      "POST /api/v1/home/posts/post1/publish": () =>
        json({ ...POST, status: "published", published_at: "2026-11-11T10:00:00Z" }),
      "GET /api/v1/home/posts/post1/social": () =>
        json({
          link: "http://x/h/janes-history/the-mill-fire/",
          note: "Copy and paste these yourself.",
          posts: [{ for: "Short posts", text: "The mill fire\nhttp://x", limit: 280 }],
        }),
    });
    renderAt("/homepage/posts/post1");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Check before publishing" }));
    expect(await screen.findByText("Mary Smith may be living.")).toBeTruthy();
    const publish = screen.getByRole("button", { name: "Approve and publish" });
    expect((publish as HTMLButtonElement).disabled).toBe(true);
    await user.click(screen.getByLabelText(/checked these/));
    await user.click(publish);
    await waitFor(() =>
      expect(calls.find((c) => c.path.endsWith("/publish"))?.body).toEqual({
        confirm_warnings: true,
      }),
    );
    expect(await screen.findByRole("button", { name: "Take it down" })).toBeTruthy();
    expect(await screen.findByLabelText("Short posts")).toBeTruthy();
  }, 10000);

  it("shows blockers and offers no publish button", async () => {
    installFetch({
      ...base,
      "GET /api/v1/home/posts/post1": () => json(POST),
      "POST /api/v1/home/posts/post1/check": () =>
        json({
          ok: false,
          blockers: [{ kind: "rights", text: "Say whose picture “mill.jpg” is." }],
          warnings: [],
        }),
    });
    renderAt("/homepage/posts/post1");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Check before publishing" }));
    expect(await screen.findByText("Say whose picture “mill.jpg” is.")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Approve and publish" })).toBeNull();
  });
});

describe("previewHtml", () => {
  it("escapes everything and keeps only the subset", () => {
    const html = previewHtml(
      "## Hi <script>x()</script>\n\n**b** [ok](https://e.org) [no](javascript:x)",
      [],
    );
    expect(html).not.toContain("<script>");
    expect(html).toContain("<h2>Hi &lt;script&gt;");
    expect(html).toContain('<a href="https://e.org"');
    expect(html).not.toContain('href="javascript');
    expect(html).toContain("<strong>b</strong>");
  });

  it("marks pictures that aren't attached", () => {
    expect(previewHtml("![x](image:00000000-0000-0000-0000-000000000000)", [])).toContain(
      "isn't attached",
    );
  });
});
