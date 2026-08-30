import { Link, NavLink, Outlet } from "react-router-dom";
import { Logo } from "./Logo";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-lg px-3 py-2 text-sm font-medium transition ${
    isActive ? "bg-white/90 text-accent shadow-sm ring-1 ring-slate-200/80" : "text-slate-600 hover:bg-white/60 hover:text-ink"
  }`;

export function Layout() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-50 border-b border-slate-200/60 bg-[#eef2f7]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link to="/universe" className="group flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white p-1.5 shadow-sm ring-1 ring-slate-200/80 transition group-hover:shadow-md group-hover:scale-105">
              <Logo className="h-full w-full drop-shadow-sm" />
            </div>
            <div>
              <span className="font-display text-xl font-bold tracking-wider text-ink group-hover:text-accent">
                PRISM
              </span>
              <p className="text-[10px] leading-tight text-slate-500 font-medium sm:text-[11px]">
                Portfolio Risk &amp; Investment Screening Model
              </p>
            </div>
          </Link>
          <nav className="flex flex-wrap items-center gap-1">
            <NavLink to="/universe" className={linkClass}>
              Rankings
            </NavLink>
            <NavLink to="/sectors" className={linkClass}>
              Sectors
            </NavLink>
            <NavLink to="/recommendations" className={linkClass}>
              For you
            </NavLink>
            <NavLink to="/" className={linkClass} end>
              Profile
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-10">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200/60 py-6 text-center text-xs text-slate-500">
        Scores are model-generated for research — not investment advice.
      </footer>
    </div>
  );
}
