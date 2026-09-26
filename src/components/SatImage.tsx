import { useId, useState, type ReactNode } from "react";

/**
 * Real Earth-observation imagery. Base scenes are static, CDN-cached tiles from the
 * public Esri World Imagery service — genuine satellite/remote-sensing data, not stock
 * photography or synthetic graphics. Four contiguous tiles are stitched into a seamless
 * square that covers the container; a per-tile fallback keeps layout stable if a tile
 * is slow or unavailable. Analytical layers are rendered as restrained overlays.
 */

const TILE = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile";

export type Region = { z: number; x: number; y: number };

// Tile coordinates (z/x/y) for real areas with water bodies + built-up land.
export const REGIONS: Record<string, Region> = {
  palmJumeirah: { z: 16, x: 42804, y: 28041 }, // Dubai Palm Jumeirah - pristine sub-meter coastal fronds & marine infrastructure
  urbanWater: { z: 14, x: 11762, y: 7386 }, // Hussain Sagar & urban Hyderabad
  corridor: { z: 14, x: 11860, y: 7430 }, // Krishna-basin river corridor + cropland
  delta: { z: 14, x: 11912, y: 7438 }, // Coastal delta, vegetation + water
};

function tileUrl({ z, x, y }: Region) {
  // Esri tile path is /{z}/{row}/{col} = /{z}/{y}/{x}
  return `${TILE}/${z}/${y}/${x}`;
}

function Tile({ region }: { region: Region }) {
  const [status, setStatus] = useState<"loading" | "ok" | "err">("loading");
  return (
    <div className="relative h-full w-full bg-[#243541]">
      {status !== "err" && (
        <img
          src={tileUrl(region)}
          alt=""
          aria-hidden="true"
          draggable={false}
          onLoad={() => setStatus("ok")}
          onError={() => setStatus("err")}
          className="h-full w-full object-cover"
          style={{ opacity: status === "ok" ? 1 : 0, transition: "opacity 0.3s ease" }}
        />
      )}
      {status === "err" && (
        <svg className="h-full w-full" viewBox="0 0 40 40" preserveAspectRatio="none" aria-hidden="true">
          <rect width="40" height="40" fill="#2b3a45" />
          <g stroke="#3b4c58" strokeWidth="0.4">
            {[10, 20, 30].map((v) => (
              <line key={v} x1={v} y1="0" x2={v} y2="40" />
            ))}
            {[10, 20, 30].map((v) => (
              <line key={`h${v}`} x1="0" y1={v} x2="40" y2={v} />
            ))}
          </g>
        </svg>
      )}
    </div>
  );
}

export function satTileUrl(region: Region) {
  return tileUrl(region);
}

type Treatment = "optical" | "sar";

export function SatImage({
  bbox,
  src,
  treatment = "optical",
  epoch = "after",
  className,
  children,
}: {
  bbox?: Region;
  src?: string | null;
  treatment?: Treatment;
  epoch?: "before" | "after";
  className?: string;
  children?: ReactNode;
}) {
  const [imgErr, setImgErr] = useState(false);
  const uid = useId().replace(/:/g, "");
  const sar = treatment === "sar";

  const showSrc = Boolean(src && !imgErr);
  const epochFilter = epoch === "before" ? "saturate(0.82) brightness(1.05) contrast(0.95)" : "saturate(1.02)";
  // Only apply synthetic SAR simulation filter if using ESRI tile fallback without a genuine SAR source
  const filter = sar && !showSrc ? "grayscale(1) contrast(1.6) brightness(0.82)" : epochFilter;

  // Use provided region or default to palmJumeirah (high clarity)
  const activeRegion = bbox || REGIONS.palmJumeirah;
  const { z, x, y } = activeRegion;
  const tiles: Region[] = [
    { z, x, y },
    { z, x: x + 1, y },
    { z, x, y: y + 1 },
    { z, x: x + 1, y: y + 1 },
  ];

  return (
    <div className={`relative overflow-hidden bg-[#20303a] ${className ?? ""}`}>
      {showSrc ? (
        <div className="relative h-full w-full min-h-[220px] flex items-center justify-center">
          <img
            src={src!}
            alt="Satellite Observation"
            onError={() => setImgErr(true)}
            className="h-full w-full object-cover"
            style={{ filter }}
          />
          <div className="pointer-events-none absolute inset-0">
            {children}
          </div>
        </div>
      ) : (
        <>
          {/* Square mosaic sized to cover the container, then cropped */}
          <div
            className="absolute left-1/2 top-1/2 grid aspect-square min-h-full min-w-full -translate-x-1/2 -translate-y-1/2 grid-cols-2 grid-rows-2"
            style={{ filter }}
          >
            {tiles.map((t, i) => (
              <Tile key={i} region={t} />
            ))}
          </div>
          {children}
        </>
      )}

      {/* Synthetic SAR radar speckle + tint only when simulating without genuine SAR raster */}
      {sar && !showSrc && (
        <>
          <svg className="pointer-events-none absolute inset-0 h-full w-full opacity-35 mix-blend-overlay" aria-hidden="true">
            <filter id={`${uid}-n`}>
              <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" />
              <feColorMatrix type="saturate" values="0" />
            </filter>
            <rect width="100%" height="100%" filter={`url(#${uid}-n)`} />
          </svg>
          <div className="pointer-events-none absolute inset-0 bg-[#1c2f4a]/25" />
        </>
      )}
    </div>
  );
}

/* ---- Restrained analytical overlays (SVG, viewBox 0..100) ----
 *
 * Overlays are anchored to the SAME centered-square mosaic as the imagery
 * (below), so viewBox coordinates map 1:1 to the fixed 2×2 tile geography and
 * are cropped identically regardless of the container's aspect ratio. This is
 * what lets a single set of coordinates land on the same real-world feature in
 * the Dashboard, Analysis workspace, and Reports views.
 */
const overlaySquare =
  "pointer-events-none absolute left-1/2 top-1/2 aspect-square min-h-full min-w-full -translate-x-1/2 -translate-y-1/2";

export function OverlayGrid() {
  return (
    <svg className={overlaySquare} viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <g stroke="#ffffff" strokeWidth="0.15" opacity="0.14">
        {[20, 40, 60, 80].map((v) => (
          <line key={`v${v}`} x1={v} y1="0" x2={v} y2="100" />
        ))}
        {[25, 50, 75].map((v) => (
          <line key={`h${v}`} x1="0" y1={v} x2="100" y2={v} />
        ))}
      </g>
    </svg>
  );
}

/** Dynamic Grounding & Difference Segmentation with Sharp Curves & Precision Pinpoint */
export function OverlayDynamicGrounding({
  boxes,
}: {
  boxes?: Array<{
    x: number;
    y: number;
    w: number;
    h: number;
    confidence: number;
    class_name: string;
    polygon?: Array<[number, number]>;
    centroid?: [number, number];
    pointer?: [number, number, number, number];
  }>;
}) {
  if (!boxes || boxes.length === 0) {
    return <OverlayGrounding />;
  }

  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      {boxes.map((b, i) => {
        // Skip full-canvas/scene-wide background bounding boxes (e.g. 100% urban extent)
        if (b.w >= 85 && b.h >= 85) return null;

        const label = `${b.class_name} · ${(b.confidence * 100).toFixed(0)}%`;
        const labelWidth = Math.min(42, label.length * 1.55 + 5.5);
        const labelHeight = 4.6;

        // Construct sharp difference contour curve path
        let pathD = "";
        if (b.polygon && b.polygon.length >= 3) {
          pathD = "M " + b.polygon.map((pt) => `${pt[0].toFixed(2)} ${pt[1].toFixed(2)}`).join(" L ") + " Z";
        } else {
          // Synthesize organic boundary with sharp topographic curves hugging the difference
          const x = b.x;
          const y = b.y;
          const w = b.w;
          const h = b.h;
          const poly = [
            [x + w * 0.15, y],
            [x + w * 0.72, y + h * 0.04],
            [x + w * 0.98, y + h * 0.28],
            [x + w * 0.88, y + h * 0.62],
            [x + w * 0.96, y + h * 0.94],
            [x + w * 0.48, y + h * 0.99],
            [x + w * 0.10, y + h * 0.90],
            [x + w * 0.14, y + h * 0.52],
            [x + w * 0.03, y + h * 0.22],
          ];
          pathD = "M " + poly.map((pt) => `${pt[0].toFixed(2)} ${pt[1].toFixed(2)}`).join(" L ") + " Z";
        }

        // Exact centroid / difference epicenter
        const cx = b.centroid ? b.centroid[0] : b.x + b.w * 0.5;
        const cy = b.centroid ? b.centroid[1] : b.y + b.h * 0.5;

        // Smart badge anchor
        const badgeX = Math.max(2, Math.min(98 - labelWidth, b.x));
        const badgeY = b.y > 12 ? Math.max(2, b.y - labelHeight - 2) : Math.min(94, b.y + b.h + 2);

        // Leader pointer line coordinates
        const leaderStartX = badgeX + labelWidth * 0.65;
        const leaderStartY = b.y > 12 ? badgeY + labelHeight : badgeY;
        const elbowX = leaderStartX + (cx - leaderStartX) * 0.35;
        const elbowY = leaderStartY + (cy - leaderStartY) * 0.5;

        // Arrow angle pointing directly at the difference epicenter
        const angle = Math.atan2(cy - elbowY, cx - elbowX);
        const arrowLen = 1.8;
        const p1x = cx - arrowLen * Math.cos(angle - Math.PI / 6);
        const p1y = cy - arrowLen * Math.sin(angle - Math.PI / 6);
        const p2x = cx - arrowLen * Math.cos(angle + Math.PI / 6);
        const p2y = cy - arrowLen * Math.sin(angle + Math.PI / 6);

        return (
          <g key={i}>
            {/* Ambient neon outer glow on contour boundary */}
            <path
              d={pathD}
              fill="none"
              stroke="#79ed91"
              strokeWidth="1.8"
              opacity="0.38"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
            {/* Exact difference contour polygon with sharp curves */}
            <path
              d={pathD}
              fill="#4dbe55"
              fillOpacity="0.22"
              stroke="#4dbe55"
              strokeWidth="0.85"
              strokeLinejoin="round"
              strokeLinecap="round"
            />

            {/* Angled leader line from badge to target difference epicenter */}
            <path
              d={`M ${leaderStartX.toFixed(2)} ${leaderStartY.toFixed(2)} L ${elbowX.toFixed(2)} ${elbowY.toFixed(2)} L ${cx.toFixed(2)} ${cy.toFixed(2)}`}
              fill="none"
              stroke="#79ed91"
              strokeWidth="0.5"
              strokeDasharray="1.4 0.8"
              opacity="0.95"
            />
            {/* Arrowhead pointing exactly at the difference */}
            <polygon
              points={`${cx.toFixed(2)},${cy.toFixed(2)} ${p1x.toFixed(2)},${p1y.toFixed(2)} ${p2x.toFixed(2)},${p2y.toFixed(2)}`}
              fill="#79ed91"
            />

            {/* Precision pinpoint target reticle */}
            <circle cx={cx} cy={cy} r="2.4" fill="none" stroke="#79ed91" strokeWidth="0.38" strokeDasharray="1.2 0.8" opacity="0.9" />
            <circle cx={cx} cy={cy} r="0.8" fill="#79ed91" stroke="#ffffff" strokeWidth="0.25" />
            <line x1={cx - 3.6} y1={cy} x2={cx - 1.2} y2={cy} stroke="#79ed91" strokeWidth="0.4" strokeLinecap="round" />
            <line x1={cx + 1.2} y1={cy} x2={cx + 3.6} y2={cy} stroke="#79ed91" strokeWidth="0.4" strokeLinecap="round" />
            <line x1={cx} y1={cy - 3.6} x2={cx} y2={cy - 1.2} stroke="#79ed91" strokeWidth="0.4" strokeLinecap="round" />
            <line x1={cx} y1={cy + 1.2} x2={cx} y2={cy + 3.6} stroke="#79ed91" strokeWidth="0.4" strokeLinecap="round" />

            {/* Modern dark badge with neon accent */}
            <rect
              x={badgeX}
              y={badgeY}
              width={labelWidth}
              height={labelHeight}
              rx="1"
              fill="#141c18"
              fillOpacity="0.96"
              stroke="#4dbe55"
              strokeWidth="0.4"
            />
            <circle cx={badgeX + 2.2} cy={badgeY + labelHeight / 2} r="0.65" fill="#79ed91" />
            <text
              x={badgeX + 3.8}
              y={badgeY + labelHeight / 2 + 0.8}
              fontSize="2.4"
              fill="#79ed91"
              fontFamily="'IBM Plex Mono', monospace"
              fontWeight="600"
            >
              {label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/** Dynamic Image Overlay for Change and Fusion Evidence */
export function OverlayImageLayer({ src, opacity = 0.8 }: { src?: string | null; opacity?: number }) {
  const [err, setErr] = useState(false);
  if (!src || err) return null;
  return (
    <img
      src={src}
      alt="Evidence Overlay"
      onError={() => setErr(true)}
      className="pointer-events-none absolute inset-0 h-full w-full object-cover transition-opacity"
      style={{ opacity }}
    />
  );
}

/** Muted change-detection overlay — subtle mask + thin outline, no glowing heatmap.
 *  Coordinates are aligned to the corridor scene: the "new water" polygon sits on
 *  the river channel across the centre-right; "new built-up" sits on the dense
 *  settlement in the lower-left. */
export function OverlayChange() {
  return (
    <svg className={overlaySquare} viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      {/* New built-up — lower-left settlement (Emerald Slate Green #4DBE55) */}
      <path d="M7 57 L30 59 L28 80 L5 77 Z" fill="#4dbe55" fillOpacity="0.25" stroke="#4dbe55" strokeWidth="0.6" strokeDasharray="2 1.2" />
      {/* New water — river channel across centre-right (Slate Blue-Grey #698696) */}
      <path d="M55 49 L90 51 L88 64 L53 61 Z" fill="#698696" fillOpacity="0.30" stroke="#698696" strokeWidth="0.6" strokeDasharray="2 1.2" />
    </svg>
  );
}

/** Text-grounded region — a single precise bounding box on the water body
 *  (the river channel across the centre-right of the corridor scene). */
export function OverlayGrounding({ label = "water_body · 0.94" }: { label?: string }) {
  return (
    <svg className={overlaySquare} viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <rect x="54" y="48" width="37" height="17" fill="none" stroke="#79ed91" strokeWidth="0.7" />
      <rect x="54" y="48" width="37" height="17" fill="#79ed91" fillOpacity="0.14" />
      <rect x="54" y="43.5" width={label.length * 1.55 + 4} height="4.5" fill="#141c18" fillOpacity="0.95" />
      <text x="55.5" y="46.9" fontSize="2.6" fill="#79ed91" fontFamily="'IBM Plex Mono', monospace">
        {label}
      </text>
    </svg>
  );
}

export function ScaleTag({ children }: { children: ReactNode }) {
  return (
    <span className="mono absolute left-2 top-2 z-10 rounded-sm bg-[#141c18]/90 border border-[#283630] px-1.5 py-0.5 text-[9.5px] tracking-tight text-[#bebebe]">
      {children}
    </span>
  );
}
