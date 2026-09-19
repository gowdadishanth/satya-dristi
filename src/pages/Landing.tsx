import type { Route } from "../App";
import { Brand } from "../components/Shell";
import { Panel, Button, Eyebrow, Badge, Confidence } from "../components/ui";
import { SatImage, OverlayGrounding, ScaleTag, REGIONS } from "../components/SatImage";
import { capabilities, pipelineSteps, domains } from "../lib/data";
import {
  IconOptical, IconSar, IconChange, IconGrounding, IconArrow,
  IconEvidence, IconTrace, IconDownload, IconStatus, IconLayers,
} from "../components/icons";
import { authService } from "../lib/firebase";

const capIcon: Record<string, any> = {
  optical: IconOptical, sar: IconSar, change: IconChange, grounding: IconGrounding,
};

export function Landing({ navigate }: { navigate: (r: Route) => void }) {
  const handleSignIn = async () => {
    try {
      await authService.signInWithGoogle();
    } catch {
      // Dev analyst fallback handled automatically
    }
    navigate("dashboard");
  };

  return (
    <div className="app-bg min-h-screen">
      {/* Top nav */}
      <header className="sticky top-0 z-30 border-b border-border bg-card/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-6 px-5">
          <Brand />
          <nav className="ml-auto hidden items-center gap-6 text-sm text-muted-foreground md:flex">
            <a href="#capabilities" className="hover:text-foreground">Capabilities</a>
            <a href="#how" className="hover:text-foreground">How it works</a>
            <a href="#evidence" className="hover:text-foreground">Evidence</a>
            <a href="#workflows" className="hover:text-foreground">Workflows</a>
          </nav>
          <div className="ml-auto flex items-center gap-2 md:ml-0">
            <Button variant="ghost" size="sm" onClick={handleSignIn}>Sign in</Button>
            <Button variant="primary" size="sm" onClick={() => navigate("analyze")}>Open workspace</Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-5 pb-8 pt-14">
        <div className="grid items-center gap-10 lg:grid-cols-[1fr_1.05fr]">
          <div className="fade-up">
            <Eyebrow>Multimodal Earth Observation Intelligence</Eyebrow>
            <h1 className="mt-4 text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl">
              Ask questions.<br />Analyze satellite imagery.
            </h1>
            <p className="mt-5 max-w-lg text-[15px] leading-relaxed text-muted-foreground">
              Satya Dristi routes Earth observation queries to specialized vision models and returns
              evidence-grounded answers across optical, SAR, and temporal imagery.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Button variant="accent" onClick={() => navigate("analyze")} icon={<IconArrow className="h-4 w-4" />}>
                Open Analysis Workspace
              </Button>
              <Button variant="outline" onClick={() => document.getElementById("how")?.scrollIntoView({ behavior: "smooth" })}>
                View How It Works
              </Button>
            </div>
            <div className="mono mt-8 flex flex-wrap gap-x-5 gap-y-2 text-[11px] uppercase tracking-wide text-muted-foreground">
              <span>Optical / Multispectral</span>
              <span>SAR</span>
              <span>Bi-temporal</span>
              <span>GeoTIFF · TIFF</span>
            </div>
          </div>

          {/* Product preview */}
          <WorkspacePreview onOpen={() => navigate("analyze")} />
        </div>
      </section>

      {/* Capabilities */}
      <section id="capabilities" className="mx-auto max-w-6xl px-5 py-16">
        <SectionHead
          title="One workspace for multiple remote-sensing tasks"
          sub="A single agentic pipeline selects the specialist model each query requires."
        />
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {capabilities.map((c) => {
            const Icon = capIcon[c.icon];
            return (
              <Panel key={c.key} className="p-5">
                <span className="grid h-9 w-9 place-items-center rounded-md bg-accent/10 text-accent">
                  <Icon className="h-5 w-5" />
                </span>
                <h3 className="mt-4 text-[15px] font-semibold">{c.title}</h3>
                <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">{c.body}</p>
              </Panel>
            );
          })}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="border-y border-border bg-card/40">
        <div className="mx-auto max-w-6xl px-5 py-16">
          <SectionHead
            title="How Satya Dristi works"
            sub="Every query traverses the same auditable pipeline from ingestion to output."
          />
          <ol className="mt-8 grid gap-x-4 gap-y-6 sm:grid-cols-2 lg:grid-cols-4">
            {pipelineSteps.map((s, i) => (
              <li key={s} className="relative">
                <div className="flex items-center gap-2">
                  <span className="mono grid h-7 w-7 place-items-center rounded-md border border-border bg-card text-xs font-semibold text-accent">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  {i < pipelineSteps.length - 1 && (
                    <span className="hidden h-px flex-1 bg-border lg:block" />
                  )}
                </div>
                <p className="mt-3 text-[13.5px] font-medium leading-snug">{s}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* Evidence-grounded */}
      <section id="evidence" className="mx-auto max-w-6xl px-5 py-16">
        <SectionHead
          title="Built for evidence-grounded analysis"
          sub="Results are inseparable from the evidence, confidence, and trace that produced them."
        />
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { icon: IconEvidence, t: "Visual evidence", b: "Overlays, masks and change maps registered to the source imagery." },
            { icon: IconStatus, t: "Confidence score", b: "Derived from agreement between available specialist predictions." },
            { icon: IconTrace, t: "Execution trace", b: "Every stage, tool and parameter recorded for audit." },
            { icon: IconDownload, t: "Downloadable report", b: "Export a structured analysis package for the record." },
          ].map((x) => (
            <Panel key={x.t} className="p-5">
              <x.icon className="h-5 w-5 text-accent" />
              <h3 className="mt-3 text-[14px] font-semibold">{x.t}</h3>
              <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">{x.b}</p>
            </Panel>
          ))}
        </div>
      </section>

      {/* Workflows */}
      <section id="workflows" className="border-t border-border bg-card/40">
        <div className="mx-auto max-w-6xl px-5 py-16">
          <SectionHead title="Designed for real remote-sensing workflows" />
          <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {domains.map((d) => (
              <Panel key={d.title} className="flex items-start gap-3 p-4">
                <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-accent" />
                <div>
                  <h3 className="text-[14px] font-semibold">{d.title}</h3>
                  <p className="mt-0.5 text-[12.5px] leading-relaxed text-muted-foreground">{d.body}</p>
                </div>
              </Panel>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-6xl px-5 py-16">
        <Panel raised className="flex flex-col items-start justify-between gap-5 p-8 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">Analyze your first scene</h2>
            <p className="mt-1 text-[13.5px] text-muted-foreground">
              Upload imagery, ask a question, and inspect the full execution trace.
            </p>
          </div>
          <Button variant="accent" onClick={() => navigate("analyze")} icon={<IconArrow className="h-4 w-4" />}>
            Open Analysis Workspace
          </Button>
        </Panel>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="mx-auto grid max-w-6xl gap-8 px-5 py-12 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <Brand />
            <p className="mt-3 max-w-xs text-[12.5px] leading-relaxed text-muted-foreground">
              Interactive multimodal satellite intelligence for evidence-grounded analysis.
            </p>
          </div>
          <FooterCol title="Product" links={["Analysis Workspace", "Capabilities", "Reports", "Release notes"]} />
          <FooterCol title="Documentation" links={["Getting started", "Task reference", "Model catalog", "API"]} />
          <FooterCol
            title="Legal"
            links={["Privacy Policy", "Terms & Conditions", "Contact"]}
            onLink={(l) => {
              if (l === "Privacy Policy") navigate("privacy");
              if (l === "Terms & Conditions") navigate("terms");
            }}
          />
        </div>
        <div className="border-t border-border">
          <div className="mono mx-auto flex max-w-6xl flex-col gap-2 px-5 py-4 text-[11px] text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
            <span>© 2026 Satya Dristi. Demonstration interface — sample data.</span>
            <span>Multimodal Earth Observation Intelligence</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

function SectionHead({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-semibold tracking-tight sm:text-[28px]">{title}</h2>
      {sub && <p className="mt-2 text-[14px] leading-relaxed text-muted-foreground">{sub}</p>}
    </div>
  );
}

function FooterCol({ title, links, onLink }: { title: string; links: string[]; onLink?: (l: string) => void }) {
  return (
    <div>
      <Eyebrow>{title}</Eyebrow>
      <ul className="mt-3 space-y-2">
        {links.map((l) => (
          <li key={l}>
            <button
              onClick={() => onLink?.(l)}
              className="focus-ring rounded text-[13px] text-muted-foreground hover:text-foreground"
            >
              {l}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function WorkspacePreview({ onOpen }: { onOpen: () => void }) {
  return (
    <Panel raised className="overflow-hidden p-0 fade-up">
      <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className="mono text-[10.5px] uppercase tracking-wide text-muted-foreground">Analysis Workspace</span>
          <Badge tone="accent">Demo</Badge>
        </div>
        <div className="flex gap-1.5">
          <span className="h-2 w-2 rounded-full bg-border" />
          <span className="h-2 w-2 rounded-full bg-border" />
          <span className="h-2 w-2 rounded-full bg-border" />
        </div>
      </div>
      <div className="grid gap-3 p-3 sm:grid-cols-[1.4fr_1fr]">
        <SatImage bbox={REGIONS.urbanWater} className="min-h-[220px] rounded-md border border-border">
          <OverlayGrounding />
          <ScaleTag>Optical · grounding</ScaleTag>
        </SatImage>
        <div className="flex flex-col gap-3">
          <div>
            <Eyebrow>Query</Eyebrow>
            <p className="mt-1 text-[12.5px] leading-snug">
              "Highlight the water body referred to in the query."
            </p>
          </div>
          <div className="border-t border-border pt-2">
            <Eyebrow>Answer</Eyebrow>
            <p className="mt-1 text-[12.5px] leading-snug">
              Located a single contiguous reservoir in the central-west quadrant.
            </p>
          </div>
          <div className="mt-auto border-t border-border pt-3">
            <Confidence level="High" agreements={[]} compact />
          </div>
          <div className="flex items-center gap-1.5 rounded-md border border-border bg-muted/50 px-2 py-1.5">
            <IconLayers className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="mono text-[10px] uppercase tracking-wide text-muted-foreground">
              Optical · Grounding · Grid
            </span>
          </div>
        </div>
      </div>
      <button
        onClick={onOpen}
        className="focus-ring flex w-full items-center justify-center gap-2 border-t border-border py-2.5 text-[12.5px] font-medium text-accent hover:bg-accent/5"
      >
        Open in workspace <IconArrow className="h-3.5 w-3.5" />
      </button>
    </Panel>
  );
}
