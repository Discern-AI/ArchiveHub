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
  title: "Smiths",
  summary: "",
  visibility: "private",
  is_owner: true,
  created_at: "",
  updated_at: "",
};
const ANN = {
  id: "a",
  name: "Ann Smith",
  living: false,
  birth: "1850",
  death: "1910",
  parents: [],
  partners: [],
  children: [],
  facts: [],
};
const fact = (id: string, value: string, in_use = true) => ({
  id,
  value,
  date_text: "",
  status: "documented",
  method: "import",
  in_use,
  evidence: 1,
});

function base(extra: Record<string, () => Response>) {
  return installFetch({
    "GET /_allauth/browser/v1/auth/session": () => json({ data: { user: USER } }),
    "GET /api/v1/projects": () => json([PROJECT]),
    "GET /api/v1/projects/p1": () => json(PROJECT),
    "GET /api/v1/chats": () => json([]),
    "GET /api/v1/projects/p1/people/a": () => json(ANN),
    "GET /api/v1/projects/p1/people": () =>
      json([{ id: "a", name: "Ann Smith", living: false, birth: "1850", death: "1910" }]),
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

describe("Tidying the tree", () => {
  it("merges a duplicate, leaving out a fact the user unticks", async () => {
    const calls = base({
      "GET /api/v1/projects/p1/people/a/merge-preview": () =>
        json({
          keep: { id: "a", name: "Ann Smith", living: "deceased" },
          other: { id: "b", name: "Ann Smith", living: "deceased" },
          questions: [
            {
              question: "birth date",
              keep: [fact("k1", "1850")],
              other: [fact("o1", "ABT 1851")],
              differs: true,
            },
            { question: "occupation", keep: [], other: [fact("o2", "Dressmaker")], differs: false },
          ],
          relatives_moving: {
            parents: [{ id: "m", name: "Mary Old" }],
            children: [],
            partners: [],
          },
          residences_moving: 0,
          warnings: [],
          note: "Facts you leave out are removed with the merged record. You can undo the merge.",
        }),
      "POST /api/v1/projects/p1/people/a/merge": () =>
        json({
          change_set: "c1",
          summary: "Merged Ann Smith into Ann Smith, leaving out 1 facts",
          person: "a",
        }),
    });
    // Arriving from the health check's "Compare and merge".
    renderAt("/projects/p1/people/a?merge=b");
    const preview = await screen.findByRole("region", { name: "Merge preview" }, { timeout: 5000 });
    expect(preview).toHaveTextContent("They differ");
    expect(preview).toHaveTextContent("Parents moving across: Mary Old");
    await userEvent.click(
      within(preview).getByRole("checkbox", { name: "Bring across birth date: ABT 1851" }),
    );
    await userEvent.click(within(preview).getByRole("button", { name: "Merge" }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === "POST")?.body).toEqual({
        other: "b",
        leave_out: ["o1"],
      }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent(/undo it from "Changes and undo"/);
  });

  it("shows who a removal would cut off, and removes the ones ticked", async () => {
    const calls = base({
      "GET /api/v1/projects/p1/people/a/delete-preview": () =>
        json({
          person: { id: "a", name: "Ann Smith" },
          facts: 6,
          relationships: 2,
          residences: 0,
          stranded: [
            [
              { id: "j", name: "John Smith" },
              { id: "k", name: "Kid Smith" },
            ],
          ],
          note: "People cut off are kept unless you choose to remove them too. You can undo this.",
        }),
      "POST /api/v1/projects/p1/people/a/delete": () =>
        json({ change_set: "c2", summary: "Removed Ann Smith and 1 others" }),
    });
    renderAt("/projects/p1/people/a?view=facts");
    await userEvent.click(await screen.findByText("Remove this person"));
    const panel = await screen.findByRole("region", { name: "Remove this person" });
    expect(panel).toHaveTextContent("only connected to the tree through Ann Smith");
    await userEvent.click(within(panel).getByRole("checkbox", { name: "Remove John Smith too" }));
    await userEvent.click(
      within(panel).getByRole("button", { name: "Remove Ann Smith and 1 more" }),
    );
    await waitFor(() =>
      expect(calls.find((c) => c.method === "POST")?.body).toEqual({ also: ["j"] }),
    );
    // Back to the family page afterwards.
    expect(await screen.findByRole("heading", { name: "Smiths" })).toBeInTheDocument();
  });
});
