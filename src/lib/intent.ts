export type Mode = "single" | "fusion" | "temporal";

export type DetectedIntent = {
  mode: Mode;
  taskName: string;
  sensorBadge: string;
  reason: string;
};

function matchesKeyword(text: string, keyword: string): boolean {
  if (keyword.endsWith("penetrat") || keyword.endsWith("encroach")) {
    return new RegExp(`\\b${keyword}`, "i").test(text);
  }
  return new RegExp(`\\b${keyword.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&")}\\b`, "i").test(text);
}

export function detectQueryIntent(q: string): DetectedIntent {
  const query = (q || "").toLowerCase();

  // 1. SAR / Radar / All-Weather / Penetration Intent
  const sarKeywords = [
    "sar", "radar", "backscatter", "sigma0", "sigma 0", "decibel", "db",
    "cloud", "penetrat", "monsoon", "night", "storm", "all-weather",
    "roughness", "dielectric", "metallic", "vessel", "ship", "microwave",
    "vv", "vh", "polarimetric"
  ];
  if (sarKeywords.some((k) => matchesKeyword(query, k))) {
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
  if (changeKeywords.some((k) => matchesKeyword(query, k))) {
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
  if (groundingKeywords.some((k) => matchesKeyword(query, k))) {
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
