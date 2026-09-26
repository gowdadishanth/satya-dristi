import { useEffect, useState, useRef, type ReactNode } from "react";
import {
  IconSatellite,
  IconDashboard,
  IconAnalyze,
  IconHistory,
  IconReports,
  IconSettings,
  IconMenu,
  IconClose,
} from "./icons";
import { StatDot, cn } from "./ui";
import type { Route } from "../App";
import { api, type SystemHealth } from "../lib/api";
import { authService, type UserProfile } from "../lib/firebase";

const nav: { key: Route; label: string; icon: (p: any) => ReactNode }[] = [
  { key: "dashboard", label: "Dashboard", icon: IconDashboard },
  { key: "analyze", label: "Analyze", icon: IconAnalyze },
  { key: "history", label: "History", icon: IconHistory },
  { key: "reports", label: "Reports", icon: IconReports },
  { key: "settings", label: "Settings", icon: IconSettings },
];

export function Brand({ onClick, small }: { onClick?: () => void; small?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group flex items-center gap-2.5 rounded-lg text-left transition-opacity focus-ring",
        onClick ? "cursor-pointer hover:opacity-90" : "cursor-default"
      )}
    >
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-[#4dbe55] to-[#79ed91] text-[#081a0c] shadow-xs font-bold transition-transform group-hover:scale-[1.02]">
        <IconSatellite className="h-[18px] w-[18px]" />
      </span>
      {!small && (
        <span className="flex flex-col justify-center">
          <span className="text-[14px] font-semibold tracking-tight text-foreground leading-tight">
            Satya Dristi
          </span>
          <span className="mono text-[9px] uppercase tracking-[0.12em] text-muted-foreground leading-tight mt-0.5">
            Earth Observation
          </span>
        </span>
      )}
    </button>
  );
}

import { AuthModal, GoogleIcon } from "./AuthModal";

export function Shell({
  route,
  navigate,
  title,
  status = "System ready",
  actions,
  children,
}: {
  route: Route;
  navigate: (r: Route) => void;
  title: string;
  status?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [user, setUser] = useState<UserProfile | null>(authService.getCurrentUser());
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let mounted = true;
    api.system.getHealth()
      .then((h) => {
        if (mounted) setHealth(h);
      })
      .catch(() => {});

    const unsubscribe = authService.onAuthStateChanged((u) => {
      if (mounted) setUser(u);
    });

    const handleOpenAuth = () => {
      setShowAuthModal(true);
      setShowUserMenu(false);
    };

    const handleClickOutside = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setShowUserMenu(false);
      }
    };

    window.addEventListener("open-auth-modal", handleOpenAuth);
    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      mounted = false;
      unsubscribe();
      window.removeEventListener("open-auth-modal", handleOpenAuth);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handleProfileClick = () => {
    if (user) {
      setShowUserMenu((prev) => !prev);
    } else {
      setShowAuthModal(true);
    }
  };

  const handleSignOut = () => {
    setShowUserMenu(false);
    authService.signOut();
  };

  const NavList = (
    <nav className="flex flex-col gap-1">
      {nav.map((n) => {
        const active = route === n.key;
        return (
          <button
            key={n.key}
            onClick={() => {
              navigate(n.key);
              setOpen(false);
            }}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors focus-ring",
              active
                ? "bg-primary text-primary-foreground font-medium"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <n.icon className="h-[18px] w-[18px] shrink-0" />
            {n.label}
          </button>
        );
      })}
    </nav>
  );

  return (
    <div className="app-bg min-h-screen">
      {/* Sidebar (desktop) */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-border bg-card/80 lg:flex">
        <div className="flex h-14 items-center px-4 border-b border-border">
          <Brand onClick={() => navigate("landing")} />
        </div>
        <div className="mt-3 flex-1 overflow-y-auto px-3">{NavList}</div>
        <div className="mt-auto p-3 border-t border-border/60">
          <div className="panel p-3">
            <div className="flex items-center gap-2">
              <StatDot tone={health?.status === "operational" ? "ok" : "warn"} />
              <span className="text-xs font-medium">
                {health?.status === "operational" ? "Backend operational" : "Connecting…"}
              </span>
            </div>
            <div className="mono mt-2 grid grid-cols-2 gap-x-2 gap-y-1 text-[10.5px] text-muted-foreground">
              <span>Compute</span>
              <span className="text-right text-foreground">{health?.preferred_device?.toUpperCase() || "CPU"}</span>
              <span>Queue</span>
              <span className="text-right text-foreground">{health?.active_jobs_count ?? 0} jobs</span>
              <span>Providers</span>
              <span className="text-right text-foreground">Copernicus</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-xs" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 flex w-64 flex-col border-r border-border bg-card">
            <div className="flex h-14 items-center justify-between px-4 border-b border-border">
              <Brand onClick={() => { navigate("landing"); setOpen(false); }} />
              <button className="focus-ring rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground" onClick={() => setOpen(false)} aria-label="Close menu">
                <IconClose className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-3 flex-1 overflow-y-auto px-3">{NavList}</div>
          </div>
        </div>
      )}

      {/* Main column */}
      <div className="lg:pl-60">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-card/85 px-4 backdrop-blur lg:px-6">
          <div className="flex items-center gap-2 lg:hidden">
            <button
              className="focus-ring rounded-md p-1.5 text-muted-foreground hover:bg-muted"
              onClick={() => setOpen(true)}
              aria-label="Open menu"
            >
              <IconMenu className="h-5 w-5" />
            </button>
            <Brand onClick={() => navigate("landing")} small />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-[15px] font-semibold text-foreground leading-tight">{title}</h1>
            <div className="flex items-center gap-1.5 mt-0.5">
              <StatDot tone="ok" />
              <span className="mono text-[10.5px] uppercase tracking-wide text-muted-foreground leading-none">{status}</span>
            </div>
          </div>
          <div className="ml-auto flex items-center gap-2">
            {actions}

            {user ? (
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={handleProfileClick}
                  className="focus-ring flex items-center gap-2 rounded-md border border-border px-2.5 py-1.5 hover:bg-muted transition-colors"
                  title={`Signed in as ${user.email}`}
                  aria-expanded={showUserMenu}
                >
                  {user.picture || user.photoURL ? (
                    <img src={user.picture || user.photoURL} alt="" className="h-6 w-6 rounded-full object-cover" />
                  ) : (
                    <span className="grid h-6 w-6 place-items-center rounded-full bg-primary/15 text-primary text-[11px] font-bold">
                      {(user.name || user.displayName || "SD").slice(0, 2).toUpperCase()}
                    </span>
                  )}
                  <span className="hidden text-xs font-semibold sm:block">
                    {user.displayName || user.name || user.email || "Google User"}
                  </span>
                  <svg className="h-3.5 w-3.5 text-muted-foreground" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
                  </svg>
                </button>

                {showUserMenu && (
                  <div className="absolute right-0 mt-2 w-72 rounded-xl border border-border bg-card p-4 shadow-xl z-50 animate-in fade-in zoom-in-95 duration-100">
                    <div className="flex items-center gap-3 border-b border-border pb-3">
                      <div className="grid h-10 w-10 place-items-center rounded-full bg-primary/15 text-primary font-bold text-sm">
                        {(user.displayName || user.name || user.email || "SD").slice(0, 2).toUpperCase()}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-xs font-semibold text-foreground">
                          {user.displayName || user.name || "Google User"}
                        </div>
                        <div className="truncate text-[11px] text-muted-foreground">
                          {user.email}
                        </div>
                        <div className="mono truncate text-[9.5px] text-muted-foreground mt-0.5">
                          UID: {user.uid}
                        </div>
                        <div className="mt-1 inline-flex items-center gap-1 rounded bg-ok/10 px-1.5 py-0.5 text-[10px] font-medium text-ok">
                          <span className="h-1.5 w-1.5 rounded-full bg-ok" />
                          <span>Google Authenticated</span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-3 space-y-1">
                      <button
                        onClick={() => {
                          setShowUserMenu(false);
                          setShowAuthModal(true);
                        }}
                        className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-xs font-medium text-foreground hover:bg-muted transition-colors text-left"
                      >
                        <GoogleIcon className="h-4 w-4" />
                        <span>Switch Google Account</span>
                      </button>

                      <button
                        onClick={handleSignOut}
                        className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-xs font-medium text-err hover:bg-err/10 transition-colors text-left"
                      >
                        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                        <span>Sign Out</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <button
                onClick={() => setShowAuthModal(true)}
                className="focus-ring flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5 hover:bg-muted transition-colors shadow-xs"
                title="Click to sign in with Google"
              >
                <GoogleIcon className="h-4 w-4" />
                <span className="text-xs font-semibold text-foreground">
                  Sign in with Google
                </span>
              </button>
            )}
          </div>
        </header>
        <main className="px-4 py-5 lg:px-6 lg:py-7">{children}</main>

        <AuthModal
          isOpen={showAuthModal}
          onClose={() => setShowAuthModal(false)}
          onSuccess={() => {
            setShowAuthModal(false);
          }}
        />
      </div>
    </div>
  );
}
