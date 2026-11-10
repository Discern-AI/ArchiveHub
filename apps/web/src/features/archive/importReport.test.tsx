import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";
import { installFetch, json } from "../../test/fakeServer";
import { ImportReport } from "./ImportReport";

const REPORT = {
  gedcom_version: "5.5.1",
  made_by: "Ancestry.com Family Trees",
  source_citations_not_imported: 1200,
  source_records_not_imported: 300,
  notes_not_imported: 0,
  media_references: 85,
  media_files_named: 85,
  media_note: "Media in a GEDCOM file are usually references to files kept elsewhere.",
  other_facts_not_imported: { "census entries": 410 },
};

function wrap(children: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{children}</QueryClientProvider>);
}

describe("ImportReport", () => {
  it("says what came across and what was left behind", () => {
    wrap(
      <ImportReport result={{ people: 2500, families: 900, living_private: 40, report: REPORT }} />,
    );
    expect(
      screen.getByText(/2500 people and 900 families from Ancestry.com Family Trees/),
    ).toBeInTheDocument();
    expect(screen.getByText(/40 may be living/)).toBeInTheDocument();
    expect(
      screen.getByText(
        /1200 source citations, 300 source records, 85 media references, 410 census entries/,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/references to files kept elsewhere/)).toBeInTheDocument();
  });

  it("reports an update and the health check, and undoes the import in one step", async () => {
    const calls = installFetch({
      "POST /api/v1/projects/p1/changes/c1/undo": () =>
        json({
          id: "c1",
          kind: "update",
          summary: "",
          created_at: "",
          by: "",
          undone_at: "x",
          counts: {},
          blocked: [],
        }),
    });
    const onUndone = vi.fn();
    wrap(
      <ImportReport
        projectId="p1"
        onUndone={onUndone}
        result={{
          people: 4,
          families: 1,
          living_private: 0,
          report: { ...REPORT, other_facts_not_imported: {} },
          mode: "update",
          added: 2,
          updated: 2,
          not_in_file_count: 1,
          health: { count: 3 },
          change_set: "c1",
        }}
      />,
    );
    expect(
      screen.getByText(/Updated 2 people and added 2. 1 person not in this file was kept./),
    ).toBeInTheDocument();
    expect(screen.getByText(/found 3 things worth a second look/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Undo this import" }));
    await waitFor(() => expect(onUndone).toHaveBeenCalled());
    expect(calls.some((c) => c.method === "POST" && c.path.endsWith("/undo"))).toBe(true);
    expect(screen.getByText(/The import was undone/)).toBeInTheDocument();
  });
});
