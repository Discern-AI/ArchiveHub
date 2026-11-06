import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { AppRoutes } from "../../app/routes";
import { installFetch, json } from "../../test/fakeServer";

const USER = { id: "u1", email: "alice@example.com", display: "alice" };
const NOT_SEARCHED = [
  { label: "Forum threads", reason: "Forums haven't opened yet." },
  { label: "People and services", reason: "The directory isn't open yet." },
];

function group(key: string, label: string, layer: "public" | "private", results: object[] = []) {
  return {
    key,
    label,
    layer,
    searched: `${label} fields`,
    results: results.map((r, i) => ({
      id: `${key}:${i}`,
      title: "",
      snippet: "",
      date: "",
      place: "",
      source: "",
      link: "",
      url: "",
      project_title: "",
      extra: {},
      ...r,
    })),
    count: results.length,
    more: false,
  };
}

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

const base = {
  "GET /_allauth/browser/v1/auth/session": () => json({ data: { user: USER } }),
  "GET /api/v1/projects": () => json([]),
  "GET /api/v1/chats": () => json([]),
};

describe("Search", () => {
  it("separates public and private results and says what was searched", async () => {
    const calls = installFetch({
      ...base,
      "GET /api/v1/search": () =>
        json({
          query: "Pigeons",
          words: ["pigeons"],
          groups: [
            group("records", "Checked records", "public", [
              { title: "Pigeons (Pub Wiki)", url: "https://pubwiki.co.uk/x", date: "1851–1940" },
            ]),
            group("places", "Places", "public"),
            group("interviews", "Interview transcripts", "private", [
              { title: "Gran, line 3", link: "/interviews/s1#line-3", snippet: "kept the Pigeons" },
            ]),
          ],
          not_searched: NOT_SEARCHED,
        }),
    });
    renderAt("/search");
    await userEvent.type(await screen.findByRole("searchbox"), "Pigeons{enter}");

    const records = await screen.findByRole("region", { name: "Checked records" });
    expect(within(records).getByRole("link", { name: /Pigeons \(Pub Wiki\)/ })).toHaveAttribute(
      "href",
      "https://pubwiki.co.uk/x",
    );
    const lines = screen.getByRole("region", { name: "Interview transcripts" });
    expect(within(lines).getByText("Private")).toBeInTheDocument();
    expect(within(lines).getByRole("link", { name: "Gran, line 3" })).toHaveAttribute(
      "href",
      "/interviews/s1#line-3",
    );
    const searched = screen.getByRole("region", { name: "What was searched" });
    expect(within(searched).getByText(/Places fields/)).toBeInTheDocument();
    expect(within(searched).getByText("Forum threads:")).toBeInTheDocument();
    expect(calls.some((c) => c.path === "/api/v1/search?q=Pigeons")).toBe(true);
  });

  it("never treats no results as proof", async () => {
    installFetch({
      ...base,
      "GET /api/v1/search": () =>
        json({
          query: "zzqx",
          words: ["zzqx"],
          groups: [group("records", "Checked records", "public")],
          not_searched: NOT_SEARCHED,
        }),
    });
    renderAt("/search?q=zzqx");
    expect(await screen.findByText("No matches in what we searched.")).toBeInTheDocument();
    expect(screen.getByText(/doesn't mean it isn't in the historical record/)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "What was searched" })).toBeInTheDocument();
  });
});
