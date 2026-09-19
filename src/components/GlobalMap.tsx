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

export function GlobalMap({ onSelectSceneAndAOI, mode }: GlobalMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const aoiLayerRef = useRef<L.Rectangle | null>(null);
  const footprintsLayerRef = useRef<L.LayerGroup | null>(null);
  const clickMarkerRef = useRef<L.CircleMarker | null>(null);

  // Search & Navigation State
  const [searchQuery, setSearchQuery] = useState("");
  const [locationName, setLocationName] = useState("Hyderabad, Telangana");
  const [currentCoords, setCurrentCoords] = useState<{ lat: number; lon: number }>({ lat: 17.424, lon: 78.474 });

  // Date & Sensor Filtering (2016-2026)
  const [year, setYear] = useState<number>(2024);
  const [sensor, setSensor] = useState<"optical" | "sar">("optical");
  const [cloudCoverMax, setCloudCoverMax] = useState<number>(30);

  // Dual-scene filter state for temporal mode
  const [temporalTarget, setTemporalTarget] = useState<"before" | "after">("after");
  const [beforeYear, setBeforeYear] = useState<number>(2022);
  const [afterYear, setAfterYear] = useState<number>(2024);

  // Scene & AOI State
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [selectedScene, setSelectedScene] = useState<Scene | null>(null);
  const [secondaryScene, setSecondaryScene] = useState<Scene | null>(null);
  const [aoi, setAoi] = useState<AOIPreview | null>(null);

  // Interactive UI State
  const [searching, setSearching] = useState(false);
  const [drawingAoi, setDrawingAoi] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [17.424, 78.474],
      zoom: 12,
      zoomControl: false,
    });

    // Satellite imagery base tiles (Esri World Imagery)
    L.tileLayer("https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
      attribution: "Tiles © Esri",
      maxZoom: 18,
    }).addTo(map);

    footprintsLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;

    // Click anywhere on map to select location
    map.on("click", async (e: L.LeafletMouseEvent) => {
      const lat = Number(e.latlng.lat.toFixed(4));
      const lon = Number(e.latlng.lng.toFixed(4));
      setCurrentCoords({ lat, lon });

      if (clickMarkerRef.current) {
        map.removeLayer(clickMarkerRef.current);
      }
      clickMarkerRef.current = L.circleMarker([lat, lon], {
        radius: 5,
        color: "#ab7c2c",
        fillColor: "#f6f3ed",
        fillOpacity: 0.9,
      }).addTo(map);

      // Center AOI box around clicked point
      const dLat = 0.03;
      const dLon = 0.03;
      const newBounds = L.latLngBounds([lat - dLat, lon - dLon], [lat + dLat, lon + dLon]);
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
    };
  }, []);

  // Update bounds and compute AOI geometry
  const createAoiFromBounds = async (bounds: L.LatLngBounds) => {
    if (!mapRef.current) return;

    if (aoiLayerRef.current) {
      mapRef.current.removeLayer(aoiLayerRef.current);
    }

    const rect = L.rectangle(bounds, {
      color: "#ab7c2c",
      weight: 2,
      dashArray: "4 4",
      fillColor: "#ab7c2c",
      fillOpacity: 0.15,
    }).addTo(mapRef.current);

    aoiLayerRef.current = rect;

    const bbox = [
      Number(bounds.getWest().toFixed(4)),
      Number(bounds.getSouth().toFixed(4)),
      Number(bounds.getEast().toFixed(4)),
      Number(bounds.getNorth().toFixed(4)),
    ];

    try {
      const preview = await api.earth.previewAOI({ bbox });
      setAoi(preview);
      setErrorMsg(null);
    } catch (err: any) {
      setAoi(null);
      setErrorMsg(err?.message || "Invalid AOI bounds or AOI validation failed.");
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
  const handleSearchScenes = async () => {
    if (!aoi) return;
    setSearching(true);
    setErrorMsg(null);

    const activeYear = mode === "temporal"
      ? (temporalTarget === "before" ? beforeYear : afterYear)
      : year;

    const targetSensor = mode === "fusion"
      ? sensor
      : (sensor === "sar" ? "sar" : "optical");

    try {
      const found = await api.earth.searchScenes({
        bbox: aoi.bbox,
        year: activeYear,
        sensor: targetSensor,
        cloud_cover_max: targetSensor === "optical" ? cloudCoverMax : undefined,
        limit: 8,
      });

      setScenes(found);

      if (found.length > 0) {
        if (mode === "temporal") {
          if (temporalTarget === "before") {
            setSecondaryScene(found[0]);
          } else {
            setSelectedScene(found[0]);
          }
        } else if (mode === "fusion") {
          if (targetSensor === "optical") {
            setSelectedScene(found[0]);
          } else {
            setSecondaryScene(found[0]);
          }
        } else {
          setSelectedScene(found[0]);
        }
      }

      // Render footprints on map
      if (footprintsLayerRef.current && mapRef.current) {
        footprintsLayerRef.current.clearLayers();
        found.forEach((s) => {
          if (s.bbox && s.bbox.length === 4) {
            const b = L.latLngBounds([s.bbox[1], s.bbox[0]], [s.bbox[3], s.bbox[2]]);
            L.rectangle(b, {
              color: s.sensor.includes("sar") || s.collection.includes("sar") ? "#4f6f8a" : "#ab7c2c",
              weight: 1,
              dashArray: "2 2",
              fillOpacity: 0.05,
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
      startLatLng = e.latlng;
      if (tempRect && mapRef.current) mapRef.current.removeLayer(tempRect);
      mapRef.current?.dragging.disable();
    };

    const onMouseMove = (e: L.LeafletMouseEvent) => {
      if (!startLatLng || !mapRef.current) return;
      const currentBounds = L.latLngBounds(startLatLng, e.latlng);
      if (!tempRect) {
        tempRect = L.rectangle(currentBounds, {
          color: "#ab7c2c",
          weight: 2,
          dashArray: "4 4",
          fillColor: "#ab7c2c",
          fillOpacity: 0.2,
        }).addTo(mapRef.current);
      } else {
        tempRect.setBounds(currentBounds);
      }
    };

    const onMouseUp = (e: L.LeafletMouseEvent) => {
      if (!startLatLng || !mapRef.current) return;
      const finalBounds = L.latLngBounds(startLatLng, e.latlng);
      if (tempRect) mapRef.current.removeLayer(tempRect);
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
      createAoiFromBounds(mapRef.current.getBounds().pad(-0.25));
    }
  };

  const handleSelectScene = (scene: Scene) => {
    if (mode === "temporal") {
      if (temporalTarget === "before") {
        setSecondaryScene(scene);
        if (selectedScene && aoi) {
          onSelectSceneAndAOI(selectedScene, aoi, scene);
        }
      } else {
        setSelectedScene(scene);
        if (aoi) {
          onSelectSceneAndAOI(scene, aoi, secondaryScene || undefined);
        }
      }
    } else if (mode === "fusion") {
      const isSar = scene.sensor.includes("sar") || scene.collection.includes("sar");
      if (isSar) {
        setSecondaryScene(scene);
        if (selectedScene && aoi) {
          onSelectSceneAndAOI(selectedScene, aoi, scene);
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
          <form onSubmit={handleSearchLocation} className="relative sm:col-span-6 lg:col-span-6">
            <IconSearch className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search a place or coordinates (e.g. Hyderabad, Suez, 17.42, 78.47)…"
              className="w-full rounded-md border border-border bg-card py-2 pl-9 pr-3 text-[13px] leading-tight focus-ring placeholder:text-muted-foreground"
            />
          </form>

          {/* Year Dropdown (2016 - 2026) */}
          <div className="sm:col-span-3 lg:col-span-3 flex items-center justify-between gap-1.5 rounded-md border border-border bg-card px-2.5 py-1.5 min-w-[105px]">
            <span className="mono text-[11px] uppercase tracking-wide text-muted-foreground whitespace-nowrap">
              {mode === "temporal" ? (temporalTarget === "before" ? "Pre:" : "Post:") : "Year:"}
            </span>
            {mode === "temporal" ? (
              <select
                value={temporalTarget === "before" ? beforeYear : afterYear}
                onChange={(e) => {
                  const val = Number(e.target.value);
                  if (temporalTarget === "before") setBeforeYear(val);
                  else setAfterYear(val);
                }}
                className="w-full bg-transparent text-[13px] font-medium outline-none text-foreground cursor-pointer"
              >
                {[2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016].map((y) => (
                  <option key={y} value={y} className="bg-card text-foreground">{y}</option>
                ))}
              </select>
            ) : (
              <select
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
                className="w-full bg-transparent text-[13px] font-medium outline-none text-foreground cursor-pointer"
              >
                {[2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016].map((y) => (
                  <option key={y} value={y} className="bg-card text-foreground">{y}</option>
                ))}
              </select>
            )}
          </div>

          {/* Sensor Selector */}
          <div className="sm:col-span-3 lg:col-span-3 flex rounded-md border border-border bg-card p-0.5">
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
        <div className="mono rounded border border-[color:var(--err)]/30 bg-[color:var(--err)]/8 px-3 py-1.5 text-[12px] text-[color:var(--err)]">
          {errorMsg}
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
      </div>

      {/* 4. SCENE RESULTS (Spacious Strip / Grid Below the Map) */}
      <div className="rounded-md border border-border bg-card p-3">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <div className="flex items-center gap-2">
            <span className="text-[13px] font-semibold">Available Satellite Scenes</span>
            <span className="mono text-[11px] text-muted-foreground">({scenes.length} found)</span>
          </div>
          <span className="mono text-[11px] text-muted-foreground">
            {mode === "temporal" ? `Viewing ${temporalTarget.toUpperCase()} catalogue` : `${year} Observations`}
          </span>
        </div>

        {/* Scene Cards Grid */}
        <div className="mt-2.5">
          {scenes.length === 0 ? (
            <div className="py-8 text-center text-[13px] text-muted-foreground">
              <p className="font-medium">No satellite scenes queried yet.</p>
              <p className="mt-1 text-[12px]">Click &ldquo;Search Satellite Scenes&rdquo; to discover real Sentinel-2 and Sentinel-1 scenes for this AOI.</p>
            </div>
          ) : (
            <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
              {scenes.map((s) => {
                const isSelected = selectedScene?.scene_id === s.scene_id;
                const isSecond = secondaryScene?.scene_id === s.scene_id;
                const isSar = s.sensor.includes("sar") || s.collection.includes("sar");

                return (
                  <div
                    key={s.scene_id}
                    onClick={() => handleSelectScene(s)}
                    className={cn(
                      "cursor-pointer rounded-md border p-2.5 transition-all text-left",
                      isSelected
                        ? "border-accent bg-accent/8 ring-1 ring-accent"
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
                      {isSelected ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[color:var(--ok)]">
                          <IconCheck className="h-3.5 w-3.5" /> Selected
                        </span>
                      ) : isSecond ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-primary">
                          <IconCheck className="h-3.5 w-3.5" /> {mode === "temporal" ? "Baseline" : "SAR"}
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
                            ? "bg-accent text-accent-foreground"
                            : isSecond
                            ? "bg-primary text-primary-foreground"
                            : "border border-border text-foreground hover:bg-muted"
                        )}
                      >
                        {isSelected ? "Active Scene" : isSecond ? "Secondary Scene" : "Select Scene"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
