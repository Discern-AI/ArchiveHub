import { useQuery } from "@tanstack/react-query";
import { NavLink, useNavigate } from "react-router";
import { api } from "../lib/api";

const itemClass = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-11 items-center truncate rounded-lg px-2.5 text-rail-ink no-underline hover:text-rail-ink ${
    isActive ? "bg-rail-active" : "hover:bg-white/5"
  }`;

function SectionLabel({ children }: { children: string }) {
  return (
    <div className="px-2.5 text-xs font-semibold tracking-wide text-rail-label uppercase">
      {children}
    </div>
  );
}

export function Sidebar() {
  const navigate = useNavigate();
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const chats = useQuery({ queryKey: ["chats"], queryFn: () => api.chats() });
  const looseChats = (chats.data ?? []).filter((c) => !c.project_id).slice(0, 30);

  return (
    <nav
      aria-label="Projects and chats"
      className="flex w-full flex-col gap-[18px] overflow-y-auto bg-rail px-3.5 py-5 text-rail-ink"
    >
      <button
        type="button"
        onClick={() => navigate("/chat")}
        className="min-h-11 cursor-pointer rounded-lg bg-rail-ink font-semibold text-ink"
      >
        New chat
      </button>

      <div className="flex flex-col gap-1">
        <SectionLabel>Projects</SectionLabel>
        {projects.isError && <p className="px-2.5 text-sm text-rail-label">Couldn't load.</p>}
        {(projects.data ?? []).map((p) => (
          <NavLink key={p.id} to={`/projects/${p.id}`} className={itemClass}>
            {p.title}
          </NavLink>
        ))}
        <NavLink to="/projects/new" className={itemClass}>
          <span aria-hidden="true" className="mr-1.5">
            +
          </span>
          New project
        </NavLink>
      </div>

      <div className="flex flex-col gap-1">
        <SectionLabel>Chats</SectionLabel>
        {chats.isSuccess && looseChats.length === 0 && (
          <p className="px-2.5 text-sm text-rail-label">No chats yet.</p>
        )}
        {looseChats.map((c) => (
          <NavLink key={c.id} to={`/chat/${c.id}`} className={itemClass}>
            {c.title || "Untitled chat"}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
