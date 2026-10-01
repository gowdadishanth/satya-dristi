// Earth observation geometry and tile helper utilities

export const WAYBACK_YEAR_RELEASES: Record<number, string> = {
  2014: "5844",
  2015: "28163",
  2016: "18966",
  2017: "25521",
  2018: "23448",
  2019: "4756",
  2020: "29260",
  2021: "26120",
  2022: "45134",
  2023: "56102",
  2024: "16453",
  2025: "13192",
  2026: "26334",
};

export function getWaybackTileUrl(targetYear: number): string {
  const releaseId = WAYBACK_YEAR_RELEASES[targetYear] || WAYBACK_YEAR_RELEASES[2024];
  return `https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/${releaseId}/{z}/{y}/{x}`;
}

export const isSarScene = (s?: { sensor?: string; collection?: string; platform?: string; scene_id?: string } | null): boolean => {
  if (!s) return false;
  const sensor = (s.sensor || "").toLowerCase();
  const col = (s.collection || "").toLowerCase();
  const plat = (s.platform || "").toLowerCase();
  const id = (s.scene_id || "").toLowerCase();
  return sensor.includes("sar") || col.includes("sentinel-1") || col.includes("grd") || plat.includes("sentinel-1") || id.startsWith("s1");
};
