import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../../app/routes";
import { groupPins, layerForYear, type HistoricLayer, type MapFeature } from "../../lib/map";
import { installFetch, json } from "../../test/fakeServer";
import type { MapViewProps } from "./MapView";

// jsdom has no WebGL: stand in for the map with its pins as plain buttons.
vi.mock("./MapView", () => ({
  default: (p: MapViewProps) => (
    <div role="region" aria-label={p.label} data-historic={p.historic?.id ?? "none"}>
      {p.features.map((f) => (
        <button key={f.id} type="button" data-layer={f.layer} onClick={() => p.onSelect(f.id)}>
          pin {f.title}
        </button>
      ))}
      <span>{p.names.length} map names</span>
      <button type="button" onClick={() => p.onPlace(51.4006, -1.3229)}>
        click the map
      </button>
    </div>
  ),
}));

const USER = { id: "u1", email: "alice@example.com", display: "alice" };
const PROJECT = {
  id: "p1",
  title: "Gran's Newbury",
  summary: "",
  visibility: "private",
  is_owner: true,
  created_at: "",
  updated_at: "",
};
const SIX_INCH: HistoricLayer = {
  id: "os-six-inch-1888",
  title: "OS six-inch, 1888–1913",
  years: [1888, 1913],
  min_zoom: 10,
  attribution: "NLS",
  available: false,
  unavailable_reason: "Historic maps aren't set up on this server yet.",
};

function feature(over: Partial<MapFeature>): MapFeature {
  return {
    id: "record:pigeons",
    layer: "public",
    kind: "record",
    title: "Pigeons, 5 Cheap Street, Newbury (Pub Wiki)",
    summary: "Licensee list.",
    date_display: "1851–1940",
    year_from: 1851,
    year_to: 1940,
    date_role: "record_covers",
    latitude: 51.4005,
    longitude: -1.3231,
    precision: "street",
    place: "Cheap Street, Newbury",
    source: "Pub Wiki",
    url: "https://pubwiki.co.uk/x",
    link: "",
    project_id: null,
    project_title: "",
    extra: {},
    ...over,
  };
}

const MEMORY = feature({
  id: "item:m1",
  layer: "private",
  kind: "memory",
  title: "Gran's first job",
  summary: "She served at the Pigeons.",
  date_display: "1952",
  year_from: 1952,
  year_to: 1952,
  date_role: "event",
  precision: "inferred",
  source: "Your project",
  url: "",
  project_id: "p1",
  project_title: "Gran's Newbury",
  extra: { item_id: "m1" },
});

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

function routes(extra: Record<string, (url: URL) => Response> = {}) {
  return {
    "GET /_allauth/browser/v1/auth/session": () => json({ data: { user: USER } }),
    "GET /api/v1/projects": () => json([PROJECT]),
    "GET /api/v1/chats": () => json([]),
    "GET /api/v1/map/layers": () =>
      json({
        today: {
          title: "Today",
          style: "https://tiles.openfreemap.org/styles/liberty",
          attribution: "OSM",
        },
        historic: [SIX_INCH],
      }),
    "GET /api/v1/map/places": () =>
      json([
        {
          id: "pl1",
          key: "cheap-street",
          name: "Cheap Street, Newbury",
          kind: "street",
          latitude: 51.4005,
          longitude: -1.3231,
          precision: "street",
          geocode_source: "Old map names",
          note: "",
        },
      ]),
    ...extra,
  };
}

describe("Time map", () => {
  it("keeps public records and private items visibly apart", async () => {
    const calls = installFetch(
      routes({
        "GET /api/v1/map/features": () =>
          json({
            public: [feature({})],
            private: [MEMORY],
            map_names: [feature({ id: "name:1" })],
            notes: [],
          }),
      }),
    );
    renderAt("/map");

    const publicList = await screen.findByRole("region", { name: "Public records" });
    const privateList = screen.getByRole("region", { name: "Private: your projects" });
    expect(await within(publicList).findByText(/Pigeons, 5 Cheap Street/)).toBeInTheDocument();
    expect(within(publicList).queryByText("Gran's first job")).not.toBeInTheDocument();
    expect(within(privateList).getByText("Gran's first job")).toBeInTheDocument();
    expect(within(privateList).getByText(/Only people in each project/)).toBeInTheDocument();
    // Each date says what kind of date it is.
    expect(within(publicList).getByText("Record covers")).toBeInTheDocument();
    expect(within(privateList).getByText("Happened")).toBeInTheDocument();

    const map = await screen.findByRole("region", { name: "Map of 1900" });
    expect(within(map).getByText("pin Gran's first job")).toHaveAttribute("data-layer", "private");
    expect(within(map).getByText("1 map names")).toBeInTheDocument();
    // The six-inch map covers 1900 but isn't configured: say so rather than hide it.
    expect(screen.getByText(/aren't set up on this server yet/)).toBeInTheDocument();
    const query = calls.find((c) => c.path.startsWith("/api/v1/map/features"))!.path;
    expect(query).toContain("year_from=1890");
    expect(query).toContain("year_to=1910");
  });

  it("opens an item and shows its privacy, date and location precision", async () => {
    installFetch(
      routes({
        "GET /api/v1/map/features": () =>
          json({ public: [], private: [MEMORY], map_names: [], notes: [] }),
      }),
    );
    renderAt("/map");
    await userEvent.click(await screen.findByText("pin Gran's first job"));
    expect(screen.getByText("Private: Gran's Newbury")).toBeInTheDocument();
    expect(screen.getByText(/Approximate location/)).toBeInTheDocument();
    expect(screen.getByText("She served at the Pigeons.")).toBeInTheDocument();
  });

  it("moves through the years", async () => {
    const calls = installFetch(
      routes({
        "GET /api/v1/map/features": () =>
          json({ public: [], private: [], map_names: [], notes: [] }),
      }),
    );
    renderAt("/map?year=1960");
    await screen.findByRole("region", { name: "Map of 1960" });
    expect(screen.getByText(/No old map covers 1960|aren't set up/)).toBeInTheDocument();
    expect(
      calls.some((c) => c.path.includes("year_from=1950") && c.path.includes("year_to=1970")),
    ).toBe(true);
  });

  it("shows today alongside the chosen year", async () => {
    installFetch(
      routes({
        "GET /api/v1/map/features": () =>
          json({ public: [], private: [], map_names: [], notes: [] }),
      }),
    );
    renderAt("/map");
    await screen.findByRole("region", { name: "Map of 1900" });
    await userEvent.click(screen.getByLabelText("Today alongside"));
    expect(await screen.findByRole("region", { name: "Map of today" })).toHaveAttribute(
      "data-historic",
      "none",
    );
  });

  it("adds a private memory where the user clicks", async () => {
    let added = false;
    const calls = installFetch(
      routes({
        "GET /api/v1/map/features": () =>
          json({ public: [], private: added ? [MEMORY] : [], map_names: [], notes: [] }),
        "POST /api/v1/projects/p1/map-items": () => {
          added = true;
          return json(MEMORY, 201);
        },
      }),
    );
    renderAt("/map");
    await userEvent.click(await screen.findByRole("button", { name: "Add a memory or photo" }));
    expect(screen.getByText(/Private to Gran's Newbury/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Title"), "Gran's first job");
    await userEvent.type(
      screen.getByLabelText("The memory, in your own words"),
      "She served at the Pigeons.",
    );
    await userEvent.type(screen.getByLabelText("From year"), "1952");
    await userEvent.click(screen.getByRole("button", { name: "Add to the map" }));
    expect(screen.getByText("Click the map where it belongs first.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);

    await userEvent.click(screen.getAllByText("click the map")[0]);
    expect(screen.getByText(/Location chosen/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Add to the map" }));
    const post = calls.find((c) => c.method === "POST")!;
    expect(post.body).toMatchObject({
      kind: "memory",
      title: "Gran's first job",
      latitude: 51.4006,
      year_from: 1952,
      year_to: 1952,
      date_role: "event",
    });
    expect(await screen.findByText("Private: Gran's Newbury")).toBeInTheDocument();
  });
});

describe("layerForYear", () => {
  const layers: HistoricLayer[] = [
    SIX_INCH,
    { ...SIX_INCH, id: "small", years: [1919, 1947], min_zoom: 6 },
    { ...SIX_INCH, id: "25k", years: [1937, 1961], min_zoom: 10 },
  ];
  it("picks the most detailed map covering the year", () => {
    expect(layerForYear(layers, 1900)?.id).toBe("os-six-inch-1888");
    expect(layerForYear(layers, 1940)?.id).toBe("25k");
    expect(layerForYear(layers, 1925)?.id).toBe("small");
    expect(layerForYear(layers, 1800)).toBeNull();
  });
});

describe("groupPins", () => {
  it("shares one pin per spot and layer, with private pins drawn last", () => {
    const a = feature({ id: "a" });
    const b = feature({ id: "b" });
    const c = feature({ id: "c", longitude: -1.3 });
    const p = feature({ id: "p", layer: "private" });
    const groups = groupPins([p, a, b, c]);
    expect(groups.map((g) => g.map((f) => f.id))).toEqual([["a", "b"], ["c"], ["p"]]);
  });
});
