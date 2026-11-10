import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { AppRoutes } from "../../app/routes";
import {
  aliveCounts,
  directLine,
  generations,
  statusAt,
  whyUncertain,
  type LifeEnd,
  type LifePerson,
  type LifePlace,
} from "../../lib/lifeline";
import { installFetch, json } from "../../test/fakeServer";
import { lifelineFeatures } from "./LifelineMap";

// The real map needs WebGL; this stand-in shows the year it was given and counts mounts.
let mapMounts = 0;
vi.mock("./LifelineMap", async (importOriginal) => {
  const real = await importOriginal<typeof import("./LifelineMap")>();
  const { useEffect } = await import("react");
  function FakeMap(p: { year: number }) {
    useEffect(() => {
      mapMounts++;
    }, []);
    return <div data-testid="map">map for {p.year}</div>;
  }
  return { ...real, default: FakeMap };
});

// jsdom has no layout, so give the scrolling list a size for the virtualiser.
const sizes = { offsetHeight: 520, offsetWidth: 1000, clientHeight: 520, clientWidth: 1000 };
const saved: Record<string, PropertyDescriptor | undefined> = {};
beforeAll(() => {
  for (const [k, v] of Object.entries(sizes)) {
    saved[k] = Object.getOwnPropertyDescriptor(HTMLElement.prototype, k);
    Object.defineProperty(HTMLElement.prototype, k, { configurable: true, get: () => v });
  }
});
afterAll(() => {
  for (const [k, d] of Object.entries(saved))
    if (d) Object.defineProperty(HTMLElement.prototype, k, d);
});

const end = (
  earliest: number | null,
  latest: number | null,
  certainty: LifeEnd["certainty"] = "exact",
): LifeEnd => ({ earliest, latest, certainty, text: "", from: "birth" });

const place = (
  kind: LifePlace["kind"],
  year: number,
  name: string,
  lat: number | null = 51,
  lng: number | null = -1,
): LifePlace => ({
  kind,
  place: name,
  latitude: lat,
  longitude: lng,
  located: "checked",
  year_from: year,
  year_to: year,
  date_text: String(year),
});

function person(id: string, name: string, extra: Partial<LifePerson> = {}): LifePerson {
  return {
    id,
    name,
    surname: name.split(" ").at(-1) ?? "",
    sex: "",
    living: false,
    parents: [],
    partners: [],
    start: null,
    end: null,
    places: [],
    ...extra,
  };
}

describe("Lifeline rules", () => {
  const exact = person("e", "Exact Person", { start: end(1900, 1900), end: end(1980, 1980) });
  const about = person("a", "About Person", {
    start: end(1845, 1855, "about"),
    end: end(1920, 1920),
  });
  const noDeath = person("n", "No Death", { start: end(1880, 1880) });

  it("says who was alive, possibly alive or just outside a year", () => {
    expect(statusAt(exact, 1950)).toBe("alive");
    expect(statusAt(exact, 1899)).toBe("soon-born");
    expect(statusAt(exact, 1983)).toBe("recently-died");
    expect(statusAt(exact, 2000)).toBe("not-alive");
    expect(statusAt(about, 1850)).toBe("uncertain");
    expect(whyUncertain(about, 1850)).toBe("born about 1850");
    expect(statusAt(about, 1860)).toBe("alive");
    expect(statusAt(noDeath, 1950)).toBe("uncertain");
    expect(whyUncertain(noDeath, 1950)).toBe("death not recorded");
    expect(statusAt(person("l", "Living One", { living: true }), 1985)).toBe("private");
    expect(statusAt(person("x", "No Dates"), 1900)).toBe("not-alive");
  });

  it("treats a recorded residence as proof of life that year", () => {
    const p = person("r", "Resident", {
      start: end(1880, 1880),
      places: [place("residence", 1921, "Leeds")],
    });
    expect(statusAt(p, 1915)).toBe("alive");
    expect(statusAt(p, 1930)).toBe("uncertain");
  });

  it("counts the living and the possibly living each year", () => {
    const counts = aliveCounts([exact, about, noDeath], 1850, 1950);
    const at = (y: number) => counts.find((c) => c.year === y)!;
    // No recorded death: only possibly alive, even when young.
    expect(at(1910)).toEqual({ year: 1910, alive: 2, uncertain: 1 });
    expect(at(1950)).toEqual({ year: 1950, alive: 1, uncertain: 1 });
  });

  it("works out generations and a direct line", () => {
    const g = person("g", "Grand", {});
    const p = person("p", "Parent", { parents: ["g"] });
    const c = person("c", "Child", { parents: ["p"] });
    const cousin = person("u", "Cousin", { parents: ["g"] });
    const gens = generations([g, p, c, cousin]);
    expect([gens.get("g"), gens.get("p"), gens.get("c"), gens.get("u")]).toEqual([1, 2, 3, 2]);
    expect([...directLine([g, p, c, cousin], "p")].sort()).toEqual(["c", "g", "p"]);
  });

  it("puts each person at their last recorded place, with moves as dashed lines", () => {
    const mover = person("m", "Mover", {
      places: [
        place("birth", 1850, "Hungerford", 51.41, -1.51),
        place("residence", 1871, "Reading", 51.45, -0.97),
        place("residence", 1881, "Unplaced", null, null),
        place("burial", 1920, "London", 51.5, -0.12),
      ],
    });
    const in1875 = lifelineFeatures([mover], 1875);
    expect(in1875.points.features[0].properties.place).toBe("Reading");
    expect(in1875.lines.features[0].geometry.coordinates).toHaveLength(2);
    const in1860 = lifelineFeatures([mover], 1860);
    expect(in1860.lines.features).toHaveLength(0);
    expect(lifelineFeatures([mover], 1840).points.features).toHaveLength(0);
  });
});

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
const OVERLAYS = [
  {
    id: "o1",
    kind: "war",
    title: "Second World War",
    year_from: 1939,
    year_to: 1945,
    date_text: "1939–45",
    area: "",
    note: "",
    source_title: "National Army Museum: Second World War",
    source_url: "https://www.nam.ac.uk/explore/second-world-war",
    builtin: true,
  },
  {
    id: "o2",
    kind: "records",
    title: "Census",
    year_from: 1921,
    year_to: null,
    date_text: "19 June 1921",
    area: "England and Wales",
    note: "",
    source_title: "The National Archives: Census records",
    source_url: "https://www.nationalarchives.gov.uk/",
    builtin: true,
  },
];

function family(count: number): LifePerson[] {
  const out: LifePerson[] = [
    person("arthur", "Arthur Sample", {
      start: end(1916, 1926, "about"),
      end: end(1988, 1988),
      places: [place("birth", 1921, "Newbury")],
    }),
    person("edith", "Edith Fictional", { start: end(1923, 1923), end: end(1990, 1992, "range") }),
    person("walter", "Walter Sample", { start: end(1890, 1890) }),
    person("alice", "Alice Sample", { living: true, parents: ["arthur", "edith"] }),
  ];
  for (let i = out.length; i < count; i++)
    out.push(
      person(`x${i}`, `Person ${i} Filler`, {
        start: end(1800 + (i % 150), 1800 + (i % 150)),
        end: end(1860 + (i % 150), 1860 + (i % 150)),
      }),
    );
  return out;
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

function serve(people: LifePerson[]) {
  return installFetch({
    "GET /_allauth/browser/v1/auth/session": () => json({ data: { user: USER } }),
    "GET /api/v1/projects": () => json([PROJECT]),
    "GET /api/v1/projects/p1": () => json(PROJECT),
    "GET /api/v1/chats": () => json([]),
    "GET /api/v1/map/layers": () =>
      json({
        today: { title: "Today", style: "https://example.test/style.json", attribution: "" },
        historic: [],
      }),
    "GET /api/v1/projects/p1/lifeline": () =>
      json({
        people,
        overlays: OVERLAYS,
        kinds: ["war", "records", "law", "calendar", "family", "custom"],
        living_private: people.filter((p) => p.living).length,
        this_year: 2026,
        about_years: 5,
      }),
    "PUT /api/v1/projects/p1/lifeline/preset": async (_u, init) =>
      json(JSON.parse(String(init.body))),
    "POST /api/v1/projects/p1/lifeline/markers": () =>
      json({ ...OVERLAYS[1], id: "m1", kind: "custom", title: "I was born", builtin: false }, 201),
  });
}

async function setYear(y: number) {
  const box = await screen.findByLabelText("Year");
  fireEvent.change(box, { target: { value: String(y) } });
}

describe("Lifeline page", () => {
  it("lists exactly who was alive in 1985, with uncertain cases labelled", async () => {
    serve(family(4));
    renderAt("/projects/p1/lifeline");
    await screen.findByRole("region", { name: /Alive in/ });
    await setYear(1985);
    const panel = screen.getByRole("region", { name: "Alive in 1985" });
    const alive = within(panel).getByRole("list", { name: "Alive" });
    expect(
      within(alive)
        .getAllByRole("link")
        .map((a) => a.textContent),
    ).toEqual(["Arthur Sample", "Edith Fictional"]);
    // Walter (born 1890) has no recorded death, so he's only possibly alive, and says why.
    const maybe = within(panel).getByRole("list", { name: "Possibly alive" });
    expect(maybe).toHaveTextContent("Walter Sample · death not recorded");
    expect(within(alive).queryByText("Walter Sample")).not.toBeInTheDocument();
    expect(panel).toHaveTextContent("1 living relative isn't counted");
    // Ten years on he'd be past the longest life we assume.
    await setYear(2000);
    expect(screen.getByRole("region", { name: "Alive in 2000" })).not.toHaveTextContent("Walter");
  });

  it("fades an estimated birth and keeps living people's dates private", async () => {
    serve(family(4));
    renderAt("/projects/p1/lifeline");
    const arthur = await screen.findByTestId("row-arthur");
    expect(arthur).toHaveAttribute("data-start", "faded");
    expect(arthur.querySelector('[data-part="fade-in"]')).not.toBeNull();
    expect(screen.getByTestId("row-edith")).toHaveAttribute("data-start", "sharp");
    expect(
      within(screen.getByTestId("row-alice")).getByText("Living: dates private"),
    ).toBeInTheDocument();
  });

  it("switching wars off removes only the war overlays, and is remembered", async () => {
    const calls = serve(family(4));
    renderAt("/projects/p1/lifeline");
    await screen.findByTestId("row-arthur");
    const lifeline = screen.getByRole("region", { name: "Lifeline" });
    expect(lifeline.querySelectorAll('[data-overlay="war"]')).toHaveLength(1);
    expect(lifeline.querySelectorAll('[data-overlay="records"]')).toHaveLength(1);
    await userEvent.click(screen.getByRole("checkbox", { name: "Wars" }));
    expect(lifeline.querySelectorAll('[data-overlay="war"]')).toHaveLength(0);
    expect(lifeline.querySelectorAll('[data-overlay="records"]')).toHaveLength(1);
    await waitFor(() =>
      expect(calls.find((c) => c.method === "PUT")?.body).toEqual({
        kinds: ["records", "law", "calendar", "family", "custom"],
      }),
    );
  });

  it("moves the map with the year without reloading it", async () => {
    mapMounts = 0;
    serve(family(4));
    renderAt("/projects/p1/lifeline");
    expect(await screen.findByTestId("map")).toHaveTextContent("map for 1900");
    await setYear(1950);
    expect(screen.getByTestId("map")).toHaveTextContent("map for 1950");
    expect(mapMounts).toBe(1);
  });

  it("draws only the visible rows of a 200-person tree", async () => {
    serve(family(200));
    renderAt("/projects/p1/lifeline");
    await screen.findByTestId("row-x150"); // the earliest born, at the top
    // Arthur, born about 1921, is far down the list, so he isn't drawn yet.
    expect(screen.queryByTestId("row-arthur")).not.toBeInTheDocument();
    const rows = document.querySelectorAll('[data-testid^="row-"]');
    expect(rows.length).toBeGreaterThan(5);
    expect(rows.length).toBeLessThan(60);
  });

  it("adds a marker of your own", async () => {
    const calls = serve(family(4));
    renderAt("/projects/p1/lifeline");
    await screen.findByTestId("row-arthur");
    await userEvent.click(screen.getByText("Add your own marker"));
    await userEvent.type(screen.getByLabelText("What happened"), "I was born");
    await userEvent.type(screen.getByLabelText("Marker year"), "1985");
    await userEvent.click(screen.getByRole("button", { name: "Add marker" }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === "POST")?.body).toEqual({
        title: "I was born",
        year_from: 1985,
      }),
    );
  });
});
