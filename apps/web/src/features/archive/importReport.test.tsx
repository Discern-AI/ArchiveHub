import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ImportReport } from "./ImportReport";

describe("ImportReport", () => {
  it("says what came across and what was left behind", () => {
    render(
      <ImportReport
        result={{
          people: 2500,
          families: 900,
          living_private: 40,
          report: {
            gedcom_version: "5.5.1",
            made_by: "Ancestry.com Family Trees",
            source_citations_not_imported: 1200,
            source_records_not_imported: 300,
            notes_not_imported: 0,
            media_references: 85,
            media_files_named: 85,
            media_note: "Media in a GEDCOM file are usually references to files kept elsewhere.",
            other_facts_not_imported: { residences: 410 },
          },
        }}
      />,
    );
    expect(
      screen.getByText(/2500 people and 900 families from Ancestry.com Family Trees/),
    ).toBeInTheDocument();
    expect(screen.getByText(/40 may be living/)).toBeInTheDocument();
    expect(
      screen.getByText(
        /1200 source citations, 300 source records, 85 media references, 410 residences/,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/references to files kept elsewhere/)).toBeInTheDocument();
  });
});
