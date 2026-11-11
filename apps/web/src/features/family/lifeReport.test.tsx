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
  title: "Examples",
  summary: "",
  visibility: "private",
  is_owner: true,
  created_at: "",
  updated_at: "",
};
const LABEL =
  "This shows their world, not them. Artists often made country life look more picturesque than it was.";
const REPORT = {
  private: false,
  person: { id: "t", name: "Thomas Example" },
  length: "short",
  cost: "Free: written from the records, without AI.",
  note: "Edit any text before saving. Nothing is published.",
  blocks: [
    { type: "title", text: "Thomas Example" },
    {
      type: "glance",
      born: "1825, Hungerford",
      died: "1890, Newbury",
      occupation: "Agricultural labourer",
      partners: 0,
      children: 0,
    },
    { type: "heading", text: "Early life" },
    {
      type: "paragraph",
      text: "Thomas was born in 1825 in Hungerford.",
      sources: [],
      status: "documented",
    },
    { type: "heading", text: "How artists and writers saw their world" },
    {
      type: "culture",
      key: "met-rowlandson-haymakers",
      kind: "print",
      title: "Haymakers",
      creator: "Thomas Rowlandson",
      made: "1787",
      description: "",
      image_url: "https://images.metmuseum.org/x.jpg",
      text: "",
      link_only: false,
      source_name: "The Met",
      source_url: "https://www.metmuseum.org/art/collection/search/737854",
      credit: "Thomas Rowlandson, Haymakers, 1787. The Met, public domain.",
      licence: "Public domain",
      why: "It shows haymaking, the kind of work recorded for Thomas (Agricultural labourer).",
      label: LABEL,
    },
    {
      type: "culture",
      key: "art-uk-x",
      kind: "painting",
      title: "A restricted painting",
      creator: "Someone",
      made: "1850",
      description: "",
      image_url: "",
      text: "",
      link_only: true,
      source_name: "Art UK",
      source_url: "https://artuk.org/x",
      credit: "Shown by link only.",
      licence: "Permission needed",
      why: "It shows a harvest.",
      label: LABEL,
    },
  ],
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

describe("Life Report", () => {
  it("shows each culture item with its reason, label and credit, and saves the family's edits", async () => {
    const calls = installFetch({
      "GET /_allauth/browser/v1/auth/session": () => json({ data: { user: USER } }),
      "GET /api/v1/projects": () => json([PROJECT]),
      "GET /api/v1/chats": () => json([]),
      "GET /api/v1/projects/p1/people/t/life-report": () => json(REPORT),
      "GET /api/v1/projects/p1/people/t/life-reports": () => json([]),
      "POST /api/v1/projects/p1/people/t/life-reports": () =>
        json({ id: "r1", created_at: "", items: [] }, 201),
    });
    renderAt("/projects/p1/people/t/report");
    const report = await screen.findByRole("article", { name: "Life Report" });
    expect(screen.getByText("Free: written from the records, without AI.")).toBeInTheDocument();
    const art = within(report).getByRole("figure", { name: "Haymakers" });
    expect(
      within(art).getByRole("img", { name: "Haymakers, Thomas Rowlandson" }),
    ).toBeInTheDocument();
    expect(art).toHaveTextContent("Why this was chosen: It shows haymaking");
    expect(art).toHaveTextContent("This shows their world, not them.");
    expect(art).toHaveTextContent("The Met, public domain.");
    // Restricted: no image, a link instead.
    const restricted = within(report).getByRole("figure", { name: "A restricted painting" });
    expect(within(restricted).queryByRole("img")).not.toBeInTheDocument();
    expect(within(restricted).getByRole("link", { name: /See it at Art UK/ })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Edit" }));
    const para = screen.getByLabelText("Paragraph");
    await userEvent.clear(para);
    await userEvent.type(para, "Edited by the family.");
    await userEvent.click(within(restricted).getByRole("button", { name: "Leave this out" }));
    await userEvent.click(screen.getByRole("button", { name: "Save this version" }));
    await waitFor(() => expect(calls.some((c) => c.method === "POST")).toBe(true));
    const body = calls.find((c) => c.method === "POST")!.body as {
      blocks: { type: string; text?: string; key?: string }[];
    };
    expect(body.blocks.find((b) => b.type === "paragraph")?.text).toBe("Edited by the family.");
    expect(body.blocks.some((b) => b.key === "art-uk-x")).toBe(false);
    expect(await screen.findByRole("status")).toHaveTextContent("Saved.");
  });
});
