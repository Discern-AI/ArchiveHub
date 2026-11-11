import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { AppRoutes } from "../../app/routes";
import { installFetch, json } from "../../test/fakeServer";

const USER = { id: "u1", email: "alice@example.com", display: "alice" };
const PROJECT = {
  id: "p1",
  title: "Samples",
  summary: "",
  visibility: "private",
  is_owner: true,
  created_at: "",
  updated_at: "",
};
const ARTHUR = {
  id: "a",
  name: "Arthur Sample",
  living: false,
  birth: "ABT 1890",
  death: "1960",
  parents: [],
  partners: [],
  children: [],
  facts: [],
};
const STORY = {
  person: { id: "a", name: "Arthur Sample" },
  private: false,
  at_a_glance: {
    born: "about 1890, Newbury",
    died: "14 March 1960",
    occupation: "Publican",
    partners: 1,
    children: 2,
  },
  chapters: [
    {
      key: "early",
      title: "Early life",
      events: [
        {
          chapter: "early",
          year: 1890,
          kind: "birth",
          sentence: "Arthur was born about 1890 in Newbury.",
          status: "documented",
          claim_ids: ["c1"],
          sources: [
            {
              title: "t.ged (GEDCOM @I1@)",
              url: "",
              source: "Your Archive",
              what_it_says: "From the imported family tree file",
            },
          ],
          people: [],
        },
      ],
    },
    {
      key: "family",
      title: "Marriage and family",
      events: [
        {
          chapter: "family",
          year: 1914,
          kind: "marriage",
          sentence: "Married Edith Fictional on 4 June 1914 at Newbury.",
          status: "remembered",
          claim_ids: [],
          sources: [],
          people: [{ id: "e", name: "Edith Fictional" }],
        },
      ],
    },
  ],
  context: [
    {
      title: "First World War",
      date_text: "1914–18",
      area: "",
      age: "about 24 to 28",
      source_title: "National Army Museum",
      source_url: "https://www.nam.ac.uk/explore/first-world-war",
    },
  ],
  context_note: "What was happening while they lived, for context. It doesn't say they took part.",
  gaps: ["No addresses recorded (censuses list where people lived)."],
};
const PHOTO = {
  id: "g1",
  file_id: "f1",
  file_name: "wedding.png",
  has_preview: false,
  caption: "Their wedding",
  date_text: "June 1914",
  year: 1914,
  decade: "1910s",
  place_text: "Newbury",
  relation: "shows",
  people: [
    { id: "a", name: "Arthur Sample", relation: "shows" },
    { id: "e", name: "Edith Fictional", relation: "shows" },
  ],
};

function serve(
  extra: Record<string, (u: URL, i: RequestInit) => Response | Promise<Response>> = {},
) {
  return installFetch({
    "GET /_allauth/browser/v1/auth/session": () => json({ data: { user: USER } }),
    "GET /api/v1/projects": () => json([PROJECT]),
    "GET /api/v1/projects/p1": () => json(PROJECT),
    "GET /api/v1/chats": () => json([]),
    "GET /api/v1/projects/p1/people/a": () => json(ARTHUR),
    "GET /api/v1/projects/p1/people/a/life-story": () => json(STORY),
    "GET /api/v1/projects/p1/people/a/gallery": () =>
      json([
        PHOTO,
        {
          ...PHOTO,
          id: "g2",
          file_id: "f2",
          file_name: "street.png",
          caption: "",
          relation: "context",
          year: null,
          decade: "Date not known",
          people: [{ id: "a", name: "Arthur Sample", relation: "context" }],
        },
      ]),
    ...extra,
  });
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

describe("Life Story", () => {
  it("opens on the life story, with sources, context kept apart and gaps", async () => {
    serve();
    renderAt("/projects/p1/people/a");
    expect(await screen.findByRole("tab", { name: "Life story" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    const glance = await screen.findByRole("region", { name: "At a glance" });
    expect(glance).toHaveTextContent("about 1890, Newbury");
    expect(glance).toHaveTextContent("1 partner, 2 children");
    const early = screen.getByRole("region", { name: "Early life" });
    expect(early).toHaveTextContent("Arthur was born about 1890 in Newbury.");
    await userEvent.click(within(early).getByRole("button", { name: "Sources (1)" }));
    expect(within(early).getByText("t.ged (GEDCOM @I1@)")).toBeInTheDocument();
    const family = screen.getByRole("region", { name: "Marriage and family" });
    expect(within(family).getByText("Remembered")).toBeInTheDocument();
    expect(within(family).getByRole("link", { name: "Edith Fictional" })).toBeInTheDocument();
    const world = screen.getByRole("region", { name: "The world around them" });
    expect(world).toHaveTextContent("First World War, 1914–18: they were about 24 to 28.");
    expect(world).toHaveTextContent("doesn't say they took part");
    expect(screen.getByRole("region", { name: "What isn't known yet" })).toHaveTextContent(
      "No addresses recorded",
    );
  });

  it("says a living person's story isn't told", async () => {
    serve({
      "GET /api/v1/projects/p1/people/a": () => json({ ...ARTHUR, living: true }),
      "GET /api/v1/projects/p1/people/a/life-story": () =>
        json({
          person: { id: "a", name: "Arthur Sample" },
          private: true,
          note: "Living people's lives aren't told here: their details are private.",
        }),
    });
    renderAt("/projects/p1/people/a?view=story");
    expect(await screen.findByText(/Living people's lives aren't told here/)).toBeInTheDocument();
  });
});

describe("Galleries", () => {
  it("groups by decade, says what each picture is, and reorders", async () => {
    const calls = serve({
      "PUT /api/v1/projects/p1/people/a/gallery/order": () => json([]),
    });
    renderAt("/projects/p1/people/a?view=gallery");
    const decade = await screen.findByRole("region", { name: "1910s" });
    expect(decade).toHaveTextContent("Their wedding");
    expect(decade).toHaveTextContent("Shows them");
    expect(within(decade).getByRole("link", { name: "Edith Fictional" })).toBeInTheDocument();
    const unknown = screen.getByRole("region", { name: "Date not known" });
    expect(unknown).toHaveTextContent("Their world, not them");
    await userEvent.click(screen.getByRole("button", { name: "Move street.png earlier" }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === "PUT")?.body).toEqual({ item_ids: ["g2", "g1"] }),
    );
  });

  it("sorts photos from the Archive by accepting a suggestion", async () => {
    let sorted = false;
    const calls = serve({
      "GET /api/v1/projects/p1/gallery": () => json(sorted ? [PHOTO] : []),
      "GET /api/v1/projects/p1/photo-suggestions": () =>
        json(
          sorted
            ? []
            : [
                {
                  file_id: "f1",
                  file_name: "Arthur Sample 1945.png",
                  folder: "Sample photos",
                  has_preview: false,
                  year_hint: 1945,
                  year_from: "the file name",
                  suggestions: [
                    {
                      id: "a",
                      name: "Arthur Sample",
                      score: 3,
                      reason: "the name says Arthur Sample; they were alive in 1945",
                    },
                  ],
                },
              ],
        ),
      "POST /api/v1/projects/p1/gallery": () => {
        sorted = true;
        return json(PHOTO, 201);
      },
    });
    renderAt("/projects/p1/gallery");
    const sort = await screen.findByRole("region", { name: "Sort your photos" });
    const suggested = await within(sort).findByRole("list", {
      name: "Suggested for Arthur Sample 1945.png",
    });
    expect(suggested).toHaveTextContent("they were alive in 1945");
    await userEvent.click(within(suggested).getByRole("button", { name: /Arthur Sample/ }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === "POST")?.body).toEqual({
        file_id: "f1",
        date_text: "1945",
        tags: [{ person_id: "a", relation: "shows" }],
      }),
    );
    expect(
      await screen.findByText("Every picture is sorted.", { exact: false }),
    ).toBeInTheDocument();
  });
});
