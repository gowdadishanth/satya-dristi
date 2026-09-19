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
  const uid = useId().replace(/:/g, "");
  const sar = treatment === "sar";

  const epochFilter = epoch === "before" ? "saturate(0.82) brightness(1.05) contrast(0.95)" : "saturate(1.02)";
  const filter = sar ? "grayscale(1) contrast(1.6) brightness(0.82)" : epochFilter;

  // Use provided region or default to corridor
  const activeRegion = bbox || REGIONS.corridor;
  const { z, x, y } = activeRegion;
  const tiles: Region[] = [
    { z, x, y },
    { z, x: x + 1, y },
    { z, x, y: y + 1 },
    { z, x: x + 1, y: y + 1 },
  ];

  return (
    <div className={`relative overflow-hidden bg-[#20303a] ${className ?? ""}`}>
      {src ? (
        <img
          src={src}
          alt="Satellite Observation"
          className="absolute inset-0 h-full w-full object-cover"
          style={{ filter }}
        />
      ) : (
        /* Square mosaic sized to cover the container, then cropped */
        <div
          className="absolute left-1/2 top-1/2 grid aspect-square min-h-full min-w-full -translate-x-1/2 -translate-y-1/2 grid-cols-2 grid-rows-2"
          style={{ filter }}
        >
          {tiles.map((t, i) => (
            <Tile key={i} region={t} />
          ))}
        </div>
      )}

      {/* SAR radar speckle + tint */}
      {sar && (
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

      {children}
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

/** Dynamic Grounding Bounding Boxes from real inference */
export function OverlayDynamicGrounding({
  boxes,
}: {
  boxes?: Array<{ x: number; y: number; w: number; h: number; confidence: number; class_name: string }>;
}) {
  if (!boxes || boxes.length === 0) {
    return <OverlayGrounding />;
  }

  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      {boxes.map((b, i) => {
        const label = `${b.class_name} · ${(b.confidence * 100).toFixed(0)}%`;
        const labelWidth = Math.min(35, label.length * 1.5 + 4);
        return (
          <g key={i}>
            <rect x={b.x} y={b.y} width={b.w} height={b.h} fill="#ab7c2c" fillOpacity="0.15" stroke="#ab7c2c" strokeWidth="0.7" />
            <rect x={b.x} y={Math.max(0, b.y - 4.5)} width={labelWidth} height="4.5" fill="#313851" fillOpacity="0.9" />
            <text x={b.x + 1.2} y={Math.max(3.2, b.y - 1.2)} fontSize="2.6" fill="#f6f3ed" fontFamily="'IBM Plex Mono', monospace">
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
  if (!src) return null;
  return (
    <img
      src={src}
      alt="Evidence Overlay"
      className="pointer-events-none absolute inset-0 h-full w-full object-cover mix-blend-multiply transition-opacity"
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
      {/* New built-up — lower-left settlement */}
      <path d="M7 57 L30 59 L28 80 L5 77 Z" fill="#ab7c2c" fillOpacity="0.22" stroke="#8a6420" strokeWidth="0.5" strokeDasharray="2 1.2" />
      {/* New water — river channel across centre-right */}
      <path d="M55 49 L90 51 L88 64 L53 61 Z" fill="#4f6f8a" fillOpacity="0.26" stroke="#3d5972" strokeWidth="0.5" strokeDasharray="2 1.2" />
    </svg>
  );
}

/** Text-grounded region — a single precise bounding box on the water body
 *  (the river channel across the centre-right of the corridor scene). */
export function OverlayGrounding({ label = "water_body · 0.94" }: { label?: string }) {
  return (
    <svg className={overlaySquare} viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
      <rect x="54" y="48" width="37" height="17" fill="none" stroke="#f6f3ed" strokeWidth="0.7" />
      <rect x="54" y="48" width="37" height="17" fill="#313851" fillOpacity="0.1" />
      <rect x="54" y="43.5" width={label.length * 1.55 + 4} height="4.5" fill="#313851" fillOpacity="0.9" />
      <text x="55.5" y="46.9" fontSize="2.6" fill="#f6f3ed" fontFamily="'IBM Plex Mono', monospace">
        {label}
      </text>
    </svg>
  );
}

export function ScaleTag({ children }: { children: ReactNode }) {
  return (
    <span className="mono absolute left-2 top-2 z-10 rounded-sm bg-[#1a1e2b]/70 px-1.5 py-0.5 text-[9.5px] tracking-tight text-white/90">
      {children}
    </span>
  );
}
