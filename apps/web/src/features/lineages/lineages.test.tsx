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
  title: "Spracklens",
  summary: "",
  visibility: "private",
  is_owner: true,
  created_at: "",
  updated_at: "",
};
const base = {
  "GET /_allauth/browser/v1/auth/session": () => json({ data: { user: USER } }),
  "GET /api/v1/projects": () => json([PROJECT]),
  "GET /api/v1/projects/p1": () => json(PROJECT),
  "GET /api/v1/chats": () => json([]),
};
const holder = (id: string, name: string | null, from: number, to: number, extra = {}) => ({
  id,
  name,
  hidden: name === null,
  year_from: from,
  year_to: to,
  date_text: from === to ? `${from}` : `${from}–${to}`,
  status: "documented",
  sources: [
    {
      title: "Pub Wiki: Pigeons",
      url: "https://pubwiki.co.uk/x",
      source: "Pub Wiki",
      what_it_says: "1881 census: publican.",
    },
  ],
  connections: [],
  ...extra,
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

describe("Lineages", () => {
  it("shows licensees in order, gaps as not recorded, and hides recent names", async () => {
    installFetch({
      ...base,
      "GET /api/v1/lineages/organisation/o1": () =>
        json({
          subject: { id: "o1", name: "The Pigeons", type: "organisation" },
          role: "licensee",
          role_label: "Licensees",
          roles: [{ role: "licensee", label: "Licensees", count: 3 }],
          holders: [
            holder("a", "William Turk", 1881, 1881),
            holder("b", "John Spracklen", 1901, 1928, {
              connections: [
                {
                  project: "Spracklens",
                  project_id: "p1",
                  person_id: "s",
                  name: "John Spracklen",
                  reason: "same first name and surname; alive then (1870–1945)",
                },
              ],
            }),
            holder("c", null, 1940, 1940),
          ],
          gaps: [
            { from: 1882, to: 1900 },
            { from: 1929, to: 1939 },
          ],
          hidden_recent: 1,
          notes: ["1 recent holder may still be living, so names are hidden."],
        }),
    });
    renderAt("/lineages/organisation/o1");
    expect(await screen.findByRole("heading", { name: "The Pigeons" })).toBeInTheDocument();
    expect(screen.getAllByTestId("succession-bar")).toHaveLength(3);
    expect(screen.getByText("Not recorded 1882–1900")).toBeInTheDocument();
    expect(screen.getByText("Name hidden (may be living)")).toBeInTheDocument();
    const list = screen.getByRole("region", { name: "Holders and their records" });
    expect(list).toHaveTextContent("May be John Spracklen in Spracklens");
    expect(list).toHaveTextContent("Check the records before treating them as the same person.");
    await userEvent.click(within(list).getAllByRole("button", { name: "Sources (1)" })[0]);
    expect(within(list).getByRole("link", { name: /Pub Wiki: Pigeons/ })).toBeInTheDocument();
  });
});

describe("Ordering records", () => {
  it("shows the fees and tracks an order until the record arrives", async () => {
    let status: "planned" | "ordered" = "planned";
    let tracked = false;
    const order = () => ({
      id: "r1",
      title: "Birth record of Arthur Sample: pdf copy",
      holder: "General Register Office (England and Wales)",
      route_label: "You order from the holder; we keep track",
      fees: [{ label: "General Register Office fee", pence: 800 }],
      total_pence: 800,
      delivery: "",
      url: "",
      rights_label: "",
      details: { event: "birth", index_reference: "SAMPLE 2c 123" },
      status,
      status_label: status === "planned" ? "Not ordered yet" : "Ordered",
      reference: "",
      file_id: null,
      person_id: "a",
    });
    const calls = installFetch({
      ...base,
      "GET /api/v1/projects/p1/people/a": () =>
        json({
          id: "a",
          name: "Arthur Sample",
          living: false,
          birth: "1890",
          death: "1960",
          parents: [],
          partners: [],
          children: [],
          facts: [],
        }),
      "GET /api/v1/projects/p1/people/a/record-offers": () =>
        json({
          note: "ArchiveHub doesn't sell these: you order from the holder, and we keep track.",
          events: [
            {
              event: "birth",
              year: 1890,
              date_text: "1890",
              place: "Newbury",
              note: "Find the GRO index reference first.",
              offers: [
                {
                  key: "gro-pdf",
                  title: "PDF copy",
                  holder: "General Register Office (England and Wales)",
                  route: "referral",
                  fees: [{ label: "General Register Office fee", pence: 800 }],
                  total_pence: 800,
                  delivery: "In your GRO online account within four working days.",
                  should_show: "An image of the registration entry, as a PDF.",
                  needs_index_reference: true,
                  url: "https://www.gro.gov.uk/gro/content/certificates/",
                  how: "Order on the General Register Office website, then mark it ordered here.",
                  rights_label: "A copy of a public record for your own research.",
                  sources: [{ title: "GRO certificate FAQ", url: "https://www.gro.gov.uk/faq" }],
                  checked_on: "2026-11-11",
                },
              ],
            },
          ],
        }),
      "GET /api/v1/record-orders": () => json(tracked ? [order()] : []),
      "POST /api/v1/record-orders": () => {
        tracked = true;
        return json(order(), 201);
      },
      "PATCH /api/v1/record-orders/r1": () => {
        status = "ordered";
        return json(order());
      },
      "GET /api/v1/projects/p1/files": () => json([]),
    });
    renderAt("/projects/p1/people/a?view=facts");
    await userEvent.click(await screen.findByText("Order records"));
    const card = await screen.findByRole("group", { name: "PDF copy of the birth" });
    expect(card).toHaveTextContent("PDF copy · £8.00");
    expect(card).toHaveTextContent("General Register Office fee: £8.00");
    expect(card).toHaveTextContent("ArchiveHub fee: none");
    expect(card).toHaveTextContent("checked 2026-11-11");
    await userEvent.type(within(card).getByLabelText("GRO index reference"), "SAMPLE 2c 123");
    await userEvent.click(within(card).getByRole("button", { name: "Track this order" }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === "POST")?.body).toEqual({
        project_id: "p1",
        person_id: "a",
        offer_key: "gro-pdf",
        event: "birth",
        index_reference: "SAMPLE 2c 123",
      }),
    );
    const mine = await screen.findByRole("group", {
      name: "Birth record of Arthur Sample: pdf copy",
    });
    await userEvent.click(within(mine).getByRole("button", { name: "I've ordered it" }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({
        status: "ordered",
        reference: "",
      }),
    );
  });
});
