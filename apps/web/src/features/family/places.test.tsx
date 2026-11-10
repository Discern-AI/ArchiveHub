import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../../app/routes";
import { installFetch, json } from "../../test/fakeServer";
import type { MapViewProps } from "../map/MapView";

vi.mock("../map/MapView", () => ({
  default: (p: MapViewProps) => (
    <div role="region" aria-label={p.label}>
      <button type="button" onClick={() => p.onPlace(51.4545, -0.9781)}>
        click the map
      </button>
    </div>
  ),
}));

const USER = { id: "u1", email: "alice@example.com", display: "alice" };
const PROJECT = {
  id: "p1",
  title: "Sample family",
  summary: "",
  visibility: "private",
  is_owner: true,
  created_at: "",
  updated_at: "",
};
const NEWBURY = {
  id: "l1",
  text: "Newbury, Berkshire, England",
  latitude: 51.3999,
  longitude: -1.3164,
  precision: "town",
  source: 'Old map names (OS six-inch, c.1900), label "NEWBURY"',
  method: "old-map-names",
  candidates: 1,
  status: "suggested",
  uses: 2,
};
const READING = {
  ...NEWBURY,
  id: "l2",
  text: "Reading, Berkshire, England",
  latitude: null,
  longitude: null,
  source: "",
  method: "",
  status: "not_found",
  uses: 1,
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

const base = {
  "GET /_allauth/browser/v1/auth/session": () => json({ data: { user: USER } }),
  "GET /api/v1/projects": () => json([PROJECT]),
  "GET /api/v1/projects/p1": () => json(PROJECT),
  "GET /api/v1/chats": () => json([]),
  "GET /api/v1/projects/p1/people": () =>
    json([{ id: "a", name: "Arthur Sample", living: false, birth: "ABT 1921", death: "1988" }]),
};

describe("Where to look next", () => {
  it("shows the records that could exist, with access, cost and unchecked leads marked", async () => {
    installFetch({
      ...base,
      "GET /api/v1/projects/p1/people/a": () =>
        json({
          id: "a",
          name: "Arthur Sample",
          living: false,
          birth: "ABT 1921",
          death: "1988",
          parents: [],
          partners: [],
          children: [],
          facts: [],
        }),
      "GET /api/v1/projects/p1/people/a/where-to-look": () =>
        json({
          note: "Where records would be if they exist; a search may find nothing.",
          steps: [
            {
              event: "birth",
              year: "1921",
              why: "Civil registration of the birth.",
              routes: [
                {
                  title: "GRO historical index and register image",
                  holder: "General Register Office",
                  what_it_gives: "The birth index with the mother's maiden name.",
                  access: "free",
                  cost: "Index free to search; Online View image about £3.",
                  url: "https://www.gro.gov.uk/gro/content/certificates/faq.asp",
                  source: "General Register Office FAQ",
                  checked: true,
                },
              ],
            },
            {
              event: "military service",
              year: "if they served",
              why: "Service records.",
              routes: [
                {
                  title: "Commonwealth War Graves Commission",
                  holder: "CWGC",
                  what_it_gives: "Burial or memorial.",
                  access: "free",
                  cost: "",
                  url: "https://www.cwgc.org/",
                  source: "CWGC",
                  checked: false,
                },
              ],
            },
          ],
        }),
    });
    renderAt("/projects/p1/people/a");
    await userEvent.click(await screen.findByRole("button", { name: "Where to look next" }));
    const panel = await screen.findByRole("region", { name: "Where to look next" });
    expect(
      await within(panel).findByRole("link", { name: /GRO historical index/ }),
    ).toHaveAttribute("href", "https://www.gro.gov.uk/gro/content/certificates/faq.asp");
    expect(within(panel).getByText(/about £3/)).toBeInTheDocument();
    expect(within(panel).getAllByText(/A lead: not yet checked/)).toHaveLength(1);
  });
});

describe("Family chart", () => {
  it("draws ancestors and children, hides living people's dates, and refocuses on click", async () => {
    installFetch({
      ...base,
      "GET /api/v1/projects/p1/family-places": () => json({ places: [], not_looked_up: 0 }),
      "GET /api/v1/projects/p1/tree-graph": () =>
        json({
          people: [
            { id: "w", name: "Walter Sample", sex: "M", living: false, born: 1890, died: null },
            { id: "a", name: "Arthur Sample", sex: "M", living: false, born: 1921, died: 1988 },
            { id: "e", name: "Edith Fictional", sex: "F", living: false, born: 1923, died: 1991 },
            { id: "c", name: "Alice Sample", sex: "F", living: true, born: null, died: null },
          ],
          links: [
            { from: "w", to: "a", kind: "parent" },
            { from: "a", to: "c", kind: "parent" },
            { from: "e", to: "c", kind: "parent" },
            { from: "a", to: "e", kind: "spouse" },
          ],
        }),
    });
    renderAt("/projects/p1/people");
    const chart = await screen.findByRole("region", { name: "Family chart" });
    // Starts on the best-connected person: Arthur, with his father above and daughter below.
    expect(
      within(chart).getByRole("group", { name: "Family chart for Arthur Sample" }),
    ).toBeInTheDocument();
    expect(
      within(chart).getByRole("button", { name: "Walter Sample, born 1890" }),
    ).toBeInTheDocument();
    expect(within(chart).getByRole("button", { name: "Alice Sample, Living" })).toBeInTheDocument();
    // Partners sit beside the person.
    expect(
      within(chart).getByRole("button", { name: "Edith Fictional, 1923–1991" }),
    ).toBeInTheDocument();
    await userEvent.click(within(chart).getByRole("button", { name: "Alice Sample, Living" }));
    expect(
      within(chart).getByRole("group", { name: "Family chart for Alice Sample" }),
    ).toBeInTheDocument();
    expect(
      within(chart).getByRole("button", { name: "Edith Fictional, 1923–1991" }),
    ).toBeInTheDocument();
    expect(within(chart).getByRole("link", { name: "Open Alice Sample's page" })).toHaveAttribute(
      "href",
      "/projects/p1/people/c",
    );
  });
});

describe("Evidence from saved finds", () => {
  it("shows a fact's evidence and backs it with a saved find", async () => {
    let attached = false;
    const calls = installFetch({
      ...base,
      "GET /api/v1/projects/p1/people/a": () =>
        json({
          id: "a",
          name: "Tom Sample",
          living: false,
          birth: "",
          death: "",
          parents: [],
          partners: [],
          children: [],
          facts: [
            {
              question: "occupation",
              disputed: false,
              answers: [
                {
                  id: "c1",
                  value: "Postman",
                  status: "documented",
                  method: "user",
                  note: "",
                  in_use: true,
                  evidence: attached
                    ? [
                        {
                          title: "The London Gazette, Issue 28538, Page 7207",
                          url: "https://www.thegazette.co.uk/London/issue/28538/page/7207",
                          what_it_says: "Named as a temporary postman.",
                        },
                      ]
                    : [],
                },
              ],
            },
          ],
        }),
      "GET /api/v1/projects/p1/basket": () =>
        json([
          {
            id: "b1",
            connector: "the-gazette",
            external_id: "London/issue/28538/page/7207",
            title: "The London Gazette, Issue 28538, Page 7207",
            url: "https://www.thegazette.co.uk/London/issue/28538/page/7207",
            storage: "reference_only",
            note: "",
            created_at: "",
          },
        ]),
      "POST /api/v1/projects/p1/claims/c1/evidence": () => {
        attached = true;
        return json({ added: 1 }, 201);
      },
    });
    renderAt("/projects/p1/people/a");
    await userEvent.click(
      await screen.findByRole("button", { name: "Back this with a saved find" }),
    );
    await userEvent.selectOptions(await screen.findByLabelText("Saved find"), "b1");
    await userEvent.type(
      screen.getByLabelText("What it says (optional)"),
      "Named as a temporary postman.",
    );
    await userEvent.click(screen.getByRole("button", { name: "Add as evidence" }));
    const evidence = await screen.findByRole("list", { name: "Evidence" });
    expect(within(evidence).getByRole("link", { name: /Issue 28538/ })).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({
      basket_item_id: "b1",
      note: "Named as a temporary postman.",
      stance: "supports",
    });
  });
});

describe("Tree health check", () => {
  it("lists things to check with links to the people, and changes nothing", async () => {
    const calls = installFetch({
      ...base,
      "GET /api/v1/projects/p1/family-places": () => json({ places: [], not_looked_up: 0 }),
      "GET /api/v1/projects/p1/tree-health": () =>
        json({
          people: 5,
          branches: 2,
          note: "These are things to check, not errors. Nothing has been changed or merged.",
          findings: [
            {
              kind: "duplicates",
              title: "Possibly the same person",
              detail: "Same name, born 1780 and 1781. Only a person can decide.",
              people: [
                { id: "a", name: "William Carter" },
                { id: "b", name: "William Carter" },
              ],
            },
          ],
        }),
    });
    renderAt("/projects/p1/people");
    await userEvent.click(await screen.findByRole("button", { name: "Check this tree" }));
    const panel = await screen.findByRole("region", { name: "Tree health check" });
    expect(
      await within(panel).findByText("Possibly the same person", { selector: "strong" }),
    ).toBeInTheDocument();
    expect(within(panel).getByText(/5 people in 2 groups/)).toBeInTheDocument();
    expect(within(panel).getAllByRole("link", { name: "William Carter" })[1]).toHaveAttribute(
      "href",
      "/projects/p1/people/b",
    );
    expect(calls.some((c) => c.method !== "GET")).toBe(false);
  });
});

describe("Places in a family tree", () => {
  it("finds locations, then lets the user confirm or reject each one", async () => {
    let located = false;
    let newbury = { ...NEWBURY };
    const calls = installFetch({
      ...base,
      "GET /api/v1/projects/p1/family-places": () =>
        json(
          located
            ? { places: [newbury, READING], not_looked_up: 0 }
            : { places: [], not_looked_up: 2 },
        ),
      "POST /api/v1/projects/p1/family-places/locate": () => {
        located = true;
        return json({ suggested: 1, not_found: 1 });
      },
      "PATCH /api/v1/family-places/l1": () => {
        newbury = { ...newbury, status: "confirmed" };
        return json(newbury);
      },
    });
    renderAt("/projects/p1/people");
    await userEvent.click(
      await screen.findByRole("button", { name: "Find locations for 2 places" }),
    );
    expect(await screen.findByText("Suggested 1 location; 1 not found.")).toBeInTheDocument();
    const panel = screen.getByRole("region", { name: "Places in this tree" });
    expect(within(panel).getByText(/Living people never appear/)).toBeInTheDocument();
    expect(within(panel).getByText(/2 events · Suggested, not yet checked/)).toBeInTheDocument();
    expect(within(panel).getByText(/label "NEWBURY"/)).toBeInTheDocument();
    expect(within(panel).getByText(/1 event · Not found/)).toBeInTheDocument();

    await userEvent.click(within(panel).getByRole("button", { name: "Right place" }));
    expect(await within(panel).findByText(/2 events · Checked/)).toBeInTheDocument();
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ status: "confirmed" });
    const placeIt = within(panel).getByRole("link", { name: "Place it on the map" });
    expect(placeIt.getAttribute("href")).toContain("/map?fix=l2");
  });

  it("places a missing place by clicking the map, then goes back", async () => {
    const calls = installFetch({
      ...base,
      "GET /api/v1/map/layers": () =>
        json({
          today: { title: "Today", style: "https://tiles.example/style", attribution: "" },
          historic: [],
        }),
      "GET /api/v1/map/places": () => json([]),
      "GET /api/v1/map/features": () =>
        json({ public: [], private: [], map_names: [], listed_buildings: [], notes: [] }),
      "PATCH /api/v1/family-places/l2": () =>
        json({ ...READING, latitude: 51.4545, longitude: -0.9781, status: "confirmed" }),
      "GET /api/v1/projects/p1/family-places": () =>
        json({ places: [NEWBURY, READING], not_looked_up: 0 }),
    });
    renderAt(
      `/map?fix=l2&label=${encodeURIComponent(READING.text)}&back=${encodeURIComponent("/projects/p1/people")}`,
    );
    expect(await screen.findByText("Place it on the map")).toBeInTheDocument();
    expect(screen.getByText("Reading, Berkshire, England")).toBeInTheDocument();
    await userEvent.click(await screen.findByText("click the map"));
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({
      latitude: 51.4545,
      longitude: -0.9781,
      precision: "town",
    });
    expect(await screen.findByRole("region", { name: "Places in this tree" })).toBeInTheDocument();
  });
});
