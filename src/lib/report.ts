import { jsPDF } from "jspdf";
import type { Analysis } from "./data";
import { REGIONS, satTileUrl, type Region } from "../components/SatImage";

/**
 * Real, downloadable report artifacts for an analysis.
 *
 * These build genuine files client-side (a valid PDF via jsPDF and a JSON
 * execution-trace export) so the download buttons produce openable, non-empty
 * files. The PDF embeds the actual satellite imagery and analytical layers for
 * the analysis, rendered from the same public Esri tiles the UI uses.
 */

const PRODUCT = "Satya Dristi";
const DESCRIPTOR = "Multimodal Earth Observation Intelligence";

/* ---------------- Scene rendering (imagery + analytical layers) ---------------- */

type Box = { x: number; y: number; w: number; h: number };

type SceneOpts = {
  treatment?: "optical" | "sar";
  epoch?: "before" | "after";
  overlay?: "change" | "grounding" | null;
  /** Grounding box in 0..100 scene coordinates (defaults to the corridor water channel). */
  groundingBox?: Box;
};

type Layer = { caption: string; region: Region; opts: SceneOpts };

/** Distinct scene + layer set per input type, mirroring the in-app treatments. */
function layersFor(a: Analysis): Layer[] {
  if (a.input === "Optical + SAR") {
    return [
      { caption: "Optical · 2.5 m/px", region: REGIONS.delta, opts: { treatment: "optical" } },
      { caption: "SAR · backscatter", region: REGIONS.delta, opts: { treatment: "sar" } },
    ];
  }
  if (a.input === "Before + After") {
    return [
      { caption: "Before · 2024-03-11", region: REGIONS.corridor, opts: { epoch: "before" } },
      { caption: "After · change overlay", region: REGIONS.corridor, opts: { epoch: "after", overlay: "change" } },
    ];
  }
  // Single image — VQA or grounding
  const grounding = a.task === "Grounding";
  return [
    {
      caption: grounding ? "Optical · grounding" : "Optical · 2.5 m/px",
      region: REGIONS.urbanWater,
      opts: {
        treatment: "optical",
        overlay: grounding ? "grounding" : null,
        // Hussain Sagar lake sits in the upper-right quadrant of this mosaic.
        groundingBox: { x: 57, y: 17, w: 38, h: 36 },
      },
    },
  ];
}

/**
 * Fetch a tile as bytes and decode it via createImageBitmap. Drawing a bitmap
 * decoded from a same-origin blob keeps the canvas untainted, so toDataURL
 * works even in sandboxed preview iframes where a cross-origin <img> would
 * taint the canvas (which previously made every report fall back to the same
 * placeholder).
 */
async function loadTile(url: string): Promise<ImageBitmap> {
  const res = await fetch(url, { mode: "cors" });
  if (!res.ok) throw new Error(`tile load failed: ${url}`);
  const blob = await res.blob();
  return createImageBitmap(blob);
}

/**
 * Zoom boost applied when rendering report imagery. Each +1 doubles the linear
 * resolution over the SAME geographic framing (2^boost tiles per axis), so the
 * analytical overlays keep their 0..100 coordinates. boost=1 → z+1, 4×4 tiles,
 * 1024px — roughly 2× sharper than the in-app 2×2 z-level mosaic.
 */
const ZOOM_BOOST = 1;

/** Render a high-resolution tile mosaic + treatment filters + analytical overlay to a JPEG data URL. */
async function renderScene(region: Region, opts: SceneOpts): Promise<string> {
  const per = 1 << ZOOM_BOOST; // tiles per axis
  const TILE_PX = 256;
  const SIZE = per * TILE_PX; // e.g. 1024px for a 4×4 grid
  const canvas = document.createElement("canvas");
  canvas.width = SIZE;
  canvas.height = SIZE;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("canvas unavailable");

  // The base 2×2 framing at `region.z` maps to a `2*per` × `2*per` block one or
  // more zoom levels deeper, covering the identical ground extent at higher res.
  const z = region.z + ZOOM_BOOST;
  const x0 = region.x * per;
  const y0 = region.y * per;
  const cols = 2 * per; // the in-app scene stitches a 2×2 base mosaic
  const placed: { region: Region; dx: number; dy: number }[] = [];
  for (let ry = 0; ry < cols; ry++) {
    for (let rx = 0; rx < cols; rx++) {
      placed.push({
        region: { z, x: x0 + rx, y: y0 + ry },
        dx: (rx / cols) * SIZE,
        dy: (ry / cols) * SIZE,
      });
    }
  }
  const drawPx = SIZE / cols;
  const imgs = await Promise.all(placed.map((p) => loadTile(satTileUrl(p.region))));

  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.filter =
    opts.treatment === "sar"
      ? "grayscale(1) contrast(1.6) brightness(0.82)"
      : opts.epoch === "before"
        ? "saturate(0.82) brightness(1.05) contrast(0.95)"
        : "saturate(1.02)";
  imgs.forEach((im, i) => ctx.drawImage(im, placed[i].dx, placed[i].dy, drawPx, drawPx));
  ctx.filter = "none";

  if (opts.treatment === "sar") {
    ctx.fillStyle = "rgba(28,47,74,0.25)";
    ctx.fillRect(0, 0, SIZE, SIZE);
  }

  // Analytical overlays — coordinates are 0..100 over the square (same as the UI).
  const s = SIZE / 100;
  ctx.lineWidth = 0.5 * s;
  ctx.setLineDash([2 * s, 1.2 * s]);
  const poly = (pts: [number, number][], fill: string, stroke: string) => {
    ctx.beginPath();
    pts.forEach(([px, py], i) => (i ? ctx.lineTo(px * s, py * s) : ctx.moveTo(px * s, py * s)));
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.strokeStyle = stroke;
    ctx.stroke();
  };

  if (opts.overlay === "change") {
    poly([[7, 57], [30, 59], [28, 80], [5, 77]], "rgba(171,124,44,0.22)", "#8a6420");
    poly([[55, 49], [90, 51], [88, 64], [53, 61]], "rgba(79,111,138,0.30)", "#3d5972");
  }

  if (opts.overlay === "grounding") {
    const b = opts.groundingBox ?? { x: 54, y: 48, w: 37, h: 17 };
    ctx.setLineDash([]);
    ctx.lineWidth = 0.7 * s;
    ctx.fillStyle = "rgba(49,56,81,0.10)";
    ctx.fillRect(b.x * s, b.y * s, b.w * s, b.h * s);
    ctx.strokeStyle = "#f6f3ed";
    ctx.strokeRect(b.x * s, b.y * s, b.w * s, b.h * s);
    const label = "water_body · 0.94";
    ctx.fillStyle = "rgba(49,56,81,0.9)";
    ctx.fillRect(b.x * s, (b.y - 4.5) * s, (label.length * 1.55 + 4) * s, 4.5 * s);
    ctx.fillStyle = "#f6f3ed";
    ctx.font = `${2.6 * s}px monospace`;
    ctx.fillText(label, (b.x + 1.5) * s, (b.y - 1.1) * s);
  }
  ctx.setLineDash([]);

  return canvas.toDataURL("image/jpeg", 0.92);
}

function modelsFor(task: Analysis["task"]): string {
  if (task === "Optical + SAR Fusion") return "Optical Encoder · SAR Encoder · Fusion";
  if (task === "Bi-Temporal Change") return "Change Understanding · Grounding";
  if (task === "Grounding") return "Grounding · Classification";
  return "Single-Image VQA · Grounding";
}

export function reportFileName(a: Analysis, ext: string): string {
  const date = new Date().toISOString().slice(0, 10);
  return `SatyaDristi_Analysis_${a.id}_${date}.${ext}`;
}

/** Structured report payload — mirrors what a backend report endpoint returns. */
export function buildReportPayload(a: Analysis) {
  return {
    product: PRODUCT,
    descriptor: DESCRIPTOR,
    report_id: a.id,
    generated_at: new Date().toISOString(),
    query: a.query,
    input: {
      type: a.input,
      format: "GeoTIFF",
      crs: "EPSG:4326",
    },
    analysis_type: a.task,
    answer: a.answer,
    confidence: a.confidence,
    execution_trace: {
      task: a.task,
      models: modelsFor(a.task),
      outputs: "Description · Evidence map",
      timestamp: `${a.date}T${a.time}:00Z`,
    },
    warnings:
      a.confidence === "Low"
        ? ["Cross-model evidence disagreement — result flagged as uncertain."]
        : [],
  };
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Revoke after the click has been dispatched.
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Generate and download a real, openable PDF of the analysis report (with imagery). */
export async function downloadReportPdf(a: Analysis) {
  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const margin = 48;
  const width = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const maxWidth = width - margin * 2;
  let y = margin;

  const line = (
    text: string,
    opts: { size?: number; bold?: boolean; gap?: number; color?: [number, number, number] } = {},
  ) => {
    const { size = 10, bold = false, gap = 6, color = [30, 34, 43] } = opts;
    doc.setFont("helvetica", bold ? "bold" : "normal");
    doc.setFontSize(size);
    doc.setTextColor(color[0], color[1], color[2]);
    const wrapped = doc.splitTextToSize(text, maxWidth);
    for (const w of wrapped) {
      if (y > pageHeight - margin) {
        doc.addPage();
        y = margin;
      }
      doc.text(w, margin, y);
      y += size + gap;
    }
  };

  const rule = () => {
    doc.setDrawColor(210, 214, 220);
    doc.line(margin, y, width - margin, y);
    y += 16;
  };

  // Render the imagery layers before laying out the PDF (async tile fetch).
  const layers = layersFor(a);
  const rendered = await Promise.all(
    layers.map(async (l) => {
      try {
        return { ...l, dataUrl: await renderScene(l.region, l.opts) };
      } catch {
        return { ...l, dataUrl: null as string | null };
      }
    }),
  );

  line(PRODUCT, { size: 20, bold: true, gap: 4 });
  line(DESCRIPTOR, { size: 10, color: [109, 129, 150], gap: 12 });
  rule();

  const payload = buildReportPayload(a);

  line("Report", { size: 8, bold: true, color: [109, 129, 150], gap: 2 });
  line(`${a.id} · Generated ${payload.generated_at}`, { size: 10, gap: 14 });

  line("Query", { size: 8, bold: true, color: [109, 129, 150], gap: 2 });
  line(a.query, { size: 12, bold: true, gap: 14 });

  line("Answer", { size: 8, bold: true, color: [109, 129, 150], gap: 2 });
  line(a.answer, { size: 11, gap: 14 });

  // Visual evidence — embedded satellite imagery + analytical layers.
  line("Visual evidence", { size: 8, bold: true, color: [109, 129, 150], gap: 8 });
  const cols = rendered.length >= 2 ? 2 : 1;
  const gap = 12;
  const imgW = (maxWidth - gap * (cols - 1)) / cols;
  const imgH = imgW; // square mosaic
  if (y + imgH + 22 > pageHeight - margin) {
    doc.addPage();
    y = margin;
  }
  const rowTop = y;
  rendered.forEach((r, i) => {
    const col = i % cols;
    const x = margin + col * (imgW + gap);
    if (r.dataUrl) {
      doc.addImage(r.dataUrl, "JPEG", x, rowTop, imgW, imgH);
    } else {
      doc.setFillColor(232, 235, 238);
      doc.rect(x, rowTop, imgW, imgH, "F");
      doc.setFont("helvetica", "normal");
      doc.setFontSize(9);
      doc.setTextColor(109, 129, 150);
      doc.text("Imagery unavailable", x + imgW / 2, rowTop + imgH / 2, { align: "center" });
    }
    doc.setDrawColor(210, 214, 220);
    doc.rect(x, rowTop, imgW, imgH);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(109, 129, 150);
    doc.text(r.caption, x + 2, rowTop + imgH + 10);
  });
  y = rowTop + imgH + 24;

  line("Input information", { size: 8, bold: true, color: [109, 129, 150], gap: 2 });
  line(`Type: ${payload.input.type}`, { gap: 4 });
  line(`Format: ${payload.input.format}    CRS: ${payload.input.crs}`, { gap: 14 });

  line("Analysis information", { size: 8, bold: true, color: [109, 129, 150], gap: 2 });
  line(`Analysis type: ${a.task}`, { gap: 4 });
  line(`Confidence: ${a.confidence}`, { gap: 14 });

  line("Execution trace", { size: 8, bold: true, color: [109, 129, 150], gap: 2 });
  line(`Task: ${payload.execution_trace.task}`, { gap: 4 });
  line(`Models / tools: ${payload.execution_trace.models}`, { gap: 4 });
  line(`Outputs: ${payload.execution_trace.outputs}`, { gap: 4 });
  line(`Timestamp: ${payload.execution_trace.timestamp}`, { gap: 14 });

  if (payload.warnings.length > 0) {
    line("Warnings", { size: 8, bold: true, color: [176, 90, 40], gap: 2 });
    for (const w of payload.warnings) line(w, { color: [176, 90, 40], gap: 4 });
    y += 8;
  }

  rule();
  line(
    "Observable execution metadata only. Internal model reasoning is not exposed. Demonstration report — sample data.",
    { size: 8, color: [109, 129, 150] },
  );

  doc.save(reportFileName(a, "pdf"));
}

/** Download the execution trace / full report payload as JSON. */
export function downloadReportJson(a: Analysis) {
  const blob = new Blob([JSON.stringify(buildReportPayload(a), null, 2)], {
    type: "application/json",
  });
  triggerDownload(blob, reportFileName(a, "json"));
}
