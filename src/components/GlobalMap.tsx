import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Badge, Button, cn } from "./ui";
import {
  IconSearch, IconOptical, IconSar, IconCheck, IconZoomIn, IconZoomOut,
  IconReset, IconGlobe
} from "./icons";
import { api, type Scene, type AOIPreview } from "../lib/api";

type GlobalMapProps = {
  onSelectSceneAndAOI: (scene: Scene, aoi: AOIPreview, secondScene?: Scene) => void;
  mode: "single" | "fusion" | "temporal";
};

const PRESETS = [
  { name: "Hyderabad", fullName: "Hyderabad / Hussain Sagar", lat: 17.424, lon: 78.474, zoom: 12 },
  { name: "Krishna River", fullName: "Krishna River Corridor", lat: 16.512, lon: 80.621, zoom: 12 },
  { name: "Godavari Delta", fullName: "Godavari Coastal Delta", lat: 16.983, lon: 82.241, zoom: 11 },
  { name: "Suez Canal", fullName: "Suez Canal Corridor", lat: 30.585, lon: 32.265, zoom: 11 },
  { name: "San Francisco", fullName: "San Francisco Bay", lat: 37.774, lon: -122.419, zoom: 11 },
  { name: "Rotterdam", fullName: "Rotterdam Port", lat: 51.924, lon: 4.477, zoom: 12 },
];

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

export function GlobalMap({ onSelectSceneAndAOI, mode }: GlobalMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const baseTileLayerRef = useRef<L.TileLayer | null>(null);
  const sceneOverlayRef = useRef<L.ImageOverlay | null>(null);
  const aoiLayerRef = useRef<L.Rectangle | null>(null);
  const footprintsLayerRef = useRef<L.LayerGroup | null>(null);
  const clickMarkerRef = useRef<L.CircleMarker | null>(null);
  const suppressNextClickRef = useRef<boolean>(false);

  // Search & Navigation State
  const [searchQuery, setSearchQuery] = useState("");
  const [locationName, setLocationName] = useState("Hyderabad, Telangana");
  const [currentCoords, setCurrentCoords] = useState<{ lat: number; lon: number }>({ lat: 17.424, lon: 78.474 });

  // Date & Sensor Filtering (2016-2026)
  const [year, setYear] = useState<number>(2024);
  const [sensor, setSensor] = useState<"optical" | "sar">("optical");
  const [cloudCoverMax, setCloudCoverMax] = useState<number>(30);

  // Dual-scene filter state for temporal mode (default Baseline: 2019, Target: 2024)
  const [temporalTarget, setTemporalTarget] = useState<"before" | "after">("before");
  const [beforeYear, setBeforeYear] = useState<number>(2019);
  const [afterYear, setAfterYear] = useState<number>(2024);
  const [beforeScenes, setBeforeScenes] = useState<Scene[]>([]);
  const [afterScenes, setAfterScenes] = useState<Scene[]>([]);
  // Dual-scene filter state for fusion mode
  const [fusionTarget, setFusionTarget] = useState<"optical" | "sar">("optical");
  const [sarScenes, setSarScenes] = useState<Scene[]>([]);
  const [showSceneOverlay, setShowSceneOverlay] = useState<boolean>(true);

  // Scene & AOI State
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [selectedScene, setSelectedScene] = useState<Scene | null>(null);
  const [secondaryScene, setSecondaryScene] = useState<Scene | null>(null);
  const [aoi, setAoi] = useState<AOIPreview | null>(null);

  const [searching, setSearching] = useState(false);
  const [drawingAoi, setDrawingAoi] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Request sequence tracking to discard stale concurrent preview requests
  const aoiRequestIdRef = useRef<number>(0);

  // When active analysis mode changes, preserve primary AOI and scene selection
  // so dynamic AI query routing does not wipe out the user's selected map region
  useEffect(() => {
    if (mode === "single") {
      setSecondaryScene(null);
    }
  }, [mode]);

  // Active viewing year on the map
  const activeViewingYear = mode === "temporal"
    ? (temporalTarget === "before" ? beforeYear : afterYear)
    : year;

  // Active scene for current view
  const activeScene = mode === "temporal"
    ? (temporalTarget === "before" ? secondaryScene : selectedScene)
    : selectedScene;

  // Dynamically update map's satellite tile layer when viewing year changes
  useEffect(() => {
    if (!mapRef.current || !baseTileLayerRef.current) return;
    const tileUrl = getWaybackTileUrl(activeViewingYear);
    baseTileLayerRef.current.setUrl(tileUrl);
  }, [activeViewingYear]);

  // Overlay authentic satellite scene quicklook when available
  useEffect(() => {
    if (!mapRef.current) return;

    if (sceneOverlayRef.current) {
      mapRef.current.removeLayer(sceneOverlayRef.current);
      sceneOverlayRef.current = null;
    }

    if (showSceneOverlay && activeScene?.preview_url && activeScene.bbox && activeScene.bbox.length === 4) {
      const bounds = L.latLngBounds(
        [activeScene.bbox[1], activeScene.bbox[0]],
        [activeScene.bbox[3], activeScene.bbox[2]]
      );
      try {
        sceneOverlayRef.current = L.imageOverlay(activeScene.preview_url, bounds, {
          opacity: 0.85,
          interactive: false,
        }).addTo(mapRef.current);
      } catch (err) {
        console.warn("Failed to overlay scene preview:", err);
      }
    }
  }, [activeScene, showSceneOverlay]);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [17.424, 78.474],
      zoom: 12,
      zoomControl: false,
      worldCopyJump: true,
      maxBounds: [
        [-85.0511, -180],
        [85.0511, 180],
      ],
      maxBoundsViscosity: 1.0,
    });

    // Satellite imagery base tiles (Esri Wayback for chosen active observation year)
    const initialYear = mode === "temporal" ? (temporalTarget === "before" ? beforeYear : afterYear) : year;
    const tileLayer = L.tileLayer(getWaybackTileUrl(initialYear), {
      attribution: `Satellite Tiles © Esri Wayback (${initialYear})`,
      maxZoom: 18,
    }).addTo(map);
    baseTileLayerRef.current = tileLayer;

    footprintsLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;

    // Track map center movement to keep coordinates accurately updated and wrapped
    map.on("moveend", () => {
      const center = map.getCenter().wrap();
      const lat = Number(Math.max(-85, Math.min(85, center.lat)).toFixed(4));
      const lon = Number(((((center.lng + 180) % 360 + 360) % 360) - 180).toFixed(4));
      setCurrentCoords({ lat, lon });
    });

    // Click anywhere on map to select location
    map.on("click", async (e: L.LeafletMouseEvent) => {
      if (suppressNextClickRef.current) {
        suppressNextClickRef.current = false;
        return;
      }

      const wrapped = e.latlng.wrap();
      const lat = Number(Math.max(-85, Math.min(85, wrapped.lat)).toFixed(4));
      const lon = Number(((((wrapped.lng + 180) % 360 + 360) % 360) - 180).toFixed(4));
      setCurrentCoords({ lat, lon });

      if (clickMarkerRef.current) {
        map.removeLayer(clickMarkerRef.current);
      }
      clickMarkerRef.current = L.circleMarker([lat, lon], {
        radius: 5,
        color: "#4dbe55",
        fillColor: "#79ed91",
        fillOpacity: 0.95,
      }).addTo(map);

      // Center AOI box around clicked point with strict WGS84 containment
      const dLat = 0.03;
      const dLon = 0.03;
      const south = Math.max(-85, lat - dLat);
      const north = Math.min(85, lat + dLat);
      const west = Math.max(-180, lon - dLon);
      const east = Math.min(180, lon + dLon);
      const newBounds = L.latLngBounds([south, west], [north, east]);
      createAoiFromBounds(newBounds);

      // Reverse geocode to get human place name
      try {
        const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
        const data = await res.json();
        if (data && data.display_name) {
          const parts = data.display_name.split(",");
          setLocationName(parts.slice(0, 2).join(",").trim());
        }
      } catch {
        setLocationName(`${lat}° N, ${lon}° E`);
      }
    });

    // Create default initial AOI
    createAoiFromBounds(map.getBounds().pad(-0.25));
    setTimeout(() => {
      map.invalidateSize();
    }, 150);

    return () => {
      map.remove();
      mapRef.current = null;
      baseTileLayerRef.current = null;
      sceneOverlayRef.current = null;
    };
  }, []);

  // Update bounds and compute AOI geometry
  const createAoiFromBounds = async (bounds: L.LatLngBounds) => {
    if (!mapRef.current) return;

    // CR-GEO-02: Increment request sequence ID to discard stale concurrent preview responses
    const currentReqId = ++aoiRequestIdRef.current;

    // CR-GEO-01: Clear stale scene results and selections immediately when new AOI is initiated
    setSelectedScene(null);
    setSecondaryScene(null);
    setScenes([]);
    setBeforeScenes([]);
    setAfterScenes([]);
    setSarScenes([]);
    if (footprintsLayerRef.current) {
      footprintsLayerRef.current.clearLayers();
    }

    if (aoiLayerRef.current) {
      mapRef.current.removeLayer(aoiLayerRef.current);
    }

    // Strict WGS84 range validation & normalization to prevent -180/+180 overflow from Leaflet
    const normalizeLng = (lng: number) => {
      let l = (((lng + 180) % 360 + 360) % 360) - 180;
      if (l === -180 && lng > 0) l = 180;
      return l;
    };
    const clampLat = (lat: number) => Math.max(-85.0511, Math.min(85.0511, lat));

    let west = bounds.getWest();
    let east = bounds.getEast();
    let south = clampLat(bounds.getSouth());
    let north = clampLat(bounds.getNorth());

    if (west < -180 || west > 180 || east < -180 || east > 180) {
      west = normalizeLng(west);
      east = normalizeLng(east);
    }
    if (west >= east) {
      if (west > east) {
        west = Math.max(-180, east - 0.1);
      } else {
        west = Math.max(-180, east - 0.05);
      }
    }
    if (south >= north) {
      north = Math.min(85, south + 0.05);
    }

    const safeBounds = L.latLngBounds([south, west], [north, east]);

    const rect = L.rectangle(safeBounds, {
      color: "#4dbe55",
      weight: 2,
      dashArray: "4 4",
      fillColor: "#79ed91",
      fillOpacity: 0.16,
    }).addTo(mapRef.current);

    aoiLayerRef.current = rect;

    const bbox = [
      Number(west.toFixed(4)),
      Number(south.toFixed(4)),
      Number(east.toFixed(4)),
      Number(north.toFixed(4)),
    ];

    try {
      const preview = await api.earth.previewAOI({ bbox });
      // Discard stale response if a newer request was dispatched
      if (currentReqId !== aoiRequestIdRef.current) {
        return;
      }
      setAoi(preview);
      setErrorMsg(null);
    } catch (err: any) {
      // Discard stale error if a newer request was dispatched
      if (currentReqId !== aoiRequestIdRef.current) {
        return;
      }
      setAoi(null);
      const rawMsg = err?.message || "";
      if (rawMsg.includes("Authorization") || rawMsg.includes("UNAUTHORIZED")) {
        setErrorMsg("Session expired or authentication required. Please sign in to query satellite imagery.");
      } else {
        setErrorMsg(rawMsg || "Invalid AOI bounds or AOI validation failed.");
      }
      if (aoiLayerRef.current && mapRef.current) {
        mapRef.current.removeLayer(aoiLayerRef.current);
        aoiLayerRef.current = null;
      }
    }
  };

  // Search Location by Name / Geocoding
  const handleSearchLocation = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim() || !mapRef.current) return;

    try {
      setErrorMsg(null);
      const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}&limit=1`);
      const data = await res.json();
      if (data && data.length > 0) {
        const lat = parseFloat(data[0].lat);
        const lon = parseFloat(data[0].lon);
        setLocationName(data[0].display_name.split(",").slice(0, 2).join(",").trim());
        setCurrentCoords({ lat, lon });
        mapRef.current.setView([lat, lon], 12);
        createAoiFromBounds(mapRef.current.getBounds().pad(-0.25));
      } else {
        setErrorMsg("Location not found. Enter city name or coordinates (e.g. 17.42, 78.47).");
      }
    } catch {
      setErrorMsg("Geocoding service unavailable.");
    }
  };

  // Search Real Satellite Scenes from Backend STAC
  // Search Real Satellite Scenes from Backend STAC
  const handleSearchScenes = async () => {
    if (!aoi) return;
    setSearching(true);
    setErrorMsg(null);

    const targetSensor = mode === "fusion"
      ? sensor
      : (sensor === "sar" ? "sar" : "optical");

    if (mode === "temporal") {
      try {
        const [foundBefore, foundAfter] = await Promise.all([
          api.earth.searchScenes({
            bbox: aoi.bbox,
            year: beforeYear,
            sensor: targetSensor,
            cloud_cover_max: targetSensor === "optical" ? cloudCoverMax : undefined,
            limit: 6,
          }),
          api.earth.searchScenes({
            bbox: aoi.bbox,
            year: afterYear,
            sensor: targetSensor,
            cloud_cover_max: targetSensor === "optical" ? cloudCoverMax : undefined,
            limit: 6,
          }),
        ]);

        setBeforeScenes(foundBefore);
        setAfterScenes(foundAfter);

        const bestBefore = foundBefore[0] || null;
        const bestAfter = foundAfter[0] || null;

        if (bestBefore) setSecondaryScene(bestBefore);
        if (bestAfter) setSelectedScene(bestAfter);

        if (bestAfter && aoi) {
          onSelectSceneAndAOI(bestAfter, aoi, bestBefore || undefined);
        } else if (bestBefore && aoi) {
          onSelectSceneAndAOI(bestBefore, aoi, undefined);
        }

        // Render footprints on map
        if (footprintsLayerRef.current && mapRef.current) {
          footprintsLayerRef.current.clearLayers();
          [...foundBefore, ...foundAfter].forEach((s) => {
            if (s.bbox && s.bbox.length === 4) {
              const b = L.latLngBounds([s.bbox[1], s.bbox[0]], [s.bbox[3], s.bbox[2]]);
              const isAfter = s.acquisition_datetime && s.acquisition_datetime.includes(String(afterYear));
              L.rectangle(b, {
                color: isAfter ? "#79ed91" : "#698696",
                weight: 1,
                dashArray: "2 2",
                fillOpacity: 0.08,
              }).addTo(footprintsLayerRef.current!);
            }
          });
        }
      } catch (err: any) {
        setErrorMsg(err.message || "No satellite scenes found for the selected years.");
        setBeforeScenes([]);
        setAfterScenes([]);
      } finally {
        setSearching(false);
      }
      return;
    }

    if (mode === "fusion") {
      try {
        const [foundOptical, foundSar] = await Promise.all([
          api.earth.searchScenes({
            bbox: aoi.bbox,
            year: year,
            sensor: "optical",
            cloud_cover_max: cloudCoverMax,
            limit: 6,
          }),
          api.earth.searchScenes({
            bbox: aoi.bbox,
            year: year,
            sensor: "sar",
            limit: 6,
          }),
        ]);

        setScenes(foundOptical);
        setSarScenes(foundSar);

        const bestOpt = foundOptical[0] || null;
        const bestSar = foundSar[0] || null;

        if (bestOpt) setSelectedScene(bestOpt);
        if (bestSar) setSecondaryScene(bestSar);

        if (bestOpt && aoi) {
          onSelectSceneAndAOI(bestOpt, aoi, bestSar || undefined);
        } else if (bestSar && aoi) {
          onSelectSceneAndAOI(bestSar, aoi, undefined);
        }

        // Render footprints on map: optical in green, sar in slate-blue
        if (footprintsLayerRef.current && mapRef.current) {
          footprintsLayerRef.current.clearLayers();
          [...foundOptical, ...foundSar].forEach((s) => {
            if (s.bbox && s.bbox.length === 4) {
              const b = L.latLngBounds([s.bbox[1], s.bbox[0]], [s.bbox[3], s.bbox[2]]);
              const isSar = isSarScene(s);
              L.rectangle(b, {
                color: isSar ? "#698696" : "#79ed91",
                weight: 1,
                dashArray: "2 2",
                fillOpacity: 0.08,
              }).addTo(footprintsLayerRef.current!);
            }
          });
        }
      } catch (err: any) {
        setErrorMsg(err.message || "No satellite scenes found for the selected area.");
        setScenes([]);
        setSarScenes([]);
      } finally {
        setSearching(false);
      }
      return;
    }

    try {
      const found = await api.earth.searchScenes({
        bbox: aoi.bbox,
        year: year,
        sensor: targetSensor,
        cloud_cover_max: targetSensor === "optical" ? cloudCoverMax : undefined,
        limit: 8,
      });

      setScenes(found);

      if (found.length > 0) {
        setSelectedScene(found[0]);
        if (aoi) {
          onSelectSceneAndAOI(found[0], aoi);
        }
      }

      // Render footprints on map
      if (footprintsLayerRef.current && mapRef.current) {
        footprintsLayerRef.current.clearLayers();
        found.forEach((s) => {
          if (s.bbox && s.bbox.length === 4) {
            const b = L.latLngBounds([s.bbox[1], s.bbox[0]], [s.bbox[3], s.bbox[2]]);
            L.rectangle(b, {
              color: isSarScene(s) ? "#698696" : "#79ed91",
              weight: 1,
              dashArray: "2 2",
              fillOpacity: 0.08,
            }).addTo(footprintsLayerRef.current!);
          }
        });
      }
    } catch (err: any) {
      setErrorMsg(err.message || "No scenes found for the selected criteria.");
      setScenes([]);
    } finally {
      setSearching(false);
    }
  };

  // Interactive Drag-to-Draw AOI
  const startDrawAoi = () => {
    if (!mapRef.current) return;
    setDrawingAoi(true);

    let startLatLng: L.LatLng | null = null;
    let tempRect: L.Rectangle | null = null;

    const onMouseDown = (e: L.LeafletMouseEvent) => {
      startLatLng = e.latlng.wrap();
      if (tempRect && mapRef.current) mapRef.current.removeLayer(tempRect);
      mapRef.current?.dragging.disable();
    };

    const onMouseMove = (e: L.LeafletMouseEvent) => {
      if (!startLatLng || !mapRef.current) return;
      const currentBounds = L.latLngBounds(startLatLng, e.latlng.wrap());
      if (!tempRect) {
        tempRect = L.rectangle(currentBounds, {
          color: "#4dbe55",
          weight: 2,
          dashArray: "4 4",
          fillColor: "#79ed91",
          fillOpacity: 0.2,
        }).addTo(mapRef.current);
      } else {
        tempRect.setBounds(currentBounds);
      }
    };

    const onMouseUp = (e: L.LeafletMouseEvent) => {
      if (!startLatLng || !mapRef.current) return;
      const finalBounds = L.latLngBounds(startLatLng, e.latlng.wrap());
      if (tempRect) mapRef.current.removeLayer(tempRect);

      suppressNextClickRef.current = true;
      setTimeout(() => {
        suppressNextClickRef.current = false;
      }, 300);

      createAoiFromBounds(finalBounds);
      mapRef.current.dragging.enable();
      setDrawingAoi(false);

      mapRef.current.off("mousedown", onMouseDown);
      mapRef.current.off("mousemove", onMouseMove);
      mapRef.current.off("mouseup", onMouseUp);
    };

    mapRef.current.on("mousedown", onMouseDown);
    mapRef.current.on("mousemove", onMouseMove);
    mapRef.current.on("mouseup", onMouseUp);
  };

  const clearAoi = () => {
    if (mapRef.current) {
      setLocationName("Hyderabad, Telangana");
      setCurrentCoords({ lat: 17.424, lon: 78.474 });
      mapRef.current.setView([17.424, 78.474], 12);
      createAoiFromBounds(mapRef.current.getBounds().pad(-0.25));
    }
  };

  const handleSelectScene = (scene: Scene) => {
    if (mode === "temporal") {
      if (temporalTarget === "before") {
        setSecondaryScene(scene);
        if (aoi) {
          onSelectSceneAndAOI(selectedScene || scene, aoi, scene);
        }
      } else {
        setSelectedScene(scene);
        if (aoi) {
          onSelectSceneAndAOI(scene, aoi, secondaryScene || undefined);
        }
      }
    } else if (mode === "fusion") {
      const isSar = isSarScene(scene);
      if (fusionTarget === "sar" || isSar) {
        setSecondaryScene(scene);
        if (selectedScene && aoi) {
          onSelectSceneAndAOI(selectedScene, aoi, scene);
        } else if (aoi) {
          onSelectSceneAndAOI(scene, aoi, undefined);
        }
      } else {
        setSelectedScene(scene);
        if (aoi) {
          onSelectSceneAndAOI(scene, aoi, secondaryScene || undefined);
        }
      }
    } else {
      setSelectedScene(scene);
      if (aoi) {
        onSelectSceneAndAOI(scene, aoi);
      }
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {/* 1. Header & Map Context Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-2.5">
        <div className="flex items-center gap-2">
          <IconGlobe className="h-4 w-4 text-accent" />
          <h2 className="text-[14px] font-semibold text-foreground tracking-tight">
            Global Earth Observation Explorer
          </h2>
          <Badge tone="accent">Copernicus &amp; AWS</Badge>
        </div>

        {/* Selected Location Strip */}
        <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
          <span className="font-medium text-foreground">{locationName}</span>
          <span className="text-border">·</span>
          <span className="mono">{currentCoords.lat}° N, {currentCoords.lon}° E</span>
          <span className="text-border">·</span>
          <span className="text-[color:var(--ok)] font-medium">Catalogue Active</span>
        </div>
      </div>

      {/* 2. Search & Filter Controls (TWO Clean, Uncramped Rows) */}
      <div className="space-y-2">
        {/* ROW 1: Location Search (Dominant) + Year + Sensor */}
        <div className="grid gap-2 sm:grid-cols-12">
          {/* Dominant Location Search Input */}
          <form onSubmit={handleSearchLocation} className={cn("relative", mode === "temporal" ? "sm:col-span-12 md:col-span-5" : "sm:col-span-12 md:col-span-6")}>
            <IconSearch className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search a place or coordinates (e.g. Hyderabad, Suez, 17.42, 78.47)…"
              className="w-full rounded-md border border-border bg-card py-2 pl-9 pr-3 text-[13px] leading-tight focus-ring placeholder:text-muted-foreground"
            />
          </form>

          {/* Year Dropdowns */}
          {mode === "temporal" ? (
            <>
              {/* Before Year Selector */}
              <div className="sm:col-span-6 md:col-span-2 flex items-center justify-between gap-1.5 rounded-md border border-border bg-card px-2.5 py-1.5 min-w-[105px]">
                <span className="mono text-[11px] uppercase tracking-wide font-semibold text-primary whitespace-nowrap">
                  Before:
                </span>
                <select
                  value={beforeYear}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    setBeforeYear(val);
                    setTemporalTarget("before");
                  }}
                  className="w-full bg-transparent text-[13px] font-medium outline-none text-foreground cursor-pointer"
                >
                  {[2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016].map((y) => (
                    <option key={y} value={y} className="bg-card text-foreground">{y}</option>
                  ))}
                </select>
              </div>

              {/* After Year Selector */}
              <div className="sm:col-span-6 md:col-span-2 flex items-center justify-between gap-1.5 rounded-md border border-border bg-card px-2.5 py-1.5 min-w-[105px]">
                <span className="mono text-[11px] uppercase tracking-wide font-semibold text-accent whitespace-nowrap">
                  After:
                </span>
                <select
                  value={afterYear}
                  onChange={(e) => {
                    const val = Number(e.target.value);
                    setAfterYear(val);
                    setTemporalTarget("after");
                  }}
                  className="w-full bg-transparent text-[13px] font-medium outline-none text-foreground cursor-pointer"
                >
                  {[2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016].map((y) => (
                    <option key={y} value={y} className="bg-card text-foreground">{y}</option>
                  ))}
                </select>
              </div>
            </>
          ) : (
            <div className="sm:col-span-6 md:col-span-3 flex items-center justify-between gap-1.5 rounded-md border border-border bg-card px-2.5 py-1.5 min-w-[105px]">
              <span className="mono text-[11px] uppercase tracking-wide text-muted-foreground whitespace-nowrap">
                Year:
              </span>
              <select
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                className="w-full bg-transparent text-[13px] font-medium outline-none text-foreground cursor-pointer"
              >
                {[2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016].map((y) => (
                  <option key={y} value={y} className="bg-card text-foreground">{y}</option>
                ))}
              </select>
            </div>
          )}

          {/* Sensor Selector / Fusion Mode Pill */}
          {mode === "fusion" ? (
            <div className="sm:col-span-12 md:col-span-3 flex items-center justify-center rounded-md border border-accent/40 bg-accent/10 px-2 py-1.5 text-[11.5px] font-semibold text-foreground gap-1.5 shadow-xs">
              <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
              <span>Multimodal: Optical + SAR</span>
            </div>
          ) : (
            <div className={cn("flex rounded-md border border-border bg-card p-0.5", mode === "temporal" ? "sm:col-span-12 md:col-span-3" : "sm:col-span-12 md:col-span-3")}>
              <button
                type="button"
                onClick={() => setSensor("optical")}
                className={cn(
                  "flex-1 rounded px-2.5 py-1 text-[12px] font-medium transition-colors",
                  sensor === "optical" ? "bg-primary text-primary-foreground font-semibold" : "text-muted-foreground hover:bg-muted"
                )}
              >
                Sentinel-2 Optical
              </button>
              <button
                type="button"
                onClick={() => setSensor("sar")}
                className={cn(
                  "flex-1 rounded px-2.5 py-1 text-[12px] font-medium transition-colors",
                  sensor === "sar" ? "bg-primary text-primary-foreground font-semibold" : "text-muted-foreground hover:bg-muted"
                )}
              >
                Sentinel-1 SAR
              </button>
            </div>
          )}
        </div>

        {/* ROW 2: Cloud Filter + Quick Presets + Search Scenes Action */}
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            {/* Cloud Cover Filter */}
            <div className="flex items-center gap-1.5 rounded-md border border-border bg-card px-2 py-1">
              <span className="mono text-[11px] uppercase tracking-wide text-muted-foreground">Cloud cover:</span>
              <select
                value={cloudCoverMax}
                onChange={(e) => setCloudCoverMax(Number(e.target.value))}
                className="bg-transparent text-[12px] font-medium outline-none text-foreground"
              >
                <option value={10} className="bg-card">&lt; 10%</option>
                <option value={20} className="bg-card">&lt; 20%</option>
                <option value={30} className="bg-card">&lt; 30%</option>
                <option value={50} className="bg-card">&lt; 50%</option>
                <option value={100} className="bg-card">Any (100%)</option>
              </select>
            </div>

            {/* Quick Presets */}
            <div className="hidden md:flex items-center gap-1">
              <span className="mono text-[11px] text-muted-foreground mr-1">Presets:</span>
              {PRESETS.map((p) => (
                <button
                  key={p.name}
                  type="button"
                  onClick={() => {
                    if (mapRef.current) {
                      setLocationName(p.fullName);
                      setCurrentCoords({ lat: p.lat, lon: p.lon });
                      mapRef.current.setView([p.lat, p.lon], p.zoom);
                      createAoiFromBounds(mapRef.current.getBounds().pad(-0.25));
                    }
                  }}
                  className="mono rounded border border-border/80 bg-card/60 px-2 py-0.5 text-[11px] text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                >
                  {p.name}
                </button>
              ))}
            </div>
          </div>

          {/* Search Scenes Primary Trigger */}
          <Button
            variant="accent"
            size="sm"
            onClick={handleSearchScenes}
            disabled={searching}
            className="px-4"
          >
            {searching ? "Searching Catalogue…" : "Search Satellite Scenes"}
          </Button>
        </div>
      </div>

      {errorMsg && (
        <div className="mono rounded border border-[color:var(--err)]/30 bg-[color:var(--err)]/8 px-3 py-2 text-[12px] text-[color:var(--err)] flex items-center justify-between gap-2">
          <span>{errorMsg}</span>
          {(errorMsg.toLowerCase().includes("sign in") ||
            errorMsg.toLowerCase().includes("session") ||
            errorMsg.toLowerCase().includes("expired") ||
            errorMsg.toLowerCase().includes("token")) && (
            <button
              type="button"
              onClick={() => window.dispatchEvent(new CustomEvent("open-auth-modal"))}
              className="shrink-0 px-2.5 py-1 rounded bg-[color:var(--err)] text-white text-[11px] font-semibold hover:opacity-90 transition-opacity cursor-pointer shadow-xs"
            >
              Sign In with Google →
            </button>
          )}
        </div>
      )}

      {/* 3. THE MAP (Large Visual Center, Full Width of Center Column) */}
      <div className="relative h-[460px] w-full overflow-hidden rounded-md border border-border shadow-xs">
        <div ref={mapContainerRef} className="absolute inset-0 h-full w-full" />

        {/* Compact Professional GIS Toolbar */}
        <div className="absolute left-3 top-3 z-[1000] flex flex-col gap-1 rounded-md border border-border bg-card/90 p-1 shadow-md backdrop-blur">
          <button
            onClick={() => mapRef.current?.zoomIn()}
            className="rounded p-1.5 hover:bg-muted text-foreground transition-colors"
            aria-label="Zoom in"
            title="Zoom in"
          >
            <IconZoomIn className="h-4 w-4" />
          </button>
          <button
            onClick={() => mapRef.current?.zoomOut()}
            className="rounded p-1.5 hover:bg-muted text-foreground transition-colors"
            aria-label="Zoom out"
            title="Zoom out"
          >
            <IconZoomOut className="h-4 w-4" />
          </button>
          <button
            onClick={() => {
              if (mapRef.current) {
                setLocationName("Hyderabad, Telangana");
                setCurrentCoords({ lat: 17.424, lon: 78.474 });
                mapRef.current.setView([17.424, 78.474], 12);
                createAoiFromBounds(mapRef.current.getBounds().pad(-0.25));
              }
            }}
            className="rounded p-1.5 hover:bg-muted text-foreground transition-colors"
            aria-label="Reset view"
            title="Reset to center"
          >
            <IconReset className="h-4 w-4" />
          </button>
          <hr className="my-0.5 border-border" />
          <button
            onClick={startDrawAoi}
            title="Drag on map to define custom Area of Interest"
            className={cn(
              "rounded px-2 py-1 text-[10.5px] font-semibold uppercase transition-colors text-center",
              drawingAoi ? "bg-accent text-accent-foreground" : "hover:bg-muted text-foreground"
            )}
          >
            {drawingAoi ? "Drawing…" : "Draw AOI"}
          </button>
          <button
            onClick={clearAoi}
            title="Reset AOI to current viewport"
            className="rounded px-2 py-0.5 text-[10.5px] font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            Reset
          </button>
        </div>

        {/* Compact Bottom Telemetry Pill */}
        {aoi && (
          <div className="mono absolute bottom-3 left-3 z-[1000] flex items-center gap-2 rounded border border-border bg-card/90 px-3 py-1 text-[11px] text-foreground shadow-sm backdrop-blur">
            <span>Area of Interest: <strong className="text-accent">{aoi.area_sq_km} km²</strong></span>
            <span className="text-border">|</span>
            <span>Centroid: {aoi.centroid[1]}° N, {aoi.centroid[0]}° E</span>
          </div>
        )}

        {/* Interactive Observation Year Switcher & Satellite Map Status */}
        <div className="absolute right-3 top-3 z-[1000] flex flex-col items-end gap-1.5">
          {mode === "temporal" ? (
            <div className="flex items-center gap-1.5 rounded-lg border border-border bg-card/95 p-1 shadow-md backdrop-blur">
              <span className="mono text-[11px] text-muted-foreground pl-2 font-medium">Map View:</span>
              <div className="flex items-center rounded-md border border-border/80 bg-muted/40 p-0.5">
                <button
                  type="button"
                  onClick={() => setTemporalTarget("before")}
                  className={cn(
                    "flex items-center gap-1.5 rounded px-2.5 py-1 text-[11.5px] font-semibold transition-all cursor-pointer",
                    temporalTarget === "before"
                      ? "bg-primary text-primary-foreground shadow-xs ring-1 ring-primary"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                  title={`View ${beforeYear} Baseline satellite imagery on map`}
                >
                  <span>◀ Before ({beforeYear})</span>
                </button>
                <button
                  type="button"
                  onClick={() => setTemporalTarget("after")}
                  className={cn(
                    "flex items-center gap-1.5 rounded px-2.5 py-1 text-[11.5px] font-semibold transition-all cursor-pointer",
                    temporalTarget === "after"
                      ? "bg-accent text-accent-foreground shadow-xs ring-1 ring-accent"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                  title={`View ${afterYear} Target satellite imagery on map`}
                >
                  <span>After ({afterYear}) ▶</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 rounded-md border border-border bg-card/95 px-3 py-1.5 shadow-md backdrop-blur">
              <span className="mono text-[11px] text-muted-foreground">Map Satellite Year:</span>
              <Badge tone="accent">{year}</Badge>
            </div>
          )}

          {/* Active Satellite Archive Status Tag */}
          <div className="mono rounded border border-border/80 bg-card/90 px-2.5 py-0.5 text-[10.5px] text-muted-foreground shadow-xs backdrop-blur flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--ok)] animate-pulse" />
            <span>Active Satellite: <strong className="text-foreground font-semibold">{activeViewingYear} Archive</strong></span>
            <span className="text-border">·</span>
            <span className="text-[10px]">Esri Wayback / Sentinel</span>
          </div>
        </div>
      </div>

      {/* 4. SCENE RESULTS (Spacious Strip / Grid Below the Map) */}
      <div className="rounded-md border border-border bg-card p-3">
        <div className="flex flex-wrap items-center justify-between border-b border-border pb-2 gap-2">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="text-[13px] font-semibold">Available Satellite Scenes</span>
            {mode === "temporal" ? (
              <div className="flex items-center rounded-md border border-border p-0.5 bg-muted/40">
                <button
                  type="button"
                  onClick={() => setTemporalTarget("before")}
                  className={cn(
                    "flex items-center gap-1.5 rounded px-2.5 py-1 text-[11.5px] font-medium transition-colors cursor-pointer",
                    temporalTarget === "before"
                      ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  <span>Baseline / Before ({beforeYear})</span>
                  <span className="mono text-[10px] opacity-80">({beforeScenes.length})</span>
                </button>
                <button
                  type="button"
                  onClick={() => setTemporalTarget("after")}
                  className={cn(
                    "flex items-center gap-1.5 rounded px-2.5 py-1 text-[11.5px] font-medium transition-colors cursor-pointer",
                    temporalTarget === "after"
                      ? "bg-accent text-accent-foreground font-semibold shadow-xs"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  <span>Target / After ({afterYear})</span>
                  <span className="mono text-[10px] opacity-80">({afterScenes.length})</span>
                </button>
              </div>
            ) : mode === "fusion" ? (
              <div className="flex items-center rounded-md border border-border p-0.5 bg-muted/40">
                <button
                  type="button"
                  onClick={() => setFusionTarget("optical")}
                  className={cn(
                    "flex items-center gap-1.5 rounded px-2.5 py-1 text-[11.5px] font-medium transition-colors cursor-pointer",
                    fusionTarget === "optical"
                      ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  <span>Sentinel-2 Optical</span>
                  <span className="mono text-[10px] opacity-80">({scenes.length})</span>
                </button>
                <button
                  type="button"
                  onClick={() => setFusionTarget("sar")}
                  className={cn(
                    "flex items-center gap-1.5 rounded px-2.5 py-1 text-[11.5px] font-medium transition-colors cursor-pointer",
                    fusionTarget === "sar"
                      ? "bg-accent text-accent-foreground font-semibold shadow-xs"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  <span>Sentinel-1 C-SAR</span>
                  <span className="mono text-[10px] opacity-80">({sarScenes.length})</span>
                </button>
              </div>
            ) : (
              <span className="mono text-[11px] text-muted-foreground">({scenes.length} found)</span>
            )}
          </div>

          <div className="flex items-center gap-2 mono text-[11px] text-muted-foreground">
            {mode === "temporal" ? (
              <>
                <span className={secondaryScene ? "text-primary font-medium" : "text-muted-foreground"}>
                  Before: {secondaryScene ? secondaryScene.acquisition_datetime.slice(0, 10) : "(not selected)"}
                </span>
                <span>·</span>
                <span className={selectedScene ? "text-accent font-medium" : "text-muted-foreground"}>
                  After: {selectedScene ? selectedScene.acquisition_datetime.slice(0, 10) : "(not selected)"}
                </span>
              </>
            ) : mode === "fusion" ? (
              <>
                <span className={selectedScene ? "text-primary font-medium" : "text-muted-foreground"}>
                  Optical: {selectedScene ? selectedScene.acquisition_datetime.slice(0, 10) : "(not selected)"}
                </span>
                <span>·</span>
                <span className={secondaryScene ? "text-accent font-medium" : "text-muted-foreground"}>
                  SAR: {secondaryScene ? secondaryScene.acquisition_datetime.slice(0, 10) : "(not selected)"}
                </span>
              </>
            ) : (
              <span>{year} Observations</span>
            )}
          </div>
        </div>

        {/* Scene Cards Grid */}
        {(() => {
          const displayedScenes = mode === "temporal"
            ? (temporalTarget === "before" ? beforeScenes : afterScenes)
            : mode === "fusion"
            ? (fusionTarget === "optical" ? scenes : sarScenes)
            : scenes;

          return (
            <div className="mt-2.5">
              {displayedScenes.length === 0 ? (
                <div className="py-8 text-center text-[13px] text-muted-foreground">
                  <p className="font-medium">
                    {mode === "temporal"
                      ? `No ${temporalTarget === "before" ? "Baseline (Before)" : "Target (After)"} scenes queried yet.`
                      : mode === "fusion"
                      ? `No ${fusionTarget === "optical" ? "Sentinel-2 Optical" : "Sentinel-1 SAR"} scenes queried yet.`
                      : "No satellite scenes queried yet."}
                  </p>
                  <p className="mt-1 text-[12px]">
                    Click &ldquo;Search Satellite Scenes&rdquo; to discover real Sentinel-2 and Sentinel-1 scenes for this AOI.
                  </p>
                </div>
              ) : (
                <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                  {displayedScenes.map((s) => {
                    const isSar = isSarScene(s);

                    let isSelected = false;
                    let isSecond = false;
                    let badgeLabel = "";
                    let btnLabel = "Select Scene";

                    if (mode === "temporal") {
                      if (temporalTarget === "before") {
                        isSelected = secondaryScene?.scene_id === s.scene_id;
                        badgeLabel = isSelected ? "Selected (Before Baseline)" : "";
                        btnLabel = isSelected ? "Selected as Before Baseline" : "Select as Before Scene";
                      } else {
                        isSelected = selectedScene?.scene_id === s.scene_id;
                        badgeLabel = isSelected ? "Selected (After Target)" : "";
                        btnLabel = isSelected ? "Selected as After Target" : "Select as After Scene";
                      }
                    } else if (mode === "fusion") {
                      if (fusionTarget === "optical") {
                        isSelected = selectedScene?.scene_id === s.scene_id;
                        badgeLabel = isSelected ? "Selected (Optical Primary)" : "";
                        btnLabel = isSelected ? "Active Optical Primary" : "Select as Optical Scene";
                      } else {
                        isSecond = secondaryScene?.scene_id === s.scene_id;
                        badgeLabel = isSecond ? "Selected (SAR Radar)" : "";
                        btnLabel = isSecond ? "Active SAR Radar" : "Select as SAR Scene";
                      }
                    } else {
                      isSelected = selectedScene?.scene_id === s.scene_id;
                      badgeLabel = isSelected ? "Selected" : "";
                      btnLabel = isSelected ? "Active Scene" : "Select Scene";
                    }

                    return (
                      <div
                        key={s.scene_id}
                        onClick={() => handleSelectScene(s)}
                        className={cn(
                          "cursor-pointer rounded-md border p-2.5 transition-all text-left",
                          isSelected
                            ? (mode === "temporal" && temporalTarget === "before"
                                ? "border-primary bg-primary/8 ring-1 ring-primary"
                                : "border-accent bg-accent/8 ring-1 ring-accent")
                            : isSecond
                            ? "border-primary bg-primary/8 ring-1 ring-primary"
                            : "border-border bg-card hover:border-muted-foreground/50 hover:bg-muted/30"
                        )}
                      >
                        {/* Thumbnail Quicklook */}
                        {s.preview_url ? (
                          <div className="relative mb-2 h-20 w-full overflow-hidden rounded bg-black/40 border border-border">
                            <img
                              src={s.preview_url}
                              alt="Scene quicklook"
                              className="h-full w-full object-cover"
                              loading="lazy"
                            />
                            <span className="mono absolute bottom-1 right-1 rounded bg-black/70 px-1 py-0.5 text-[9.5px] text-white">
                              10 m/px
                            </span>
                          </div>
                        ) : null}

                        {/* Header */}
                        <div className="flex items-center justify-between gap-1">
                          <div className="flex items-center gap-1.5">
                            {isSar ? <IconSar className="h-4 w-4 text-accent" /> : <IconOptical className="h-4 w-4 text-accent" />}
                            <span className="text-[12.5px] font-semibold text-foreground">
                              {isSar ? "Sentinel-1 SAR" : "Sentinel-2 L2A"}
                            </span>
                          </div>
                          {badgeLabel ? (
                            <span className={cn(
                              "inline-flex items-center gap-1 text-[11px] font-semibold",
                              mode === "temporal" && temporalTarget === "before" ? "text-primary" : "text-[color:var(--ok)]"
                            )}>
                              <IconCheck className="h-3.5 w-3.5" /> {badgeLabel}
                            </span>
                          ) : null}
                        </div>

                        {/* Metadata */}
                        <div className="mono mt-2 space-y-1 text-[11.5px] text-muted-foreground">
                          <div className="flex justify-between">
                            <span>Acquired:</span>
                            <span className="font-medium text-foreground">{s.acquisition_datetime.slice(0, 10)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Cloud cover:</span>
                            <span className="font-medium text-foreground">
                              {s.cloud_cover !== null ? `${s.cloud_cover}%` : "0% (All-weather)"}
                            </span>
                          </div>
                          <div className="flex justify-between truncate">
                            <span>Scene ID:</span>
                            <span className="font-medium text-foreground truncate ml-1">{s.scene_id.slice(0, 16)}…</span>
                          </div>
                        </div>

                        {/* Select Action Button */}
                        <div className="mt-2.5 border-t border-border/60 pt-2">
                          <button
                            type="button"
                            className={cn(
                              "w-full rounded py-1 text-[11.5px] font-semibold transition-colors",
                              isSelected
                                ? (mode === "temporal" && temporalTarget === "before"
                                    ? "bg-primary text-primary-foreground"
                                    : "bg-accent text-accent-foreground")
                                : isSecond
                                ? "bg-primary text-primary-foreground"
                                : "border border-border text-foreground hover:bg-muted"
                            )}
                          >
                            {btnLabel}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })()}
      </div>
    </div>
  );
}
