import { useEffect, useState } from "react";
import { ThemeProvider } from "./lib/theme";
import { Shell } from "./components/Shell";
import { Landing } from "./pages/Landing";
import { Dashboard } from "./pages/Dashboard";
import { Analyze } from "./pages/Analyze";
import { History } from "./pages/History";
import { Reports } from "./pages/Reports";
import { Settings } from "./pages/Settings";
import { Legal } from "./pages/Legal";
import { Button } from "./components/ui";
import { IconArrow } from "./components/icons";

export type Route =
  | "landing" | "dashboard" | "analyze" | "history" | "reports" | "settings" | "privacy" | "terms";

const titles: Record<Route, { title: string; status: string }> = {
  landing: { title: "Satya Dristi", status: "System ready" },
  dashboard: { title: "Dashboard", status: "System ready" },
  analyze: { title: "Analysis Workspace", status: "System ready" },
  history: { title: "Analysis History", status: "System ready" },
  reports: { title: "Reports", status: "System ready" },
  settings: { title: "Settings", status: "System ready" },
  privacy: { title: "Privacy Policy", status: "Legal · demo" },
  terms: { title: "Terms & Conditions", status: "Legal · demo" },
};

export default function App() {
  const [route, setRoute] = useState<Route>("landing");

  const navigate = (r: Route) => {
    setRoute(r);
    window.scrollTo({ top: 0 });
  };

  useEffect(() => {
    document.title = `Satya Dristi · ${titles[route].title}`;
  }, [route]);

  return (
    <ThemeProvider>
      {route === "landing" ? (
        <Landing navigate={navigate} />
      ) : (
        <Shell
          route={route}
          navigate={navigate}
          title={titles[route].title}
          status={titles[route].status}
          actions={
            route === "analyze" ? undefined : (
              <Button size="sm" variant="accent" icon={<IconArrow className="h-3.5 w-3.5" />} onClick={() => navigate("analyze")}>
                New analysis
              </Button>
            )
          }
        >
          {route === "dashboard" && <Dashboard navigate={navigate} />}
          {route === "analyze" && <Analyze />}
          {route === "history" && <History navigate={navigate} />}
          {route === "reports" && <Reports />}
          {route === "settings" && <Settings />}
          {route === "privacy" && <Legal kind="privacy" />}
          {route === "terms" && <Legal kind="terms" />}
        </Shell>
      )}
    </ThemeProvider>
  );
}
