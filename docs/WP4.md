# WP4 — Record

**Gate (SPEC §12):** a real GEDCOM and a folder of family documents can be imported and corrected.

**Status (5 Nov 2026):** built and tested, including an end-to-end run on the real servers (upload, background reading, GEDCOM import, correction, export). Tested with a synthetic family tree (`fixtures/illustrative/sample_family.ged`), not a real one; please try one of yours.

## What was built

- **Archive** (`services/api/archive`, `/archive`): folders, drag-and-drop or chosen uploads, previews, file details, download of the unchanged original, delete with confirmation. Everything is private to the project.
- **Upload checks:** size limit (50 MB), allowed types only, and the file's bytes must match its type (a renamed program isn't accepted as a PDF). Word files are checked for unsafe expansion. Originals are stored under random names with a SHA-256 checksum.
- **Reading pipeline:** text, PDF text layers, Word documents and GEDCOM files are read automatically; images get a small preview with all EXIF removed (camera date kept as metadata; location flagged, never shown). Scanned PDFs with no text layer are flagged as needing reading.
- **Optional reading with confirmation:** "Read handwriting (AI)" and "Read printed text (OCR)" show an estimate and only run after "Use credits and start". The AI transcription is labelled as such, marks uncertain words [?], and sits beside the original, never replacing it.
- **Family trees** (`services/api/genealogy`, `/projects/:id/people`): GEDCOM import into people, relationships and claims (with the file as evidence), a person page with parents, partners and children, facts showing every version, "Add or correct a fact" (kept beside the original), and GEDCOM 5.5.1 export using what the project currently uses.
- **Privacy:** people who may be living are private; the assistant never sees them; other users can't reach a project's people, files or evidence (tested).
- **Assistant:** `search_archive` searches the text read from the user's own files, citing the file.

## Not installed on this machine (ADR-026)

- **OCR** (Tesseract) and **scanned-PDF OCR** (OCRmyPDF): OCR jobs fail with a plain message and charge nothing.
- **Malware scanner** (e.g. ClamAV): uploads say no scanner is configured. Needed before public launch.
- **Redis**: jobs run in a worker thread locally (ADR-024).

## Added later (7–10 Nov 2026)

- **Family chart** on the family page: a person with up to three generations above, partners beside and children below; choose a box to move the chart. Living people show as "Living", without dates.
- **Tree health check** (ADR-040): things worth a second look; nothing is changed or merged.
- **GEDCOM import report** (ADR-040): what came across and what didn't.
- **GEDCOM 7.0 export** (ADR-042) beside 5.5.1.
- **Where to look next** (ADR-041): the records that could exist for someone who has died, who holds them and the cost.
- **Places in the tree on the time map** (ADR-038).

## Known limits

- Credits are estimated and recorded but not yet deducted (ADR-027; ledger in WP8).
- AI handwriting reading is untested against the real API (no credit yet); its request format matches the API reference.
- The family chart shows one person's ancestors (up to three generations), partners and children, not the whole tree at once.
- Audio and video are stored but not transcribed (WP5).
- Search over files is simple word matching.
