import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { api } from "../../lib/api";

const card = "flex flex-col gap-1.5 rounded-lg border border-line bg-surface p-4";

export function ProjectPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.project(projectId!),
  });
  const chats = useQuery({
    queryKey: ["chats", { projectId }],
    queryFn: () => api.chats(projectId),
  });

  if (project.isPending) return <p className="p-8 text-muted">Loading…</p>;
  if (project.isError) return <p className="p-8 text-warning">This project couldn't be found.</p>;
  const p = project.data;

  async function remove() {
    try {
      await api.deleteProject(p.id);
      await qc.invalidateQueries({ queryKey: ["projects"] });
      await qc.invalidateQueries({ queryKey: ["chats"] });
      navigate("/chat");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-[1040px] flex-col gap-6 px-4 py-8 sm:px-12">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-[13px] font-semibold tracking-wide text-muted uppercase">
            Project
          </div>
          <h1 className="m-0 font-serif text-[34px] font-semibold">{p.title}</h1>
          {p.summary && <p className="mt-1 mb-0 text-muted">{p.summary}</p>}
        </div>
        <button
          type="button"
          onClick={() => navigate(`/chat?project=${p.id}`)}
          className="min-h-11 cursor-pointer rounded-lg bg-accent px-4 font-semibold text-white"
        >
          New chat in this project
        </button>
      </div>

      <div className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(280px,1fr))]">
        <section className={card}>
          <h2 className="m-0 text-lg font-semibold">Chats</h2>
          {chats.data?.length === 0 && <p className="m-0 text-muted">No chats yet.</p>}
          {chats.data?.map((c) => (
            <Link
              key={c.id}
              to={`/chat/${c.id}`}
              className="flex min-h-11 items-center font-medium"
            >
              {c.title || "Untitled chat"}
            </Link>
          ))}
        </section>
        <section className={card}>
          <h2 className="m-0 text-lg font-semibold">Files, evidence and next steps</h2>
          <p className="m-0 text-muted">
            Files, disputed claims and suggested next steps will collect here as those parts of
            ArchiveHub arrive.
          </p>
        </section>
      </div>

      {p.is_owner && (
        <section className="flex flex-col gap-2 border-t border-line pt-4">
          {!confirming ? (
            <div>
              <button
                type="button"
                onClick={() => setConfirming(true)}
                className="min-h-11 cursor-pointer rounded-lg border border-warning bg-surface px-3 font-medium text-warning"
              >
                Delete project…
              </button>
            </div>
          ) : (
            <div
              role="alertdialog"
              aria-label="Confirm project deletion"
              className="flex flex-wrap items-center gap-3 rounded-lg border-2 border-warning bg-surface p-3.5"
            >
              <span className="flex-1">
                Delete <strong>{p.title}</strong> and all its chats? This can't be undone.
              </span>
              <button
                type="button"
                onClick={() => setConfirming(false)}
                className="min-h-11 cursor-pointer rounded-lg border border-control bg-surface px-3.5"
              >
                Keep it
              </button>
              <button
                type="button"
                onClick={remove}
                className="min-h-11 cursor-pointer rounded-lg bg-warning px-4 font-semibold text-white"
              >
                Delete project
              </button>
            </div>
          )}
          {error && (
            <p role="alert" className="m-0 text-warning">
              {error}
            </p>
          )}
        </section>
      )}
    </div>
  );
}
