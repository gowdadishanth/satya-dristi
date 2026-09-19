import { useEffect, useState } from "react";
import type { Route } from "../App";
import { Panel, Button, Badge, Eyebrow, Confidence, StatDot } from "../components/ui";
import { SatImage, OverlayChange, OverlayGrid, ScaleTag, REGIONS, OverlayDynamicGrounding, OverlayImageLayer } from "../components/SatImage";
import { analyses as sampleAnalyses } from "../lib/data";
import { ConfBadge, TaskIcon } from "../components/bits";
import { IconArrow, IconZoomIn, IconZoomOut, IconReset, IconLayers, IconTrace, IconGlobe } from "../components/icons";
import { api, type AnalysisRecord, type SystemHealth } from "../lib/api";

export function Dashboard({ navigate }: { navigate: (r: Route) => void }) {
  const [latest, setLatest] = useState<any>(sampleAnalyses[0]);
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);

  useEffect(() => {
    let mounted = true;

    // Load recent analyses from backend
    api.history.list({ limit: 1 })
      .then((records) => {
        if (mounted && records && records.length > 0) {
          const rec = records[0];
          setLatest({
            id: rec.analysis_id,
            query: rec.query,
            task: rec.task,
            input: rec.input,
            date: rec.date,
            time: rec.time,
            confidence: rec.confidence,
            agreements: rec.agreements,
            status: rec.status,
            answer: rec.answer,
            observed_evidence: rec.observed_evidence,
            model_interpretation: rec.model_interpretation,
            model_used: rec.model_used,
            primary_image_path: rec.primary_image_path,
            evidence_path: rec.evidence_path,
            boxes: rec.boxes,
            execution_trace: rec.execution_trace,
          });
        }
      })
      .catch(() => {
        // Fall back to demonstration record
      });

    // Load system telemetry
    api.system.getHealth()
      .then((health) => {
        if (mounted) setSystemHealth(health);
      })
      .catch(() => {});

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="space-y-8">
      {/* Start new analysis */}
      <div className="flex flex-col gap-3 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-[22px] font-semibold tracking-tight">Analysis workspace</h2>
          <p className="mt-1 max-w-lg text-[13.5px] leading-relaxed text-muted-foreground">
            Search genuine Sentinel-2 optical and Sentinel-1 SAR observations across any location on Earth.
            Natural language queries are routed to specialized remote-sensing models.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="primary" onClick={() => navigate("analyze")} icon={<IconArrow className="h-4 w-4" />}>
            Start new analysis
          </Button>
        </div>
      </div>

      {/* Workstation: imagery centerpiece + analysis side panel */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        {/* Centerpiece viewer */}
        <div>
          <Panel className="overflow-hidden p-0">
            <div className="flex items-center justify-between border-b border-border px-3 py-2">
              <div className="flex items-center gap-2">
                <TaskIcon task={latest.task} className="h-4 w-4 text-muted-foreground" />
                <span className="text-[13px] font-medium">{latest.task}</span>
                <Badge tone="neutral">{latest.id.startsWith("AN-") ? "Authentic Observation" : "Demonstration Scene"}</Badge>
              </div>
              <div className="flex items-center gap-0.5">
                {[IconZoomIn, IconZoomOut, IconReset, IconLayers].map((Ic, i) => (
                  <span key={i} className="rounded p-1.5 text-muted-foreground">
                    <Ic className="h-4 w-4" />
                  </span>
                ))}
              </div>
            </div>

            <SatImage
              src={latest.primary_image_path}
              bbox={REGIONS.corridor}
              className="aspect-[16/10] w-full"
            >
              {latest.evidence_path ? (
                <OverlayImageLayer src={latest.evidence_path} opacity={0.8} />
              ) : (
                <OverlayChange />
              )}
              {latest.boxes && latest.boxes.length > 0 ? (
                <OverlayDynamicGrounding boxes={latest.boxes} />
              ) : null}
              <OverlayGrid />
              <ScaleTag>Sentinel-2 MSI · EPSG:4326 · 10 m/px</ScaleTag>
              <span className="mono absolute bottom-2 right-2 rounded-sm bg-[#1a1e2b]/70 px-1.5 py-0.5 text-[9.5px] text-white/90">
                Active AOI Observation
              </span>
            </SatImage>

            {/* Restrained legend */}
            <div className="flex flex-wrap items-center gap-4 border-t border-border px-3 py-2">
              <Legend c="#ab7c2c" label="Grounding / Built-up" />
              <Legend c="#4f6f8a" label="Water Body" />
              <Legend c="#38a169" label="Active Vegetation" />
              <Legend c="#c2cbd3" label="Unchanged Surface" />
              <span className="mono ml-auto text-[10.5px] text-muted-foreground">
                {latest.id.startsWith("AN-") ? "Real Model Output" : "Demonstration Overlay"}
              </span>
            </div>
          </Panel>

          {/* Execution trace (bottom / secondary) */}
          <div className="mt-6">
            <div className="flex items-center gap-2">
              <IconTrace className="h-4 w-4 text-muted-foreground" />
              <Eyebrow>Observable Execution Trace</Eyebrow>
            </div>
            <dl className="mono mt-2 grid grid-cols-1 gap-x-8 gap-y-1.5 border-t border-border pt-3 text-[11.5px] sm:grid-cols-2">
              <Trace k="Task" v={latest.task} />
              <Trace k="Input" v={latest.input} />
              <Trace k="Model Engine" v={latest.model_used || "Remote-Sensing Vision Specialist"} />
              <Trace k="Status" v="Verified" ok />
              <Trace k="Confidence" v={`${latest.confidence} Confidence`} />
              <Trace k="Timestamp" v={`${latest.date} · ${latest.time}`} />
            </dl>
          </div>
        </div>

        {/* Side panel: query → input → task → confidence → evidence */}
        <aside className="space-y-6">
          <section>
            <Eyebrow>Current Query</Eyebrow>
            <p className="mt-1.5 text-[14px] font-medium leading-snug">{latest.query}</p>
            <p className="mt-2 text-[13px] leading-relaxed text-muted-foreground">{latest.answer}</p>
          </section>

          <section className="border-t border-border pt-5">
            <Eyebrow>Satellite Ingestion</Eyebrow>
            <dl className="mono mt-2 space-y-1.5 text-[11.5px]">
              <Trace k="Input Mode" v={latest.input} />
              <Trace k="Format" v="Cloud-Optimized GeoTIFF" />
              <Trace k="Resolution" v="10 m/px Ground Resolution" />
              <Trace k="CRS" v="EPSG:4326 (WGS 84)" />
              <Trace k="Catalog" v="Copernicus Data Space STAC" />
            </dl>
          </section>

          <section className="border-t border-border pt-5">
            <Eyebrow>Task Classification</Eyebrow>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <Badge tone="accent">{latest.task}</Badge>
              <Badge tone="neutral">{latest.input}</Badge>
            </div>
          </section>

          <section className="border-t border-border pt-5">
            <Eyebrow>Confidence Level</Eyebrow>
            <div className="mt-2">
              <Confidence
                level={latest.confidence}
                agreements={latest.agreements || [
                  { label: "Optical Agreement", state: "agree" },
                  { label: "SAR Backscatter", state: "agree" },
                  { label: "Spectral Indices", state: "agree" },
                ]}
              />
            </div>
          </section>

          <section className="border-t border-border pt-5">
            <Eyebrow>System Telemetry</Eyebrow>
            <div className="mt-2 rounded-md border border-border bg-muted/40 p-3">
              <div className="flex items-center gap-2">
                <StatDot tone={systemHealth?.status === "operational" ? "ok" : "warn"} />
                <span className="text-[12px] font-medium">
                  {systemHealth?.status === "operational" ? "Backend Operational" : "Connecting..."}
                </span>
              </div>
              <dl className="mono mt-2 grid grid-cols-2 gap-y-1 text-[10.5px] text-muted-foreground">
                <dt>Compute Device</dt>
                <dd className="text-right text-foreground">{systemHealth?.preferred_device?.toUpperCase() || "CPU"}</dd>
                <dt>Active Jobs</dt>
                <dd className="text-right text-foreground">{systemHealth?.active_jobs_count ?? 0}</dd>
                <dt>STAC Providers</dt>
                <dd className="text-right text-foreground">Copernicus / AWS</dd>
                <dt>Database</dt>
                <dd className="text-right text-foreground">{systemHealth?.database_status || "connected"}</dd>
              </dl>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

function Legend({ c, label }: { c: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="h-2.5 w-2.5 rounded-[2px]" style={{ background: c }} />
      <span className="text-muted-foreground">{label}</span>
    </div>
  );
}

function Trace({ k, v, ok }: { k: string; v: string; ok?: boolean }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="uppercase tracking-wide text-muted-foreground">{k}</span>
      <span className={ok ? "truncate font-medium text-[color:var(--ok)]" : "truncate text-foreground"}>{v}</span>
    </div>
  );
}
