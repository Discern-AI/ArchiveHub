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
