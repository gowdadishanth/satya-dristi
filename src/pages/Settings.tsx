import { Panel, Button, Eyebrow, cn } from "../components/ui";
import { useTheme, type Surface, type Appearance, type Density } from "../lib/theme";
import { IconCheck } from "../components/icons";

const surfaces: { key: Surface; name: string; desc: string }[] = [
  { key: "default", name: "Professional", desc: "Editorial / geospatial. Flat surfaces, subtle borders, generous whitespace." },
  { key: "neo", name: "NeoMorphism", desc: "Optional alternative. Subtle raised surfaces and tactile controls." },
];

export function Settings() {
  const { surface, setSurface, appearance, setAppearance, density, setDensity } = useTheme();

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Appearance */}
      <section>
        <SectionTitle n="01" title="Appearance" sub="Choose the interface treatment. All themes share the same information architecture and functionality." />
        <div className="mt-4">
          <Eyebrow>Theme</Eyebrow>
          <div className="mt-2 grid gap-4 sm:grid-cols-2">
            {surfaces.map((s) => (
              <button
                key={s.key}
                onClick={() => setSurface(s.key)}
                className={cn(
                  "focus-ring rounded-lg border p-1 text-left transition-colors",
                  surface === s.key ? "border-accent ring-1 ring-accent" : "border-border hover:border-muted-foreground/40",
                )}
              >
                <ThemePreview surface={s.key} />
                <div className="p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-[13.5px] font-semibold">{s.name}</span>
                    {surface === s.key && (
                      <span className="ml-auto grid h-5 w-5 place-items-center rounded-full bg-accent text-accent-foreground">
                        <IconCheck className="h-3 w-3" />
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-[11.5px] leading-relaxed text-muted-foreground">{s.desc}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <Panel className="p-4">
            <Eyebrow>Appearance mode</Eyebrow>
            <Segmented<Appearance>
              value={appearance}
              onChange={setAppearance}
              options={[["light", "Light"], ["dark", "Dark"], ["system", "System"]]}
            />
          </Panel>
          <Panel className="p-4">
            <Eyebrow>Density</Eyebrow>
            <Segmented<Density>
              value={density}
              onChange={setDensity}
              options={[["comfortable", "Comfortable"], ["compact", "Compact"]]}
            />
          </Panel>
        </div>
      </section>

      {/* Analysis preferences */}
      <section>
        <SectionTitle n="02" title="Analysis Preferences" sub="Defaults applied to new analyses." />
        <Panel className="mt-4 divide-y divide-border p-0">
          <Toggle label="Auto-select specialist tools" desc="Let the agent choose models based on the query." on />
          <Toggle label="Require input compatibility check" desc="Validate CRS, format and co-registration before inference." on />
          <Toggle label="Attach execution trace to reports" desc="Include the full auditable trace in exports." on />
          <Toggle label="Flag low-confidence results" desc="Surface uncertainty when specialist predictions disagree." on />
        </Panel>
      </section>

      {/* System / Privacy / About */}
      <section>
        <SectionTitle n="03" title="System" />
        <Panel className="mt-4 divide-y divide-border p-0">
          <KV k="Region" v="ap-south (demonstration)" />
          <KV k="Default export format" v="PDF · GeoTIFF overlays" />
          <KV k="Models online" v="6 / 6" />
        </Panel>
      </section>

      <section>
        <SectionTitle n="04" title="Privacy" />
        <Panel className="mt-4 divide-y divide-border p-0">
          <Toggle label="Retain uploaded imagery after analysis" desc="Store source scenes for reproducibility." />
          <Toggle label="Include query text in stored history" desc="Keep queries for search and audit." on />
        </Panel>
      </section>

      <section>
        <SectionTitle n="05" title="About" />
        <Panel className="mt-4 p-4">
          <p className="text-[13px] font-medium">Satya Dristi — Multimodal Earth Observation Intelligence</p>
          <p className="mono mt-1 text-[11px] text-muted-foreground">Demonstration build · v0.9.0 · sample data only</p>
          <div className="mt-3 flex gap-2">
            <Button size="sm" variant="outline">Documentation</Button>
            <Button size="sm" variant="outline">Model catalog</Button>
          </div>
        </Panel>
      </section>
    </div>
  );
}

function SectionTitle({ n, title, sub }: { n: string; title: string; sub?: string }) {
  return (
    <div className="flex items-baseline gap-3 border-b border-border pb-3">
      <span className="mono text-[11px] text-accent">{n}</span>
      <div>
        <h2 className="text-[16px] font-semibold tracking-tight">{title}</h2>
        {sub && <p className="mt-0.5 text-[12.5px] leading-relaxed text-muted-foreground">{sub}</p>}
      </div>
    </div>
  );
}

function Segmented<T extends string>({ value, onChange, options }: { value: T; onChange: (v: T) => void; options: [T, string][] }) {
  return (
    <div className="mt-2 inline-flex w-full gap-1 rounded-md border border-border p-1">
      {options.map(([v, label]) => (
        <button
          key={v}
          onClick={() => onChange(v)}
          className={cn(
            "flex-1 rounded px-3 py-1.5 text-[12.5px] font-medium transition-colors focus-ring",
            value === v ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted",
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function Toggle({ label, desc, on = false }: { label: string; desc: string; on?: boolean }) {
  const id = label.replace(/\s/g, "");
  return (
    <label htmlFor={id} className="flex cursor-pointer items-start justify-between gap-4 p-4">
      <span>
        <span className="block text-[13px] font-medium">{label}</span>
        <span className="mt-0.5 block text-[12px] leading-relaxed text-muted-foreground">{desc}</span>
      </span>
      <span className="mt-0.5">
        <input id={id} type="checkbox" defaultChecked={on} className="peer sr-only" />
        <span className="relative block h-5 w-9 rounded-full bg-muted-foreground/30 transition-colors peer-checked:bg-accent peer-focus-visible:ring-2 peer-focus-visible:ring-ring after:absolute after:left-0.5 after:top-0.5 after:h-4 after:w-4 after:rounded-full after:bg-white after:transition-transform after:content-[''] peer-checked:after:translate-x-4" />
      </span>
    </label>
  );
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between gap-4 p-4">
      <span className="text-[13px] font-medium">{k}</span>
      <span className="mono text-[11.5px] text-muted-foreground">{v}</span>
    </div>
  );
}

/* Miniature live preview of each theme, using the real palette */
function ThemePreview({ surface }: { surface: Surface }) {
  const card =
    surface === "neo"
      ? "bg-[#f6f3ed] rounded-xl border border-white/60 shadow-[3px_3px_7px_rgba(60,68,95,0.16),-3px_-3px_7px_rgba(255,255,255,0.85)]"
      : "bg-white rounded-md border border-[#e2ded4]";
  return (
    <div className="rounded-md bg-[#f6f3ed] p-3">
      <div className="flex gap-2">
        <div className={cn("h-9 flex-1", card)} />
        <div className="h-9 w-9 rounded-md bg-[#313851]" />
      </div>
      <div className={cn("mt-2 h-6", card)} />
    </div>
  );
}
