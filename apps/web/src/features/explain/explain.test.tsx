import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { AppRoutes } from "../../app/routes";
import { installFetch, json } from "../../test/fakeServer";
import { LifeAndTimes } from "./LifeAndTimes";

const USER = { id: "u1", email: "alice@example.com", display: "alice" };
const TNA = {
  title: "The National Archives: Workhouse inmates and staff",
  url: "https://www.nationalarchives.gov.uk/x",
};
const EXPLAINED = {
  says: { text: "Mary Smith, a pauper, in the workhouse", year: 1790, place: "Hungerford" },
  words: [
    {
      term: "Workhouse",
      found: "workhouse",
      meaning: "From the Poor Law Amendment Act of 1834, parishes were combined into unions…",
      area: "England and Wales",
      applies: false,
      period_note: "Before 1834 the poor laws were mostly run by each parish.",
      sources: [TNA],
      contributed_by: "",
    },
    {
      term: "Cordwainer",
      found: "cordwainer",
      meaning: "A shoemaker working new leather.",
      area: "",
      applies: true,
      period_note: "",
      sources: [{ title: "A dictionary of old trades", url: "" }],
      contributed_by: "Bob, Berkshire FHS",
    },
  ],
  may_mean: [
    {
      term: "Pauper",
      text: "It describes their situation when the record was made, not their whole life.",
      sources: [TNA],
    },
  ],
  may_mean_label:
    "Careful readings of what records like this usually show. They describe what was common, not what happened to this person.",
  find_out_more: [
    {
      text: "For Hungerford, start with Royal Berkshire Archives (Berkshire Record Office).",
      sources: [],
    },
  ],
  sensitive: true,
  sensitive_note:
    "Records of workhouses and poor relief can be hard to read about. Descendants decide what's shared; nothing here is published.",
  nothing_found: false,
  note: "",
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

describe("Explain this record", () => {
  it("shows the four layers, with the period warning, credit and sensitivity", async () => {
    const calls = installFetch({
      "GET /_allauth/browser/v1/auth/session": () => json({ data: { user: USER } }),
      "GET /api/v1/projects": () => json([]),
      "GET /api/v1/chats": () => json([]),
      "POST /api/v1/explain": () => json(EXPLAINED),
      "POST /api/v1/explanations": () =>
        json(
          {
            id: "x",
            status: "proposed",
            note: "Thank you. It'll be shown, with your credit, once reviewed.",
          },
          201,
        ),
    });
    renderAt("/explain");
    await userEvent.type(
      await screen.findByLabelText("The record's wording"),
      "Mary Smith, a pauper, in the workhouse",
    );
    await userEvent.type(screen.getByLabelText("Year"), "1790");
    await userEvent.type(screen.getByLabelText("Place"), "Hungerford");
    await userEvent.click(screen.getByRole("button", { name: "Explain this record" }));
    await waitFor(() =>
      expect(calls.find((c) => c.path === "/api/v1/explain")?.body).toEqual({
        text: "Mary Smith, a pauper, in the workhouse",
        year: 1790,
        place: "Hungerford",
      }),
    );
    const says = await screen.findByRole("region", { name: "What it says" });
    expect(says).toHaveTextContent("Dated 1790 · Hungerford");
    const words = screen.getByRole("region", { name: "What the words mean" });
    expect(words).toHaveTextContent("Before 1834 the poor laws were mostly run by each parish.");
    expect(words).toHaveTextContent("Explained by Bob, Berkshire FHS");
    expect(
      within(words).getAllByRole("link", { name: /The National Archives/ })[0],
    ).toHaveAttribute("href", TNA.url);
    expect(screen.getByRole("region", { name: "What it may mean for them" })).toHaveTextContent(
      "not what happened to this person",
    );
    expect(screen.getByRole("region", { name: "Where to find out more" })).toHaveTextContent(
      "Royal Berkshire Archives",
    );
    expect(screen.getByText(/Descendants decide what's shared/)).toBeInTheDocument();

    await userEvent.click(screen.getByText("Know what a word means? Explain it for others"));
    await userEvent.type(screen.getByLabelText("The word or term"), "Ag lab");
    await userEvent.type(
      screen.getByLabelText("What it meant, in your words"),
      "Agricultural labourer.",
    );
    await userEvent.type(
      screen.getByLabelText(/Where it comes from/),
      "Census enumerators' instructions",
    );
    await userEvent.type(screen.getByLabelText("Credit it to"), "Alice");
    await userEvent.click(screen.getByRole("button", { name: "Offer this explanation" }));
    expect(await screen.findByRole("status")).toHaveTextContent("once reviewed");
  });
});

describe("Life and times", () => {
  it("shows money, weather and events for the chosen year, as context", async () => {
    const calls = installFetch({
      "GET /api/v1/life-and-times": (url) =>
        json({
          year: Number(url.searchParams.get("year")),
          label: "Context: what the world was like, not a fact about anyone in particular.",
          money: {
            available: true,
            sentence: `£1 in ${url.searchParams.get("year")} would buy roughly what £173 did in 2025.`,
            note: "A comparison of average retail prices, not of wages.",
            source: "Office for National Statistics",
            source_url: "https://www.ons.gov.uk/",
          },
          weather: {
            available: true,
            sentence: "In central England, 1900 averaged 9.6°C, about average.",
            rank: "",
            note: "A region, not their town.",
            source: "Met Office HadCET",
            source_url: "https://www.metoffice.gov.uk/hadobs/hadcet/",
          },
          happening: [
            {
              title: "Boer War",
              date_text: "1899–1902",
              area: "",
              kind: "war",
              when: "under way",
              source_title: "NAM",
              source_url: "https://www.nam.ac.uk/explore/boer-war",
            },
          ],
          accounts: {
            available: false,
            note: "Diaries need permission to show here.",
            search: "diaries",
          },
        }),
    });
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <LifeAndTimes from={1890} to={1960} initial={1900} who="Arthur" />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    const panel = await screen.findByRole("region", { name: "Life and times" });
    expect(await within(panel).findByText(/£1 in 1900 would buy/)).toBeInTheDocument();
    expect(panel).toHaveTextContent("not a fact about anyone");
    expect(panel).toHaveTextContent("Boer War (1899–1902): under way.");
    expect(panel).toHaveTextContent("Arthur was about 10");
    fireEvent.change(within(panel).getByLabelText("Year for life and times"), {
      target: { value: "1914" },
    });
    await waitFor(() =>
      expect(calls.some((c) => c.path === "/api/v1/life-and-times?year=1914")).toBe(true),
    );
  });
});
