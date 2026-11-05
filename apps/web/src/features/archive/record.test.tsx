import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { AppRoutes } from "../../app/routes";
import { installFetch, json } from "../../test/fakeServer";

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
const FILE = {
  id: "f1",
  name: "letter.jpg",
  folder_id: null,
  kind: "image",
  size: 2048,
  status: "needs_processing",
  status_detail: "Preview made.",
  scan_note: "File type checked. No malware scanner is configured on this server yet.",
  page_count: 1,
  has_preview: true,
  created_at: "",
};
const base = {
  "GET /_allauth/browser/v1/auth/session": () => json({ data: { user: USER } }),
  "GET /api/v1/projects": () => json([PROJECT]),
  "GET /api/v1/projects/p1": () => json(PROJECT),
  "GET /api/v1/chats": () => json([]),
  "GET /api/v1/projects/p1/folders": () => json([]),
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

describe("Record", () => {
  it("uploads a file and only reads handwriting after the user confirms the estimate", async () => {
    let files: unknown[] = [];
    let job: Record<string, unknown> | null = null;
    const calls = installFetch({
      ...base,
      "GET /api/v1/projects/p1/files": () => json(files),
      "POST /api/v1/projects/p1/files": () => {
        files = [FILE];
        return json(FILE, 201);
      },
      "GET /api/v1/files/f1": () =>
        json({
          ...FILE,
          sha256: "a".repeat(64),
          metadata: {},
          texts:
            job?.status === "done"
              ? [
                  {
                    id: "t1",
                    method: "ai_handwriting",
                    engine: "m",
                    note: "AI transcription. Check it against the original.",
                    text: "Dear Mum",
                  },
                ]
              : [],
          jobs: job ? [job] : [],
          can_process: [{ kind: "handwriting", label: "Read handwriting (AI)" }],
        }),
      "POST /api/v1/files/f1/jobs": () => {
        job = {
          id: "j1",
          kind: "handwriting",
          status: "awaiting_confirmation",
          estimate_credits: 2,
          credits_used: 0,
          error: "",
          result: {},
          created_at: "",
        };
        return json(job, 201);
      },
      "POST /api/v1/jobs/j1/confirm": () => {
        job = { ...job!, status: "done", credits_used: 2 };
        return json(job);
      },
    });
    const user = userEvent.setup();
    renderAt("/archive");

    const input = await screen.findByLabelText("Choose files");
    await user.upload(input, new File(["jpegbytes"], "letter.jpg", { type: "image/jpeg" }));
    expect(await screen.findByRole("status")).toHaveTextContent("They're private");
    expect(
      calls.find((c) => c.method === "POST" && c.path === "/api/v1/projects/p1/files")?.body,
    ).toEqual({ file: "letter.jpg" });

    await user.click(await screen.findByRole("button", { name: "letter.jpg" }));
    const panel = await screen.findByRole("complementary", { name: "File details" });
    expect(within(panel).getByText(/No malware scanner/)).toBeVisible();
    await user.click(within(panel).getByRole("button", { name: "Read handwriting (AI)" }));

    const dialog = await within(panel).findByRole("alertdialog", { name: "Confirm credit use" });
    expect(dialog).toHaveTextContent("about 2 credits");
    expect(calls.some((c) => c.path === "/api/v1/jobs/j1/confirm")).toBe(false);
    await user.click(within(dialog).getByRole("button", { name: "Use credits and start" }));
    expect(await within(panel).findByText("Dear Mum")).toBeVisible();
    expect(within(panel).getByText(/Check it against the original/)).toBeVisible();
  });

  it("shows a person's family and saves a correction beside the imported fact", async () => {
    const claims: unknown[] = [];
    const person = (corrected: boolean) => ({
      id: "a",
      name: "Arthur Sample",
      living: false,
      birth: corrected ? "1922" : "ABT 1921",
      death: "14 MAR 1988",
      parents: [{ id: "w", name: "Walter Sample", living: false, birth: "1890", death: "" }],
      partners: [{ id: "e", name: "Edith Fictional", living: false, birth: "1923", death: "" }],
      children: [{ id: "c", name: "Alice Sample", living: true, birth: "", death: "" }],
      facts: [
        {
          question: "birth date",
          disputed: corrected,
          answers: [
            {
              id: "x1",
              value: "ABT 1921",
              status: "documented",
              method: "import",
              note: "",
              in_use: !corrected,
              evidence: [],
            },
            ...(corrected
              ? [
                  {
                    id: "x2",
                    value: "1922",
                    status: "remembered",
                    method: "user",
                    note: "Mum always said 1922",
                    in_use: true,
                    evidence: [],
                  },
                ]
              : []),
          ],
        },
      ],
    });
    installFetch({
      ...base,
      "GET /api/v1/projects/p1/people/a": () => json(person(claims.length > 0)),
      "POST /api/v1/projects/p1/people/a/claims": (_url, init) => {
        claims.push(JSON.parse(String(init.body)));
        return json({ id: "x2" }, 201);
      },
    });
    const user = userEvent.setup();
    renderAt("/projects/p1/people/a");

    expect(await screen.findByRole("heading", { name: "Arthur Sample" })).toBeVisible();
    expect(screen.getByRole("link", { name: /Walter Sample/ })).toBeVisible();
    expect(screen.getByRole("link", { name: /Alice Sample,\s*Living \(private\)/ })).toBeVisible();

    await user.type(screen.getByLabelText("Value"), "1922");
    await user.type(
      screen.getByLabelText("Where it comes from (optional)"),
      "Mum always said 1922",
    );
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("status")).toHaveTextContent("earlier version stays on file");
    expect(claims).toEqual([
      {
        predicate: "birth date",
        value: "1922",
        status: "remembered",
        note: "Mum always said 1922",
      },
    ]);
    expect(await screen.findByText("Versions differ")).toBeVisible();
    expect(screen.getByText("ABT 1921")).toBeVisible();
  });
});
