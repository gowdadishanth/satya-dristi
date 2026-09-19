import { useEffect, useState, type ReactNode } from "react";
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
    <button onClick={onClick} className="flex items-center gap-2.5 focus-ring rounded-md">
      <span className="grid h-8 w-8 place-items-center rounded-md bg-primary text-primary-foreground">
        <IconSatellite className="h-[18px] w-[18px]" />
      </span>
      {!small && (
        <span className="flex flex-col items-start leading-none">
          <span className="text-[15px] font-semibold tracking-tight">Satya Dristi</span>
          <span className="mono text-[9.5px] uppercase tracking-[0.14em] text-muted-foreground">
            Earth Observation Intelligence
          </span>
        </span>
      )}
    </button>
  );
}

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

    return () => {
      mounted = false;
      unsubscribe();
    };
  }, []);

  const handleAuthAction = async () => {
    if (user) {
      authService.signOut();
    } else {
      try {
        await authService.signInWithGoogle();
      } catch {
        // Fallback already handled
      }
    }
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
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-border bg-card/80 px-3 py-4 lg:flex">
        <div className="px-2">
          <Brand onClick={() => navigate("landing")} />
        </div>
        <div className="mt-6 px-2">{NavList}</div>
        <div className="mt-auto px-2">
          <div className="panel px-3 py-3">
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
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-64 border-r border-border bg-card px-3 py-4">
            <div className="flex items-center justify-between px-2">
              <Brand onClick={() => { navigate("landing"); setOpen(false); }} />
              <button className="focus-ring rounded p-1" onClick={() => setOpen(false)} aria-label="Close menu">
                <IconClose />
              </button>
            </div>
            <div className="mt-6 px-2">{NavList}</div>
          </div>
        </div>
      )}

      {/* Main column */}
      <div className="lg:pl-60">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-card/85 px-4 backdrop-blur lg:px-6">
          <button
            className="focus-ring rounded-md p-1.5 text-muted-foreground hover:bg-muted lg:hidden"
            onClick={() => setOpen(true)}
            aria-label="Open menu"
          >
            <IconMenu />
          </button>
          <div className="min-w-0">
            <h1 className="truncate text-[15px] font-semibold leading-tight">{title}</h1>
            <div className="flex items-center gap-1.5">
              <StatDot tone="ok" />
              <span className="mono text-[10.5px] uppercase tracking-wide text-muted-foreground">{status}</span>
            </div>
          </div>
          <div className="ml-auto flex items-center gap-2">
            {actions}
            <button
              onClick={handleAuthAction}
              className="focus-ring flex items-center gap-2 rounded-md border border-border px-2 py-1.5 hover:bg-muted"
              title={user ? `Signed in as ${user.email}. Click to sign out.` : "Click to sign in with Google"}
            >
              {user?.picture || user?.photoURL ? (
                <img src={user.picture || user.photoURL} alt="" className="h-6 w-6 rounded object-cover" />
              ) : (
                <span className="grid h-6 w-6 place-items-center rounded bg-accent text-[11px] font-semibold text-accent-foreground">
                  {user ? ((user.name || user.displayName) ? (user.name || user.displayName)!.slice(0, 2).toUpperCase() : "US") : "SD"}
                </span>
              )}
              <span className="hidden text-xs font-medium sm:block">
                {user ? user.name || user.displayName || "Analyst" : "Sign In"}
              </span>
            </button>
          </div>
        </header>
        <main className="px-4 py-5 lg:px-6 lg:py-7">{children}</main>
      </div>
    </div>
  );
}
