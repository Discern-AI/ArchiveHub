import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { installFetch, json } from "../../test/fakeServer";
import { ImportTree } from "./ImportTree";

const PREVIEW = {
  people: 4,
  families: 1,
  living_private: 0,
  mode: "update",
  added: 2,
  updated: 2,
  not_in_file: ["Cy Gone"],
  not_in_file_count: 1,
  id_but_not_name: [{ id: "@I3@", in_tree: "Cy Gone", in_file: "Zed Stranger" }],
  report: {},
  health: {
    findings: [
      {
        kind: "duplicates",
        title: "Possibly the same person",
        detail: "",
        people: [
          { id: "a", name: "Ada Example" },
          { id: "b", name: "Ada Example" },
        ],
      },
    ],
  },
};

describe("Importing a family tree", () => {
  it("previews an update to an earlier tree, then imports it", async () => {
    const calls = installFetch({
      "GET /api/v1/projects/p1/trees": () =>
        json([
          {
            tree: "gedcom:f0",
            first_file: "v1.ged",
            people: 3,
            last_updated: null,
            last_file: "v1.ged",
          },
        ]),
      "GET /api/v1/files/f2/gedcom-preview": () => json(PREVIEW),
      "POST /api/v1/files/f2/jobs": () =>
        json({ id: "j", kind: "gedcom_import", status: "done", result: {} }, 201),
    });
    const onImported = vi.fn();
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <ImportTree fileId="f2" projectId="p1" onImported={onImported} />
      </QueryClientProvider>,
    );
    // An earlier tree exists, so updating it is offered first.
    expect(await screen.findByRole("radio", { name: /Update v1.ged/ })).toBeChecked();
    await userEvent.click(screen.getByRole("button", { name: "Preview the import" }));
    const preview = await screen.findByRole("region", { name: "Import preview" });
    expect(preview).toHaveTextContent("2 would be updated and 2 added");
    expect(preview).toHaveTextContent("1 person in the tree isn't in this file. They'll be kept.");
    expect(preview).toHaveTextContent("Zed Stranger (the tree has Cy Gone as @I3@)");
    expect(
      within(preview).getByRole("list", { name: "Health check after import" }),
    ).toHaveTextContent("Possibly the same person: Ada Example, Ada Example");
    expect(preview).toHaveTextContent("Nothing has changed yet");
    expect(calls.find((c) => c.path.startsWith("/api/v1/files/f2/gedcom-preview"))?.path).toBe(
      "/api/v1/files/f2/gedcom-preview?mode=update&base=gedcom%3Af0",
    );
    await userEvent.click(screen.getByRole("button", { name: "Update the tree" }));
    await waitFor(() => expect(onImported).toHaveBeenCalled());
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({
      kind: "gedcom_import",
      options: { mode: "update", base: "gedcom:f0" },
    });
  });
});
