import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Surface = "default" | "neo";
export type Appearance = "light" | "dark" | "system";
export type Density = "comfortable" | "compact";

type ThemeState = {
  surface: Surface;
  appearance: Appearance;
  density: Density;
  setSurface: (s: Surface) => void;
  setAppearance: (a: Appearance) => void;
  setDensity: (d: Density) => void;
};

const Ctx = createContext<ThemeState | null>(null);

function prefersDark() {
  return typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [surface, setSurface] = useState<Surface>("default");
  const [appearance, setAppearance] = useState<Appearance>("light");
  const [density, setDensity] = useState<Density>("comfortable");

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("theme-default", "theme-neo");
    root.classList.add(`theme-${surface}`);
    const dark = appearance === "dark" || (appearance === "system" && prefersDark());
    root.classList.toggle("dark", dark);
    root.dataset.density = density;
  }, [surface, appearance, density]);

  return (
    <Ctx.Provider value={{ surface, appearance, density, setSurface, setAppearance, setDensity }}>
      {children}
    </Ctx.Provider>
  );
}

export function useTheme() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useTheme outside provider");
  return c;
}
