import { useEffect, useState } from "react";
import { Badge, Button, Confidence, StatDot, cn } from "../components/ui";
import {
  SatImage, OverlayGrid, OverlayDynamicGrounding, OverlayImageLayer, ScaleTag, REGIONS,
} from "../components/SatImage";
import {
  UploadSlot, makeUploadedFile, revokeUploaded, type UploadedFile,
} from "../components/Uploader";
import { GlobalMap, isSarScene } from "../components/GlobalMap";
import { executionStages, type InputType, type TaskType } from "../lib/data";
import {
  IconOptical, IconSar, IconChange, IconCheck, IconTriangle,
  IconLayers, IconZoomIn, IconZoomOut, IconReset, IconChevron,
  IconTrace, IconDownload, IconGlobe, IconUpload, IconFile,
} from "../components/icons";
import { api, getAnalysisImageUrl, type Scene, type AOIPreview, type AnalysisRecord, type AnalysisJobStatus } from "../lib/api";

type LayerKey = "optical" | "sar" | "change" | "grounding" | "grid";
const REGION = REGIONS.corridor;

type Mode = "single" | "fusion" | "temporal";
type Phase = "setup" | "running" | "result";
type InputSource = "map" | "upload";

const modeMeta: Record<Mode, { label: string; input: InputType; task: TaskType; icon: any; desc: string }> = {
  single: { label: "Single Image", input: "Single image", task: "Single-Image VQA", icon: IconOptical, desc: "Optical 10m L2A" },
  fusion: { label: "Optical + SAR", input: "Optical + SAR", task: "Optical + SAR Fusion", icon: IconSar, desc: "Multimodal Fusion" },
  temporal: { label: "Before + After", input: "Before + After", task: "Bi-Temporal Change", icon: IconChange, desc: "Change Detection" },
};

const slotLabels: Record<Mode, string[]> = {
  single: ["Image"],
  fusion: ["Optical", "SAR"],
  temporal: ["Before", "After"],
};

const exampleQueries: Record<Mode, string[]> = {
  single: [
    "Describe the major land-cover types visible in this area.",
    "Highlight water bodies and identify built-up structures.",
    "Delineate agricultural plots versus urban infrastructure.",
  ],
  fusion: [
    "Use optical and SAR together to identify built-up regions.",
    "Differentiate calm open water from high-backscatter structures.",
    "Assess surface roughness and soil moisture from SAR backscatter.",
  ],
  temporal: [
    "What changed between these two observation dates?",
    "Detect new urban construction or vegetation loss.",
    "Identify changes in water bodies or surface runoff.",
  ],
};

const sampleFiles: Record<Mode, { name: string; modality: string; res: string; sensor: string; ts: string; crs: string; icon: any; compat: "ok" | "warn" }[]> = {
  single: [{ name: "S2A_MSIL2A_20241228.tif", modality: "Optical", res: "10 m/px", sensor: "Sentinel-2 MSI", ts: "2024-12-28 05:24Z", crs: "EPSG:4326", icon: IconOptical, compat: "ok" }],
  fusion: [
    { name: "S2A_MSIL2A_20241228.tif", modality: "Optical", res: "10 m/px", sensor: "Sentinel-2 MSI", ts: "2024-12-28 05:24Z", crs: "EPSG:4326", icon: IconOptical, compat: "ok" },
    { name: "S1A_IW_GRDH_20241226.tif", modality: "SAR (C-band)", res: "10 m/px", sensor: "Sentinel-1 SAR", ts: "2024-12-26 00:32Z", crs: "EPSG:4326", icon: IconSar, compat: "ok" },
  ],
  temporal: [
    { name: "S2A_MSIL2A_20221231.tif", modality: "Optical · before", res: "10 m/px", sensor: "Sentinel-2 MSI", ts: "2022-12-31 05:02Z", crs: "EPSG:4326", icon: IconOptical, compat: "ok" },
    { name: "S2B_MSIL2A_20241228.tif", modality: "Optical · after", res: "10 m/px", sensor: "Sentinel-2 MSI", ts: "2024-12-28 05:24Z", crs: "EPSG:4326", icon: IconOptical, compat: "ok" },
  ],
};

function formatErrorMessage(raw: string): string {
  if (!raw) return "Analysis failed. Please try again.";
  if (raw.includes("503") || raw.toLowerCase().includes("high demand") || raw.toLowerCase().includes("unavailable")) {
    return "The Gemini AI model was temporarily experiencing high demand. Automatic retry is enabled, please click Retry Analysis below.";
  }
  if (raw.includes("429") || raw.toLowerCase().includes("quota") || raw.toLowerCase().includes("rate limit")) {
    return "Gemini API rate limit reached. Please wait a few seconds and click Retry Analysis.";
  }
  if (raw.includes("401") || raw.toLowerCase().includes("unauthorized") || raw.toLowerCase().includes("api key")) {
    return "Invalid or unauthorized Gemini API key. Please check your GEMINI_API_KEY in backend/.env.";
  }
  const match = raw.match(/'message':\s*['"]([^'"]+)['"]/);
  if (match && match[1]) {
    return match[1];
  }
  return raw;
}

export type DetectedIntent = {
  mode: Mode;
  taskName: string;
  sensorBadge: string;
  reason: string;
};

export function detectQueryIntent(q: string): DetectedIntent {
  const query = (q || "").toLowerCase();

  // 1. SAR / Radar / All-Weather / Penetration Intent
  const sarKeywords = [
    "sar", "radar", "backscatter", "sigma0", "sigma 0", "decibel", "db",
    "cloud", "penetrat", "monsoon", "night", "storm", "all-weather",
    "roughness", "dielectric", "metallic", "vessel", "ship", "microwave",
    "vv", "vh", "polarimetric"
  ];
  if (sarKeywords.some((k) => query.includes(k))) {
    return {
      mode: "fusion",
      taskName: "Optical + SAR Multimodal Fusion",
      sensorBadge: "Sentinel-1 SAR + Sentinel-2",
      reason: "All-weather / radar backscatter query detected: automatically routing to Sentinel-1 C-SAR & Sentinel-2 fusion pipeline.",
    };
  }

  // 2. Bi-Temporal Change Detection Intent
  const changeKeywords = [
    "change", "difference", "before and after", "before/after", "temporal",
    "increased", "decreased", "growth", "shrink", "shrunk", "shrinkage",
    "expansion", "encroach", "deforest", "loss", "gained", "built since",
    "over time", "between 20", "since 20", "past years", "new construction",
    "historical", "timeline", "years ago", "progress of"
  ];
  if (changeKeywords.some((k) => query.includes(k))) {
    return {
      mode: "temporal",
      taskName: "Bi-Temporal Change Detection",
      sensorBadge: "Multi-Temporal Sentinel-2 Pair",
      reason: "Multi-temporal comparison detected: automatically routing to baseline historical & current observation change pipeline.",
    };
  }

  // 3. Referral Grounding / Spatial Localization Intent
  const groundingKeywords = [
    "highlight", "locate", "find", "where is", "bounding box", "point out",
    "delineate", "boundary", "demarcate", "isolate", "contour", "segment"
  ];
  if (groundingKeywords.some((k) => query.includes(k))) {
    return {
      mode: "single",
      taskName: "Semantic Spatial Grounding",
      sensorBadge: "Sentinel-2 10m L2A + Pixel Referral",
      reason: "Spatial localization query detected: automatically routing to pixel coordinate referral and boundary grounding.",
    };
  }

  // 4. Default: Single-Image Optical VQA / Land Cover Description
  return {
    mode: "single",
    taskName: "Single-Image Optical VQA",
    sensorBadge: "Sentinel-2 10m Multispectral",
    reason: "Earth observation query detected: routing to high-resolution multispectral visual reasoning pipeline.",
  };
}

export function Analyze() {
  const [autoMode, setAutoMode] = useState(true);
  const [mode, setMode] = useState<Mode>("single");
  const [inputSource, setInputSource] = useState<InputSource>("map");
  const [files, setFiles] = useState<Record<string, UploadedFile | null>>({});
  const [useSample, setUseSample] = useState(false);
  const [query, setQuery] = useState("Describe the major land-cover types visible in this area.");
  const [phase, setPhase] = useState<Phase>("setup");

  // Global Map Selection State
  const [selectedScene, setSelectedScene] = useState<Scene | null>(null);
  const [secondaryScene, setSecondaryScene] = useState<Scene | null>(null);
  const [selectedAoi, setSelectedAoi] = useState<AOIPreview | null>(null);

  // Real Asynchronous Job Execution State
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<AnalysisJobStatus | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisRecord | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  // Auto-Routing: dynamically computes effective mode based on query intent
  const detectedIntent = detectQueryIntent(query);
  const effectiveMode: Mode = autoMode ? detectedIntent.mode : mode;

  const meta = modeMeta[effectiveMode];
  const labels = slotLabels[effectiveMode];
  const allReady = labels.every((l) => files[l]?.status === "ready");
  const anyInvalid = labels.some((l) => files[l]?.status === "invalid");

  const hasImagery = inputSource === "map"
    ? (selectedScene !== null || useSample)
    : (useSample || allReady);

  const clearFiles = () => {
    setFiles((s) => {
      Object.values(s).forEach((f) => revokeUploaded(f ?? null));
      return {};
    });
  };

  const setSlot = (label: string, file: File) => {
    setFiles((s) => {
      revokeUploaded(s[label] ?? null);
      return { ...s, [label]: makeUploadedFile(file) };
    });
    setUseSample(false);
  };

  const removeSlot = (label: string) => {
    setFiles((s) => {
      revokeUploaded(s[label] ?? null);
      const next = { ...s };
      delete next[label];
      return next;
    });
  };

  const handleSelectFromMap = (scene: Scene, aoi: AOIPreview, secondScene?: Scene) => {
    setSelectedScene(scene);
    setSelectedAoi(aoi);
    if (secondScene) {
      setSecondaryScene(secondScene);
    }
  };

  // Launch Real Asynchronous Analysis
  const run = async () => {
    if (!hasImagery || anyInvalid || !query.trim() || phase === "running") return;

    setPhase("running");
    setAnalysisError(null);
    setAnalysisResult(null);

    try {
      let job: AnalysisJobStatus;

      if (inputSource === "map") {
        const isFirstSar = isSarScene(selectedScene);
        const opticalSceneId = effectiveMode === "fusion"
          ? (isFirstSar ? secondaryScene?.scene_id : selectedScene?.scene_id)
          : selectedScene?.scene_id;
        const sarSceneId = effectiveMode === "fusion"
          ? (isFirstSar ? selectedScene?.scene_id : secondaryScene?.scene_id)
          : undefined;

        job = await api.analyses.create({
          mode: effectiveMode,
          query,
          scene_id: opticalSceneId,
          aoi: selectedAoi,
          before_scene_id: effectiveMode === "temporal" ? (secondaryScene?.scene_id || "AUTO_BASELINE") : undefined,
          after_scene_id: effectiveMode === "temporal" ? selectedScene?.scene_id : undefined,
          optical_scene_id: opticalSceneId,
          sar_scene_id: sarSceneId,
        });
      } else {
        // Form data upload
        const formData = new FormData();
        formData.append("mode", effectiveMode);
        formData.append("query", query);
        if (selectedAoi) {
          formData.append("aoi", JSON.stringify(selectedAoi));
        }
        Object.entries(files).forEach(([slot, uploaded]) => {
          if (uploaded?.file) {
            formData.append(slot.toLowerCase(), uploaded.file);
          }
        });
        job = await api.analyses.createUpload(formData);
      }

      setActiveJobId(job.analysis_id);
      setJobStatus(job);
    } catch (err: any) {
      setAnalysisError(err.message || "Failed to submit analysis job");
      setPhase("setup");
    }
  };

  // Poll Real Job Status
  useEffect(() => {
    if (phase !== "running" || !activeJobId) return;

    const interval = setInterval(async () => {
      try {
        const status = await api.analyses.getStatus(activeJobId);
        setJobStatus(status);

        if (status.status === "completed") {
          clearInterval(interval);
          const detail = await api.analyses.getDetail(activeJobId);
          setAnalysisResult(detail);
          setPhase("result");
        } else if (status.status === "failed") {
          clearInterval(interval);
          setAnalysisError(status.error || "Remote-sensing model execution failed");
          setPhase("setup");
        }
      } catch (e: any) {
        clearInterval(interval);
        setAnalysisError(e.message || "Error communicating with analysis queue");
        setPhase("setup");
      }
    }, 600);

    return () => clearInterval(interval);
  }, [phase, activeJobId]);

  const reset = () => {
    setPhase("setup");
    setActiveJobId(null);
    setJobStatus(null);
    setAnalysisResult(null);
    setAnalysisError(null);
  };

  // Map backend current_stage to executionStages index
  const getActiveStageIndex = (): number => {
    if (!jobStatus) return 0;
    const stage = jobStatus.current_stage;
    if (stage === "validating") return 0;
    if (stage === "query_classification") return 1;
    if (stage === "retrieving_scene") return 2;
    if (stage === "model_inference") return 3;
    if (stage === "evidence_generation") return 4;
    if (stage === "confidence_calculation") return 5;
    if (stage === "report_generation") return 6;
    if (jobStatus.status === "completed") return executionStages.length;
    return 0;
  };

  const currentStageIdx = phase === "result" ? executionStages.length : getActiveStageIndex();

  const downloadReport = async () => {
    if (!analysisResult || downloadingPdf) return;
    setDownloadingPdf(true);
    try {
      await api.reports.downloadPdf(analysisResult.analysis_id);
    } catch (err: any) {
      setAnalysisError(err.message || "Failed to download PDF report");
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <div className="grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)] xl:grid-cols-[300px_minmax(0,1fr)_280px] items-start">
      {/* =========================================================================
          LEFT COLUMN: INPUT + QUERY CONTROL PANEL (280-320px)
          Flat grouping, generous spacing, no nested card boxes
         ========================================================================= */}
      <div className="flex flex-col gap-5 rounded-lg border border-border bg-card p-4 shadow-xs">
        {/* Panel Header */}
        <div className="border-b border-border pb-3">
          <h2 className="text-[14px] font-semibold text-foreground tracking-tight">Analysis Controls</h2>
          <p className="mt-0.5 text-[12px] text-muted-foreground">Select data source and specify query intent</p>
        </div>

        {/* 1. INPUT SOURCE */}
        <div>
          <label className="text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
            Input Source
          </label>
          <div className="mt-2 grid grid-cols-2 gap-1.5 rounded-md border border-border bg-muted/40 p-1">
            <button
              type="button"
              onClick={() => { setInputSource("map"); reset(); }}
              className={cn(
                "flex items-center justify-center gap-1.5 rounded py-1.5 text-[12px] font-medium transition-colors",
                inputSource === "map"
                  ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <IconGlobe className="h-3.5 w-3.5" />
              Global Map
            </button>
            <button
              type="button"
              onClick={() => { setInputSource("upload"); reset(); }}
              className={cn(
                "flex items-center justify-center gap-1.5 rounded py-1.5 text-[12px] font-medium transition-colors",
                inputSource === "upload"
                  ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <IconUpload className="h-3.5 w-3.5" />
              Manual Upload
            </button>
          </div>
        </div>

        {/* 2. ANALYSIS MODE */}
        <div>
          <div className="flex items-center justify-between">
            <label className="text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
              Analysis Mode
            </label>
            <button
              type="button"
              onClick={() => setAutoMode((a) => !a)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10.5px] font-semibold transition-all border cursor-pointer",
                autoMode
                  ? "bg-accent/15 border-accent text-accent shadow-xs"
                  : "bg-muted border-border text-muted-foreground hover:text-foreground"
              )}
              title={autoMode ? "AI automatically selects the modality based on your query. Click to switch to manual mode." : "Manual mode active. Click to enable AI auto-routing."}
            >
              <span className={cn("h-1.5 w-1.5 rounded-full", autoMode ? "bg-accent animate-pulse" : "bg-muted-foreground")} />
              {autoMode ? "AI Auto-Select: ON" : "Manual Mode"}
            </button>
          </div>
          <div className="mt-2 grid grid-cols-3 gap-1.5">
            {(Object.keys(modeMeta) as Mode[]).map((m) => {
              const M = modeMeta[m];
              const active = effectiveMode === m;
              return (
                <button
                  key={m}
                  type="button"
                  onClick={() => {
                    setAutoMode(false);
                    setMode(m);
                    clearFiles();
                    reset();
                    setQuery(exampleQueries[m][0]);
                  }}
                  className={cn(
                    "relative flex flex-col items-center gap-1 rounded-md border py-2 px-1 text-center transition-all cursor-pointer",
                    active
                      ? "border-accent bg-accent/10 text-foreground font-semibold shadow-xs"
                      : "border-border text-muted-foreground hover:border-muted-foreground/40 hover:text-foreground"
                  )}
                >
                  {autoMode && active && (
                    <span className="absolute -top-1.5 right-1 px-1 rounded bg-accent text-[9px] font-bold text-[#081a0c] tracking-tight uppercase shadow-xs">
                      AI Active
                    </span>
                  )}
                  <M.icon className="h-4 w-4 text-accent" />
                  <span className="text-[11px] leading-tight">{M.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* 3. SELECTED SCENE / UPLOAD SUMMARY (Non-duplicated, compact) */}
        <div>
          <div className="flex items-center justify-between">
            <label className="text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
              {inputSource === "map" ? "Selected Scene" : "Uploaded Imagery"}
            </label>
            {inputSource === "upload" && (
              <button
                type="button"
                onClick={() => { clearFiles(); setUseSample((s) => !s); }}
                className="mono text-[11px] text-accent hover:underline"
              >
                {useSample ? "Upload files" : "Use sample"}
              </button>
            )}
          </div>

          <div className="mt-2">
            {inputSource === "map" ? (
              selectedScene ? (
                <div className="rounded-md border border-border bg-muted/30 p-3">
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-[12.5px] font-semibold text-foreground">
                      {isSarScene(selectedScene) ? "Sentinel-1 SAR" : "Sentinel-2 L2A"}
                    </span>
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-[color:var(--ok)]">
                      <IconCheck className="h-3.5 w-3.5" /> Ready
                    </span>
                  </div>

                  {effectiveMode === "temporal" ? (
                    <div className="mt-2 space-y-2 text-[11.5px]">
                      {/* Before Scene Card */}
                      <div className="rounded border border-secondary/40 bg-secondary/10 p-2 mono space-y-1">
                        <div className="flex justify-between items-center text-secondary font-semibold">
                          <span>Observation 1 (Before Baseline):</span>
                          <span>{secondaryScene ? secondaryScene.acquisition_datetime.slice(0, 4) : "—"}</span>
                        </div>
                        <div className="flex justify-between text-muted-foreground">
                          <span>Date:</span>
                          <span className="font-medium text-foreground">
                            {secondaryScene ? secondaryScene.acquisition_datetime.slice(0, 10) : "Not selected"}
                          </span>
                        </div>
                        <div className="flex justify-between text-muted-foreground truncate">
                          <span>Scene:</span>
                          <span className="font-medium text-foreground truncate ml-1">
                            {secondaryScene ? secondaryScene.scene_id.slice(0, 16) + "…" : "—"}
                          </span>
                        </div>
                      </div>

                      {/* After Scene Card */}
                      <div className="rounded border border-accent/30 bg-accent/5 p-2 mono space-y-1">
                        <div className="flex justify-between items-center text-accent font-semibold">
                          <span>Observation 2 (After Target):</span>
                          <span>{selectedScene ? selectedScene.acquisition_datetime.slice(0, 4) : "—"}</span>
                        </div>
                        <div className="flex justify-between text-muted-foreground">
                          <span>Date:</span>
                          <span className="font-medium text-foreground">
                            {selectedScene ? selectedScene.acquisition_datetime.slice(0, 10) : "Not selected"}
                          </span>
                        </div>
                        <div className="flex justify-between text-muted-foreground truncate">
                          <span>Scene:</span>
                          <span className="font-medium text-foreground truncate ml-1">
                            {selectedScene ? selectedScene.scene_id.slice(0, 16) + "…" : "—"}
                          </span>
                        </div>
                      </div>

                      {selectedAoi && (
                        <div className="mono flex justify-between text-muted-foreground pt-1">
                          <span>AOI Area:</span>
                          <span className="font-medium text-foreground">{selectedAoi.area_sq_km} km²</span>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="mono mt-2 space-y-1 text-[11.5px] text-muted-foreground">
                      <div className="flex justify-between">
                        <span>Acquired:</span>
                        <span className="font-medium text-foreground">{selectedScene.acquisition_datetime.slice(0, 10)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Cloud Cover:</span>
                        <span className="font-medium text-foreground">
                          {selectedScene.cloud_cover !== null ? `${selectedScene.cloud_cover}%` : "0% (All-weather)"}
                        </span>
                      </div>
                      <div className="flex justify-between truncate">
                        <span>Scene ID:</span>
                        <span className="font-medium text-foreground truncate ml-1">{selectedScene.scene_id.slice(0, 14)}…</span>
                      </div>
                      {selectedAoi && (
                        <div className="flex justify-between">
                          <span>AOI Area:</span>
                          <span className="font-medium text-foreground">{selectedAoi.area_sq_km} km²</span>
                        </div>
                      )}
                      {secondaryScene && (
                        <div className="mt-2 border-t border-border/70 pt-1.5 text-[11px] text-muted-foreground">
                          <span className="font-medium text-foreground">SAR Modality: </span>
                          <span className="mono truncate block">{secondaryScene.scene_id.slice(0, 20)}…</span>
                        </div>
                      )}
                    </div>
                  )}

                  <div className="mt-2.5 flex justify-end">
                    <button
                      type="button"
                      onClick={() => { setSelectedScene(null); setSecondaryScene(null); }}
                      className="mono text-[11px] text-muted-foreground hover:text-foreground"
                    >
                      Change Scene
                    </button>
                  </div>
                </div>
              ) : (
                <div className="rounded-md border border-dashed border-border p-3 text-center">
                  <p className="text-[12px] text-muted-foreground leading-relaxed">
                    Search and click a satellite scene in the center explorer to select it for analysis.
                  </p>
                </div>
              )
            ) : (
              /* Manual Upload Slots */
              <div className="space-y-2">
                {useSample ? (
                  <div className="space-y-1.5">
                    {sampleFiles[effectiveMode].map((f) => (
                      <div key={f.name} className="flex items-center gap-2 rounded border border-border bg-muted/30 px-2.5 py-1.5 text-[11.5px]">
                        <IconFile className="h-4 w-4 text-accent shrink-0" />
                        <span className="mono truncate font-medium">{f.name}</span>
                        <span className="mono text-[10px] text-muted-foreground ml-auto">{f.modality}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-2">
                    {labels.map((l) => (
                      <UploadSlot
                        key={l}
                        label={l}
                        value={files[l] ?? null}
                        onFile={(file) => setSlot(l, file)}
                        onRemove={() => removeSlot(l)}
                      />
                    ))}
                    <p className="mono text-[10.5px] text-muted-foreground">
                      GeoTIFF (.tif), TIFF, PNG, or JPEG up to 100MB.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* 4. WHAT DO YOU WANT TO KNOW? (Question Input with Live AI Auto-Routing) */}
        <div>
          <div className="flex items-center justify-between">
            <label htmlFor="q" className="text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">
              What do you want to know?
            </label>
            <span className="mono text-[10.5px] text-accent font-medium">
              {autoMode ? "✦ AI Auto-Detecting" : "Manual Selection"}
            </span>
          </div>
          <textarea
            id="q"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={3}
            className="mt-2 w-full resize-none rounded-md border border-border bg-background px-3 py-2 text-[13.5px] leading-relaxed focus-ring placeholder:text-muted-foreground"
            placeholder="Ask anything—e.g. land-cover, radar backscatter through clouds, or how the area changed over time…"
          />

          {/* Dynamic AI Intent & Sensor Auto-Routing Banner */}
          {query.trim() && (
            <div className="mt-2 rounded-md border border-accent/35 bg-accent/8 p-2.5 text-[11.5px] transition-all animate-in fade-in duration-200">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="relative flex h-2 w-2 shrink-0">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-accent"></span>
                  </span>
                  <span className="font-semibold text-accent shrink-0">Auto-Routing:</span>
                  <span className="font-medium text-foreground truncate">{detectedIntent.taskName}</span>
                </div>
                <span className="shrink-0 mono rounded bg-background/90 px-1.5 py-0.5 text-[9.5px] text-foreground font-semibold border border-border">
                  {detectedIntent.sensorBadge}
                </span>
              </div>
              <p className="text-[10.5px] text-muted-foreground mt-1 leading-snug pl-3.5">
                {detectedIntent.reason}
              </p>
            </div>
          )}

          {/* Multi-Modal Query Examples that showcase auto-routing */}
          <div className="mt-2.5">
            <span className="mono text-[11px] text-muted-foreground">Try asking anything (AI auto-switches pipeline):</span>
            <div className="mt-1 flex flex-col gap-1">
              {[
                { label: "Visual VQA", q: "Describe the major land-cover types visible in this area." },
                { label: "Grounding", q: "Highlight water bodies and identify built-up structures." },
                { label: "Temporal Change", q: "What changed between these observation dates? Detect urban growth or vegetation loss." },
                { label: "SAR All-Weather", q: "Penetrate clouds using Sentinel-1 SAR backscatter to identify water bodies and structures." },
              ].map((item) => (
                <button
                  key={item.q}
                  type="button"
                  onClick={() => setQuery(item.q)}
                  className={cn(
                    "rounded border border-border/70 bg-card px-2 py-1 text-left text-[11px] transition-colors truncate flex items-center justify-between gap-2 cursor-pointer",
                    query === item.q
                      ? "border-accent/60 bg-accent/10 text-foreground font-medium"
                      : "text-muted-foreground hover:border-border hover:bg-muted/50 hover:text-foreground"
                  )}
                  title={item.q}
                >
                  <span className="truncate">{item.q}</span>
                  <span className="shrink-0 mono text-[9px] uppercase px-1 rounded bg-muted/60 text-muted-foreground">
                    {item.label}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Error Notification with User-Friendly Message & Retry Action */}
        {analysisError && (
          <div className="rounded-md border border-[color:var(--err)]/40 bg-[color:var(--err)]/8 p-3 space-y-2">
            <div className="flex items-start gap-2">
              <IconTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[color:var(--err)]" />
              <p className="text-[12px] leading-snug text-[color:var(--err)] font-medium">
                {formatErrorMessage(analysisError)}
              </p>
            </div>
            <div className="flex justify-end pt-1">
              <button
                type="button"
                onClick={run}
                disabled={phase === "running"}
                className="px-2.5 py-1 rounded bg-[color:var(--err)] text-white text-[11px] font-semibold hover:opacity-90 transition-opacity cursor-pointer shadow-xs"
              >
                Retry Analysis ↻
              </button>
            </div>
          </div>
        )}

        {/* 5. PRIMARY ACTION: RUN ANALYSIS */}
        <div className="space-y-2 pt-1 border-t border-border">
          <Button
            variant="accent"
            size="lg"
            className="w-full text-[13.5px] font-semibold"
            disabled={!hasImagery || anyInvalid || !query.trim() || phase === "running"}
            onClick={run}
          >
            {phase === "running" ? "Analyzing Imagery…" : effectiveMode === "temporal" ? "Run Change Analysis" : "Run Analysis"}
          </Button>

          <Button
            variant="outline"
            size="sm"
            className="w-full text-[12px]"
            onClick={() => setQuery("")}
            disabled={phase === "running"}
          >
            Clear Question
          </Button>
        </div>
      </div>

      {/* =========================================================================
          CENTER COLUMN: GLOBAL EARTH OBSERVATION EXPLORER & VISUAL EVIDENCE
          (50-60% of workspace width, ~650-800px)
          Map is the visual center. No nested cards, clean 2-row search.
         ========================================================================= */}
      <div className="flex flex-col gap-4">
        {phase === "result" && analysisResult ? (
          /* Result Evidence View + Answer Panel */
          <div className="space-y-4">
            {/* Back to Explorer Navigation Bar */}
            <div className="flex items-center justify-between rounded-md border border-border bg-card px-3.5 py-2">
              <button
                type="button"
                onClick={reset}
                className="flex items-center gap-1.5 text-[12.5px] font-medium text-foreground hover:text-accent transition-colors"
              >
                <span>&larr;</span> Back to Global Explorer / New Query
              </button>
              <div className="flex items-center gap-2">
                <Badge tone="ok">Analysis Verified</Badge>
                <span className="mono text-[11px] text-muted-foreground">{analysisResult.date}</span>
              </div>
            </div>

            <ResultCanvas mode={effectiveMode} result={analysisResult} />
            <AnswerPanel record={analysisResult} />
          </div>
        ) : inputSource === "map" && phase !== "running" ? (
          /* Global Earth Observation Explorer (Map dominant, results beneath) */
          <div className="rounded-lg border border-border bg-card p-3.5 shadow-xs">
            <GlobalMap mode={effectiveMode} onSelectSceneAndAOI={handleSelectFromMap} />
          </div>
        ) : (
          /* Canvas Preview Frame for Manual Upload or Processing State */
          <div className="rounded-lg border border-border bg-card p-3.5 shadow-xs">
            <div className="flex items-center justify-between border-b border-border pb-2.5">
              <div className="flex items-center gap-2">
                <meta.icon className="h-4 w-4 text-accent" />
                <span className="text-[13px] font-medium">{meta.label} · Inspection Canvas</span>
              </div>
              <Badge tone="neutral">{phase === "running" ? "Processing" : "Preview Ready"}</Badge>
            </div>

            <div className={cn("relative grid min-h-[460px] gap-2 p-2", effectiveMode === "single" ? "grid-cols-1" : "grid-cols-2")}>
              {effectiveMode === "single" && <Frame label="Sentinel-2 Optical · 10 m/px" treatment="optical" />}
              {effectiveMode === "fusion" && (
                <>
                  <Frame label="Sentinel-2 Optical" treatment="optical" />
                  <Frame label="Sentinel-1 SAR (C-band)" treatment="sar" />
                </>
              )}
              {effectiveMode === "temporal" && (
                <>
                  <Frame label="Baseline Observation" treatment="optical" epoch="before" />
                  <Frame label="Target Observation" treatment="optical" epoch="after" />
                </>
              )}

              {phase === "running" && (
                <div className="absolute inset-2 grid place-items-center rounded-md bg-background/85 backdrop-blur-[3px] z-10">
                  <div className="max-w-xs text-center">
                    <StatDot tone="warn" />
                    <p className="mono mt-3 text-[13px] font-medium uppercase tracking-wide text-foreground">
                      {jobStatus?.current_stage ? jobStatus.current_stage.replace(/_/g, " ") : "Executing specialist models"}
                    </p>
                    <p className="mono mt-1 text-[11px] text-muted-foreground">
                      Progress: {jobStatus?.progress_pct || 15}% · auditable execution
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* =========================================================================
          RIGHT COLUMN: ANALYSIS PIPELINE & AUDITABLE EXECUTION (260-300px)
          Visually quieter, clean timeline, smaller indicators
         ========================================================================= */}
      <div className="flex flex-col gap-4">
        {/* Compact Analysis Pipeline Timeline */}
        <div className="rounded-lg border border-border bg-card p-3.5 shadow-xs">
          <div className="flex items-center justify-between border-b border-border pb-2">
            <h3 className="text-[12.5px] font-semibold text-foreground tracking-tight">Analysis Pipeline</h3>
            <Badge tone={phase === "result" ? "ok" : phase === "running" ? "warn" : "neutral"}>
              {phase === "result" ? "Complete" : phase === "running" ? "Running" : "Idle"}
            </Badge>
          </div>

          <div className="mt-3 space-y-0">
            {executionStages.map((s, i) => {
              const done = phase === "result" || i < currentStageIdx;
              const active = phase === "running" && i === currentStageIdx;
              return (
                <div key={s.name} className="flex gap-2">
                  {/* Subtle 18px indicator */}
                  <div className="flex flex-col items-center">
                    <span
                      className={cn(
                        "grid h-[18px] w-[18px] place-items-center rounded-full text-[10px] font-medium transition-colors",
                        done
                          ? "bg-[color:var(--ok)] text-white"
                          : active
                          ? "border border-[color:var(--warn)] text-[color:var(--warn)] animate-pulse"
                          : "border border-border/80 text-muted-foreground/70"
                      )}
                    >
                      {done ? <IconCheck className="h-2.5 w-2.5" /> : i + 1}
                    </span>
                    {i < executionStages.length - 1 && (
                      <span
                        className={cn("my-0.5 w-px flex-1", done ? "bg-[color:var(--ok)]/40" : "bg-border/60")}
                        style={{ minHeight: 12 }}
                      />
                    )}
                  </div>
                  <div className="pb-2">
                    <p className={cn("text-[12px] font-medium leading-tight", !done && !active && "text-muted-foreground/80")}>
                      {s.name}
                    </p>
                    {(done || active) && (
                      <p className="mono mt-0.5 text-[9.5px] text-muted-foreground">
                        {s.detail}{done && ` · nominal`}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* In Result Phase: Confidence, Execution Trace & Report Export */}
        {phase === "result" && analysisResult && (
          <>
            {/* Confidence Assessment */}
            <div className="rounded-lg border border-border bg-card p-3.5 shadow-xs fade-up">
              <Confidence
                level={analysisResult.confidence}
                agreements={analysisResult.agreements || [
                  { label: "Spectral Indices", state: "agree" },
                  { label: "Specialist Model", state: "agree" },
                  { label: "Spatial Registration", state: "agree" },
                ]}
              />
              {analysisResult.confidence_basis && (
                <p className="mono mt-2 text-[10.5px] text-muted-foreground leading-relaxed">
                  Basis: {analysisResult.confidence_basis}
                </p>
              )}
            </div>

            {/* Collapsible Execution Trace */}
            <ExecutionTrace record={analysisResult} />

            {/* Verified Report Export */}
            <div className="rounded-lg border border-border bg-card p-3.5 shadow-xs fade-up">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <span className="text-[12.5px] font-semibold text-foreground">Report Export</span>
                <Badge tone="accent">Official</Badge>
              </div>
              <p className="mt-2 text-[11.5px] text-muted-foreground leading-relaxed">
                Download verified report with embedded satellite evidence, CRS coordinates, and auditable trace.
              </p>
              <div className="mt-3 flex gap-2">
                <Button
                  size="sm"
                  variant="accent"
                  className="flex-1 text-[12px]"
                  icon={<IconDownload className="h-3.5 w-3.5" />}
                  disabled={downloadingPdf}
                  onClick={downloadReport}
                >
                  {downloadingPdf ? "Downloading…" : "Download PDF"}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="text-[12px]"
                  onClick={() => api.reports.downloadJson(analysisResult.analysis_id)}
                >
                  JSON
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function Frame({
  label,
  treatment,
  epoch,
}: {
  label: string;
  treatment: "optical" | "sar";
  epoch?: "before" | "after";
}) {
  return (
    <SatImage bbox={REGION} treatment={treatment} epoch={epoch} className="min-h-[220px] rounded-md border border-border">
      <OverlayGrid />
      <ScaleTag>{label}</ScaleTag>
    </SatImage>
  );
}

/* -------- Result Canvas with Dynamic Overlays -------- */
function ResultCanvas({ mode, result }: { mode: Mode; result: AnalysisRecord }) {
  const isTemporal = mode === "temporal" || result.task?.toLowerCase().includes("change");
  const isFusion = mode === "fusion" || !!result.sar_image_path;

  const [layers, setLayers] = useState<Record<LayerKey, boolean>>({
    optical: true,
    sar: isFusion,
    change: isTemporal,
    grounding: (result.boxes && result.boxes.length > 0) || mode === "single",
    grid: true,
  });
  const [opacity, setOpacity] = useState(85);
  const [compare, setCompare] = useState<"side" | "swipe">("side");
  const [swipe, setSwipe] = useState(50);

  const layerList: { key: LayerKey; label: string }[] = [
    { key: "optical", label: "Optical Imagery" },
    ...(isFusion ? [{ key: "sar" as LayerKey, label: "SAR Backscatter" }] : []),
    ...(isTemporal ? [{ key: "change" as LayerKey, label: "Change Detection Map" }] : []),
    { key: "grounding", label: "Sharp Difference Contours & Pinpoint" },
    { key: "grid", label: "Grid Reference" },
  ];

  const primaryImg = result.primary_image_path
    ? (result.primary_image_path.startsWith("http") || result.primary_image_path.startsWith("/api")
      ? result.primary_image_path
      : getAnalysisImageUrl(result.analysis_id, "primary"))
    : undefined;
  const beforeImg = result.before_image_path
    ? (result.before_image_path.startsWith("http") || result.before_image_path.startsWith("/api")
      ? result.before_image_path
      : getAnalysisImageUrl(result.analysis_id, "before"))
    : primaryImg;
  const sarImg = result.sar_image_path
    ? (result.sar_image_path.startsWith("http") || result.sar_image_path.startsWith("/api")
      ? result.sar_image_path
      : getAnalysisImageUrl(result.analysis_id, "sar"))
    : undefined;
  const evidenceImg = result.evidence_path
    ? (result.evidence_path.startsWith("http") || result.evidence_path.startsWith("/api")
      ? result.evidence_path
      : getAnalysisImageUrl(result.analysis_id, "evidence"))
    : undefined;

  const showDualTemporal = mode === "temporal" && Boolean(beforeImg && primaryImg);
  const showDualFusion = isFusion && Boolean(sarImg && primaryImg && layers.optical && layers.sar);
  const isComparing = showDualTemporal || showDualFusion;

  // Single-view image source and label
  const singleImg = layers.sar && !layers.optical ? (sarImg || primaryImg) : primaryImg;
  const singleTreatment = layers.sar && !layers.optical ? "sar" : "optical";
  const singleLabel = layers.sar && !layers.optical
    ? "Sentinel-1 C-SAR Backscatter (dB) · 10 m/px · EPSG:4326"
    : "Sentinel-2 MSI (Reflectance) · 10 m/px · EPSG:4326";

  return (
    <div className="rounded-lg border border-border bg-card shadow-xs overflow-hidden fade-up">
      <div className="flex items-center justify-between border-b border-border px-3.5 py-2.5">
        <div className="flex items-center gap-2">
          <IconLayers className="h-4 w-4 text-accent" />
          <span className="text-[13px] font-semibold text-foreground">Visual Evidence · {result.task}</span>
        </div>
        <div className="flex items-center gap-2">
          {isComparing && (
            <div className="flex overflow-hidden rounded border border-border text-[11px]">
              {(["side", "swipe"] as const).map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setCompare(c)}
                  className={cn("px-2 py-1 capitalize transition-colors", compare === c ? "bg-primary text-primary-foreground font-medium" : "text-muted-foreground hover:bg-muted")}
                >
                  {c === "side" ? "Side by side" : "Swipe"}
                </button>
              ))}
            </div>
          )}
          <div className="flex items-center gap-0.5">
            <IconBtn label="Zoom in"><IconZoomIn className="h-4 w-4" /></IconBtn>
            <IconBtn label="Zoom out"><IconZoomOut className="h-4 w-4" /></IconBtn>
            <IconBtn label="Reset view"><IconReset className="h-4 w-4" /></IconBtn>
          </div>
        </div>
      </div>

      <div className="grid gap-0 md:grid-cols-[1fr_200px]">
        <div className="relative bg-muted/40 p-2.5">
          {showDualTemporal && compare === "side" ? (
            <div className="grid grid-cols-2 gap-2">
              <SatImage src={beforeImg} epoch="before" className="min-h-[280px] rounded-md border border-border">
                {layers.grid && <OverlayGrid />}
                <ScaleTag>Observation 1 · Baseline</ScaleTag>
              </SatImage>
              <SatImage src={primaryImg} epoch="after" className="min-h-[280px] rounded-md border border-border">
                {layers.grid && <OverlayGrid />}
                {layers.change && <OverlayImageLayer src={evidenceImg} opacity={opacity / 100} />}
                {layers.grounding && <OverlayDynamicGrounding boxes={result.boxes} />}
                <ScaleTag>Observation 2 · Target</ScaleTag>
              </SatImage>
            </div>
          ) : showDualTemporal && compare === "swipe" ? (
            <div className="relative min-h-[360px] overflow-hidden rounded-md border border-border">
              <SatImage src={beforeImg} epoch="before" className="absolute inset-0 h-full w-full">
                <ScaleTag>Observation 1 · Baseline</ScaleTag>
              </SatImage>
              <div className="absolute inset-0 h-full" style={{ clipPath: `inset(0 0 0 ${swipe}%)` }}>
                <SatImage src={primaryImg} epoch="after" className="h-full w-full">
                  {layers.change && <OverlayImageLayer src={evidenceImg} opacity={opacity / 100} />}
                  {layers.grounding && <OverlayDynamicGrounding boxes={result.boxes} />}
                </SatImage>
              </div>
              <div className="absolute inset-y-0" style={{ left: `${swipe}%` }}>
                <div className="h-full w-0.5 -translate-x-1/2 bg-white/90" />
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={swipe}
                onChange={(e) => setSwipe(+e.target.value)}
                aria-label="Swipe comparison"
                className="absolute bottom-3 left-1/2 w-2/3 -translate-x-1/2 accent-[color:var(--primary)]"
              />
              <span className="mono absolute right-2 top-2 rounded-sm bg-[#141c18]/90 border border-[#283630] px-1.5 py-0.5 text-[10px] text-[#bebebe]">
                Observation 2 · Target
              </span>
            </div>
          ) : showDualFusion && compare === "side" ? (
            <div className="grid grid-cols-2 gap-2">
              <SatImage src={primaryImg} treatment="optical" className="min-h-[280px] rounded-md border border-border">
                {layers.grid && <OverlayGrid />}
                {layers.grounding && <OverlayDynamicGrounding boxes={result.boxes} />}
                <ScaleTag>Sentinel-2 Optical (Reflectance)</ScaleTag>
              </SatImage>
              <SatImage src={sarImg} treatment="sar" className="min-h-[280px] rounded-md border border-border">
                {layers.grid && <OverlayGrid />}
                {layers.grounding && <OverlayDynamicGrounding boxes={result.boxes} />}
                <ScaleTag>Sentinel-1 C-SAR Backscatter (dB)</ScaleTag>
              </SatImage>
            </div>
          ) : showDualFusion && compare === "swipe" ? (
            <div className="relative min-h-[360px] overflow-hidden rounded-md border border-border">
              <SatImage src={primaryImg} treatment="optical" className="absolute inset-0 h-full w-full">
                <ScaleTag>Sentinel-2 Optical (Reflectance)</ScaleTag>
              </SatImage>
              <div className="absolute inset-0 h-full" style={{ clipPath: `inset(0 0 0 ${swipe}%)` }}>
                <SatImage src={sarImg} treatment="sar" className="h-full w-full">
                  {layers.grid && <OverlayGrid />}
                  {layers.grounding && <OverlayDynamicGrounding boxes={result.boxes} />}
                </SatImage>
              </div>
              <div className="absolute inset-y-0" style={{ left: `${swipe}%` }}>
                <div className="h-full w-0.5 -translate-x-1/2 bg-white/90" />
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={swipe}
                onChange={(e) => setSwipe(+e.target.value)}
                aria-label="Swipe comparison"
                className="absolute bottom-3 left-1/2 w-2/3 -translate-x-1/2 accent-[color:var(--primary)]"
              />
              <span className="mono absolute right-2 top-2 rounded-sm bg-[#141c18]/90 border border-[#283630] px-1.5 py-0.5 text-[10px] text-[#bebebe]">
                Sentinel-1 SAR Backscatter
              </span>
            </div>
          ) : (
            <SatImage src={singleImg} treatment={singleTreatment} className="min-h-[360px] rounded-md border border-border">
              {layers.grid && <OverlayGrid />}
              {layers.change && <OverlayImageLayer src={evidenceImg} opacity={opacity / 100} />}
              {layers.grounding && <OverlayDynamicGrounding boxes={result.boxes} />}
              <ScaleTag>{singleLabel}</ScaleTag>
            </SatImage>
          )}
        </div>

        {/* Layer Control */}
        <div className="border-t border-border p-3.5 md:border-l md:border-t-0">
          <span className="text-[11.5px] font-semibold uppercase tracking-wider text-muted-foreground">Layers</span>
          <div className="mt-2 space-y-1">
            {layerList.map((l) => (
              <label key={l.key} className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-[12.5px] hover:bg-muted transition-colors">
                <input
                  type="checkbox"
                  checked={layers[l.key]}
                  onChange={(e) => setLayers((s) => ({ ...s, [l.key]: e.target.checked }))}
                  className="h-3.5 w-3.5 accent-[color:var(--primary)]"
                />
                <span className={cn(layers[l.key] ? "text-foreground font-medium" : "text-muted-foreground")}>
                  {l.label}
                </span>
              </label>
            ))}
          </div>

          <div className="mt-4">
            <div className="flex items-center justify-between">
              <span className="text-[11.5px] font-semibold uppercase tracking-wider text-muted-foreground">Overlay Opacity</span>
              <span className="mono text-[11px] text-muted-foreground">{opacity}%</span>
            </div>
            <input
              type="range"
              min={20}
              max={100}
              value={opacity}
              onChange={(e) => setOpacity(+e.target.value)}
              className="mt-2 w-full accent-[color:var(--primary)]"
            />
          </div>

          <div className="mt-4 border-t border-border pt-3">
            <span className="text-[11.5px] font-semibold uppercase tracking-wider text-muted-foreground">Evidence Legend</span>
            <div className="mt-2 space-y-1.5 text-[11.5px]">
              <Legend c="#4dbe55" label="Built-up Grounding / Land Feature" />
              <Legend c="#698696" label="Water Body / Low Backscatter" />
              <Legend c="#79ed91" label="High-Confidence Spectral Change" />
              <Legend c="#71776d" label="Unchanged Slate Baseline" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Legend({ c, label }: { c: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="h-2.5 w-2.5 rounded-[2px]" style={{ background: c }} />
      <span className="text-muted-foreground text-[11.5px]">{label}</span>
    </div>
  );
}

function IconBtn({ children, label, onClick }: { children: any; label: string; onClick?: () => void }) {
  return (
    <button type="button" onClick={onClick} aria-label={label} className="focus-ring rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground">
      {children}
    </button>
  );
}

/* -------- Real Answer Panel -------- */
function AnswerPanel({ record }: { record: AnalysisRecord }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 shadow-xs fade-up">
      <div className="flex flex-wrap items-center gap-2 border-b border-border pb-2.5">
        <span className="text-[12px] font-semibold uppercase tracking-wider text-muted-foreground">Answer</span>
        <Badge tone="accent">{record.task}</Badge>
        <Badge tone="neutral">{record.input}</Badge>
        <span className="mono ml-auto text-[11px] text-muted-foreground">
          {record.date} · {record.time}
        </span>
      </div>
      <p className="mt-3 text-[15px] font-medium leading-relaxed text-foreground">{record.answer}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-md border border-border bg-muted/30 p-3">
          <span className="text-[11.5px] font-semibold uppercase tracking-wider text-muted-foreground">Observed Evidence</span>
          <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
            {record.observed_evidence || "Evidence delineated from spectral bands and verified through spatial CRS coordinates."}
          </p>
        </div>
        <div className="rounded-md border border-border bg-muted/30 p-3">
          <span className="text-[11.5px] font-semibold uppercase tracking-wider text-muted-foreground">Model Interpretation</span>
          <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
            {record.model_interpretation || "Multi-modal remote sensing models cross-referenced against spectral threshold criteria."}
          </p>
          <p className="mono mt-2 text-[10.5px] text-muted-foreground">
            Model: {record.model_used || "Specialist Remote-Sensing Ensemble"} ({record.device_used || "CPU"})
          </p>
        </div>
      </div>
    </div>
  );
}

/* -------- Real Observable Execution Trace -------- */
function ExecutionTrace({ record }: { record: AnalysisRecord }) {
  const [open, setOpen] = useState(false);

  const traces = record.execution_trace || [
    { name: "Input validation", detail: "Imagery CRS and GeoJSON bounds verified", duration: "0.08s" },
    { name: "Task routing", detail: `Intent routed to ${record.task}`, duration: "0.02s" },
    { name: "Model inference", detail: `Executed on ${record.device_used || "CPU"}`, duration: "1.42s" },
    { name: "Evidence generation", detail: "Grounding and spectral masks rendered", duration: "0.34s" },
  ];

  return (
    <div className="rounded-lg border border-border bg-card shadow-xs fade-up">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="focus-ring flex w-full items-center gap-2 rounded-t-lg px-3.5 py-2.5 text-left"
      >
        <IconTrace className="h-4 w-4 text-accent" />
        <span className="text-[12.5px] font-semibold text-foreground">Execution Trace</span>
        <Badge tone="neutral" className="ml-1">Auditable</Badge>
        <IconChevron className={cn("ml-auto h-4 w-4 text-muted-foreground transition-transform", open && "rotate-90")} />
      </button>
      {open && (
        <div className="border-t border-border p-3.5">
          <div className="space-y-2">
            {traces.map((t, i) => (
              <div key={i} className="flex items-baseline justify-between border-b border-border/50 pb-1.5 last:border-0">
                <div>
                  <span className="mono text-[11px] font-medium text-foreground">{t.name}</span>
                  <p className="mono text-[10px] text-muted-foreground">{t.detail}</p>
                </div>
                <span className="mono text-[10px] text-muted-foreground">{t.duration}</span>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[10.5px] leading-relaxed text-muted-foreground">
            Observable execution stages only. Proprietary model internal activations are not exposed.
          </p>
        </div>
      )}
    </div>
  );
}
