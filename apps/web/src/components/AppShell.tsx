import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { signOut } from "../lib/auth";
import { Sidebar } from "./Sidebar";

const TOP_NAV = [
  { to: "/search", label: "Search" },
  { to: "/map", label: "Map" },
  { to: "/explain", label: "Explain" },
  { to: "/forums", label: "Forums" },
  { to: "/archive", label: "Archive" },
];

const navClass = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-11 items-center rounded-lg px-3.5 font-medium text-rail-ink no-underline hover:text-rail-ink ${
    isActive ? "bg-rail-active" : "hover:bg-white/5"
  }`;

function AccountMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const qc = useQueryClient();

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", esc);
    };
  }, [open]);

  const go = (to: string) => {
    setOpen(false);
    navigate(to);
  };

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen(!open)}
        className="min-h-11 cursor-pointer rounded-lg border border-[#47665e] bg-transparent px-3.5 font-medium text-rail-ink"
      >
        Account
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 top-[50px] z-40 flex w-60 flex-col gap-0.5 rounded-lg border border-line bg-surface p-2 text-ink shadow-[0_8px_24px_rgba(14,38,33,0.22)]"
        >
          {[
            ["/homepage", "Homepage"],
            ["/profile", "Profile"],
            ["/settings", "Settings"],
          ].map(([to, label]) => (
            <button
              key={to}
              role="menuitem"
              type="button"
              onClick={() => go(to)}
              className="min-h-11 cursor-pointer rounded-lg px-2.5 text-left font-medium hover:bg-tint"
            >
              {label}
            </button>
          ))}
          <hr className="my-1 border-line-soft" />
          <button
            role="menuitem"
            type="button"
            onClick={async () => {
              await signOut();
              qc.clear();
              navigate("/signin");
            }}
            className="min-h-11 cursor-pointer rounded-lg px-2.5 text-left font-medium hover:bg-tint"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

export function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  // Close the phone menu whenever the page changes.
  const [lastPath, setLastPath] = useState(location.pathname);
  if (lastPath !== location.pathname) {
    setLastPath(location.pathname);
    setMenuOpen(false);
  }

  return (
    <div className="flex h-full min-h-screen flex-col">
      <header className="relative z-30 flex flex-wrap items-center justify-between gap-x-5 gap-y-1.5 bg-bar px-3.5 py-2 text-rail-ink">
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(!menuOpen)}
            className="flex size-11 cursor-pointer items-center justify-center rounded-lg text-rail-ink md:hidden"
          >
            <svg
              aria-hidden="true"
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <path d="M4 7h16M4 12h16M4 17h16" />
            </svg>
          </button>
          <NavLink
            to="/chat"
            className="min-h-11 px-2 font-serif text-2xl font-semibold text-rail-ink no-underline hover:text-rail-ink"
          >
            ArchiveHub
          </NavLink>
        </div>
        <div className="flex flex-wrap items-center gap-1">
          <nav aria-label="Main" className="flex flex-wrap gap-1">
            {TOP_NAV.map((item) => (
              <NavLink key={item.to} to={item.to} className={navClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>
          <AccountMenu />
        </div>
      </header>

      <div className="relative flex min-h-0 flex-1">
        <div
          className={`${
            menuOpen ? "fixed inset-0 top-[60px] z-20 flex" : "hidden"
          } w-full md:static md:flex md:w-[260px] md:shrink-0`}
        >
          <Sidebar />
        </div>
        <main className="flex min-w-0 flex-1 flex-col">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
