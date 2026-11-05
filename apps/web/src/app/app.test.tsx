import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { installFetch, json, sseResponse } from "../test/fakeServer";
import { AppRoutes } from "./routes";

const USER = { id: "u1", email: "alice@example.com", display: "alice" };
const signedIn = { "GET /_allauth/browser/v1/auth/session": () => json({ data: { user: USER } }) };
const emptyLists = {
  "GET /api/v1/projects": () => json([]),
  "GET /api/v1/chats": () => json([]),
};

function renderApp(path = "/chat") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ArchiveHub app", () => {
  it("sends signed-out visitors to the sign-in page", async () => {
    installFetch({ "GET /_allauth/browser/v1/auth/session": () => json({}, 401) });
    renderApp("/chat");
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("shows the shell and the four starter prompts on a new chat", async () => {
    installFetch({ ...signedIn, ...emptyLists });
    renderApp("/chat");
    expect(await screen.findByRole("heading", { name: "What are you working on?" })).toBeVisible();
    for (const name of [
      /Record your family or local history/,
      /Research a person, place or event/,
      /Are you a historian, archivist or blogger\?/,
      /Is this for your business or services\?/,
    ]) {
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    }
    expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Projects and chats" })).toBeInTheDocument();
  });

  it("creates a chat, streams the reply and hides the starter prompts", async () => {
    const calls = installFetch({
      ...signedIn,
      ...emptyLists,
      "POST /api/v1/chats": () =>
        json({ id: "c1", project_id: null, title: "", created_at: "", updated_at: "" }, 201),
      "POST /api/v1/chats/c1/stream": () =>
        sseResponse([
          [
            "start",
            {
              user_message: {
                id: "m1",
                role: "user",
                content: "Where was the Pigeons?",
                status: "complete",
                created_at: "",
              },
              reply_id: "m2",
            },
          ],
          ["delta", { text: "Sources " }],
          ["delta", { text: "disagree." }],
          [
            "done",
            {
              message: {
                id: "m2",
                role: "assistant",
                content: "Sources disagree.",
                status: "complete",
                created_at: "",
              },
            },
          ],
        ]),
    });
    const user = userEvent.setup();
    renderApp("/chat");

    const box = await screen.findByLabelText("Message ArchiveHub");
    await user.type(box, "Where was the Pigeons?{Enter}");

    expect(await screen.findByText("Sources disagree.")).toBeInTheDocument();
    expect(screen.getByText("Where was the Pigeons?")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "What are you working on?" })).toBeNull();
    expect(box).toHaveValue("");

    const stream = calls.find((c) => c.path === "/api/v1/chats/c1/stream")!;
    expect(stream.body).toEqual({ content: "Where was the Pigeons?" });
    expect(stream.headers.get("X-CSRFToken")).toBe("test-token");
  });

  it("shows an error state when the reply fails", async () => {
    installFetch({
      ...signedIn,
      ...emptyLists,
      "GET /api/v1/chats/c9/messages": () => json([]),
      "POST /api/v1/chats/c9/stream": () => json({ detail: "Not Found" }, 404),
    });
    const user = userEvent.setup();
    renderApp("/chat/c9");
    const box = await screen.findByLabelText("Message ArchiveHub");
    await user.type(box, "hello{Enter}");
    expect(await screen.findByRole("alert")).toHaveTextContent("Not Found");
    expect(screen.getByText(/This reply didn't finish/)).toBeInTheDocument();
  });

  it("loads an existing conversation", async () => {
    installFetch({
      ...signedIn,
      ...emptyLists,
      "GET /api/v1/chats/c2/messages": () =>
        json([
          {
            id: "a",
            role: "user",
            content: "Earlier question",
            status: "complete",
            created_at: "",
          },
          {
            id: "b",
            role: "assistant",
            content: "Earlier answer",
            status: "incomplete",
            created_at: "",
          },
        ]),
    });
    renderApp("/chat/c2");
    expect(await screen.findByText("Earlier answer")).toBeInTheDocument();
    expect(screen.getByText(/cut off/)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "What are you working on?" })).toBeNull();
  });

  it("creates a project and lists it", async () => {
    let projects: unknown[] = [];
    const project = {
      id: "p1",
      title: "The Pigeons",
      summary: "",
      visibility: "private",
      is_owner: true,
      created_at: "",
      updated_at: "",
    };
    installFetch({
      ...signedIn,
      "GET /api/v1/chats": () => json([]),
      "GET /api/v1/projects": () => json(projects),
      "POST /api/v1/projects": () => {
        projects = [project];
        return json(project, 201);
      },
      "GET /api/v1/projects/p1": () => json(project),
    });
    const user = userEvent.setup();
    renderApp("/projects/new");
    await user.type(await screen.findByLabelText("Name"), "The Pigeons");
    await user.click(screen.getByRole("button", { name: "Create project" }));
    expect(await screen.findByRole("heading", { name: "The Pigeons" })).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("link", { name: "The Pigeons" })).toBeInTheDocument(),
    );
  });
});
