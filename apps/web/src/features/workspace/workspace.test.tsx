import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { AppRoutes } from "../../app/routes";
import { installFetch, json, sseResponse } from "../../test/fakeServer";
import { recordImage } from "./ExplorerTab";

const USER = { id: "u1", email: "alice@example.com", display: "alice" };
const CHAT = { id: "c1", project_id: "p1", title: "Pigeons", created_at: "", updated_at: "" };
const RECORD = {
  connector: "checked-reference",
  id: "closedpubs-pigeons",
  title: "The Pigeons, Newbury (Closed Pubs)",
  description: "Gives 69 Cheap Street with no source.",
  record_type: "lost pub listing",
  url: "https://www.closedpubs.co.uk/berkshire/newbury_pigeons.html",
  date_text: "",
  latitude: null,
  longitude: null,
  fields: { address: "69 Cheap Street" },
  rights: "Our own summary",
  attribution: "Closed Pubs",
};
const DISPUTE = {
  subject_type: "organisation",
  subject_id: "o1",
  subject: "The Pigeons",
  predicate: "address",
};

const base = {
  "GET /_allauth/browser/v1/auth/session": () => json({ data: { user: USER } }),
  "GET /api/v1/projects": () => json([]),
  "GET /api/v1/chats": () => json([]),
  "GET /api/v1/chats/c1": () => json(CHAT),
  "GET /api/v1/explorer/sources": () =>
    json([
      {
        key: "checked-reference",
        name: "ArchiveHub checked records",
        description: "Hand-checked facts.",
        access_type: "hosted",
        capabilities: ["search"],
        licence: "",
        attribution: "",
        storage: "reference_only",
        available: true,
      },
      {
        key: "europeana",
        name: "Europeana",
        description: "European collections.",
        access_type: "live_api",
        capabilities: ["search"],
        licence: "",
        attribution: "",
        storage: "metadata_only",
        available: false,
        note: "Needs a Europeana project API key",
      },
    ]),
  "GET /api/v1/explorer/checked-reference/search": () =>
    json({ records: [RECORD], next_cursor: null, searched: "" }),
  "GET /api/v1/explorer/checked-reference/records/closedpubs-pigeons": () =>
    json({ ...RECORD, citation: "The Pigeons. Closed Pubs", storage: "reference_only" }),
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

describe("Workspace", () => {
  it("browses a source, saves a record and asks the assistant about it", async () => {
    const calls = installFetch({
      ...base,
      "GET /api/v1/chats/c1/messages": () => json([]),
      "POST /api/v1/projects/p1/basket": () =>
        json(
          {
            id: "b1",
            connector: "checked-reference",
            external_id: RECORD.id,
            title: RECORD.title,
            url: RECORD.url,
            storage: "reference_only",
            note: "",
            created_at: "",
          },
          201,
        ),
      "GET /api/v1/projects/p1/basket": () => json([]),
      "POST /api/v1/chats/c1/stream": () =>
        sseResponse([
          ["delta", { text: "It gives 69 Cheap Street [1]." }],
          [
            "done",
            {
              message: {
                id: "m2",
                role: "assistant",
                content: "It gives 69 Cheap Street [1].",
                status: "complete",
                created_at: "",
              },
            },
          ],
        ]),
    });
    const user = userEvent.setup();
    renderAt("/chat/c1");

    await user.click(await screen.findByRole("button", { name: "Open Explorer" }));
    const panel = await screen.findByRole("complementary", { name: "Workspace" });
    // Sources that aren't set up are listed with what they need, not hidden.
    expect(
      await within(panel).findByText("1 more source isn't available here yet"),
    ).toBeInTheDocument();
    expect(within(panel).getByText(/Needs a Europeana project API key/)).toBeInTheDocument();
    expect(within(panel).queryByRole("option", { name: /Europeana/ })).not.toBeInTheDocument();
    await user.click(await within(panel).findByRole("button", { name: /The Pigeons, Newbury/ }));
    expect(await within(panel).findByText("Cite as: The Pigeons. Closed Pubs")).toBeVisible();
    expect(within(panel).getByRole("link", { name: "Open the original" })).toHaveAttribute(
      "href",
      RECORD.url,
    );

    await user.click(within(panel).getByRole("button", { name: "Save to project" }));
    expect(await within(panel).findByRole("status")).toHaveTextContent("Saved");
    expect(calls.find((c) => c.method === "POST" && c.path.endsWith("/basket"))?.body).toEqual({
      connector: "checked-reference",
      record_id: "closedpubs-pigeons",
    });

    await user.click(within(panel).getByRole("button", { name: "Ask about this record" }));
    expect(screen.getByText(RECORD.title, { selector: "strong" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Message ArchiveHub"), "What does it say?{Enter}");
    expect(await screen.findByText("It gives 69 Cheap Street [1].")).toBeInTheDocument();
    const stream = calls.find((c) => c.path === "/api/v1/chats/c1/stream")!;
    expect(stream.body).toEqual({
      content: "What does it say?",
      record: { connector: "checked-reference", id: "closedpubs-pigeons" },
    });
  });

  it("compares disputed sources and records the project's choice", async () => {
    const decisions: unknown[] = [];
    installFetch({
      ...base,
      "GET /api/v1/chats/c1/messages": () =>
        json([
          { id: "a", role: "user", content: "Where?", status: "complete", created_at: "" },
          {
            id: "b",
            role: "assistant",
            content: "Sources disagree.",
            status: "complete",
            disputes: [DISPUTE],
            created_at: "",
          },
        ]),
      "GET /api/v1/evidence/organisation/o1": () =>
        json({
          subject: { type: "organisation", id: "o1", name: "The Pigeons" },
          predicate: "address",
          disputed: true,
          decision: decisions.length ? { chosen_id: "a5", keep_disputed: false } : null,
          claims: [
            {
              id: "a5",
              value: "5 Cheap Street",
              date: null,
              status: "documented",
              method: "import",
              note: "",
              evidence: [
                {
                  record_title: "Kelly's 1970",
                  record_key: "k",
                  source: "Pub Wiki",
                  url: "https://pubwiki.co.uk/x",
                  what_it_says: "Listed at 5.",
                  stance: "supports",
                  suggested_weight: "stronger",
                  weight_suggested_by: "editor",
                },
              ],
            },
            {
              id: "a69",
              value: "69 Cheap Street",
              date: null,
              status: "documented",
              method: "import",
              note: "",
              evidence: [],
            },
          ],
        }),
      "PUT /api/v1/projects/p1/decisions": (_url, init) => {
        decisions.push(JSON.parse(String(init.body)));
        return json({ ok: true });
      },
    });
    const user = userEvent.setup();
    renderAt("/chat/c1");

    await user.click(await screen.findByRole("button", { name: "Compare sources" }));
    const panel = await screen.findByRole("complementary", { name: "Workspace" });
    expect(await within(panel).findByText("Address of The Pigeons")).toBeVisible();
    // Simple by default; full comparison one click away, with weights labelled.
    expect(within(panel).queryByText("Listed at 5.")).toBeNull();
    await user.click(within(panel).getByRole("button", { name: "Show the full comparison" }));
    expect(within(panel).getByText(/suggested by an ArchiveHub editor/)).toBeVisible();

    await user.type(within(panel).getByLabelText("Your reason (optional)"), "Three sources agree");
    await user.click(within(panel).getByRole("button", { name: "Use 5 Cheap Street" }));
    expect(await within(panel).findByRole("status")).toHaveTextContent("stay on file");
    expect(decisions).toEqual([
      {
        subject_type: "organisation",
        subject_id: "o1",
        predicate: "address",
        chosen_id: "a5",
        reason: "Three sources agree",
      },
    ]);
    expect(
      await within(panel).findByRole("button", { name: "Used in this project" }),
    ).toHaveAttribute("aria-pressed", "true");
  });
});

describe("recordImage", () => {
  const base = {
    connector: "met-museum",
    id: "1",
    title: "Side Chair",
    description: "",
    record_type: "",
    url: "https://www.metmuseum.org/x",
    date_text: "",
    latitude: null,
    longitude: null,
    rights: "",
    attribution: "",
  };
  it("shows public-domain museum images and credited Geograph photos only", () => {
    expect(
      recordImage({ ...base, fields: { image: "https://images.metmuseum.org/a.jpg" } }),
    ).toEqual({ src: "https://images.metmuseum.org/a.jpg", credit: "Public domain" });
    expect(
      recordImage({
        ...base,
        connector: "geograph",
        fields: { thumbnail: "https://s0.geograph.org.uk/t.jpg", photographer: "Lewis Clarke" },
      })?.credit,
    ).toBe("Photo © Lewis Clarke, CC BY-SA 2.0, via Geograph");
    // A Europeana preview has per-item rights, so it isn't shown.
    expect(
      recordImage({ ...base, connector: "europeana", fields: { preview: "https://x/p.jpg" } }),
    ).toBeNull();
    expect(recordImage({ ...base, fields: { image: "http://insecure/x.jpg" } })).toBeNull();
  });
});
