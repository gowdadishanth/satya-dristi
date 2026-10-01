import { authService, isJwtExpired } from "./firebase";

/**
 * Satya Dristi API Client Service Layer
 * Connects frontend directly to the FastAPI backend.
 * All operations require authentic backend execution and valid Firebase authentication.
 */

const RAW_API_BASE = (import.meta.env.VITE_API_BASE_URL || "").trim().replace(/\/+$/, "");
export const hasCustomBackend = Boolean(RAW_API_BASE && RAW_API_BASE !== "");
const API_BASE = hasCustomBackend
  ? (RAW_API_BASE.endsWith("/api/v1") ? RAW_API_BASE : `${RAW_API_BASE}/api/v1`)
  : "/api/v1";

export async function getAuthToken(forceRefresh = false): Promise<string | null> {
  if (typeof window === "undefined") return null;
  let cached = localStorage.getItem("sd_auth_token");
  if (!forceRefresh && cached && !isJwtExpired(cached, 30)) {
    return cached;
  }
  try {
    const token = await authService.getIdToken(forceRefresh);
    if (token && !isJwtExpired(token, 0)) {
      return token;
    }
  } catch (err) {
    console.warn("Failed to refresh token via authService:", err);
  }
  if (cached && isJwtExpired(cached, 0)) {
    console.warn("Cached token expired and refresh failed. Clearing stale token.");
    localStorage.removeItem("sd_auth_token");
    cached = null;
  }
  return cached;
}

async function request<T>(endpoint: string, options: RequestInit = {}, retryCount = 0): Promise<T> {
  const token = await getAuthToken(false);
  const headers: Record<string, string> = {
    ...((options.headers as Record<string, string>) || {}),
  };

  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  // Automatically refresh and retry once if 401 Unauthorized occurs
  if (res.status === 401 && retryCount === 0) {
    console.info("Received 401 response; attempting token refresh and retry...");
    const freshToken = await getAuthToken(true);
    if (freshToken && freshToken !== token) {
      const retryHeaders = {
        ...headers,
        Authorization: `Bearer ${freshToken}`,
      };
      return request<T>(endpoint, { ...options, headers: retryHeaders }, retryCount + 1);
    }
  }

  // Intercept HTML responses from static hosting / Vercel SPA rewrites
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("text/html")) {
    throw new Error(`Endpoint ${endpoint} returned HTML (static routing fallback).`);
  }

  if (!res.ok) {
    let errorDetail = `API request failed (${res.status})`;
    try {
      if (contentType.includes("application/json")) {
        const errJson = await res.json();
        errorDetail = errJson.message || errJson.detail?.message || errJson.detail || JSON.stringify(errJson);
      } else {
        const errText = await res.text();
        if (errText) errorDetail = errText.slice(0, 300);
      }
    } catch {
      // Do not attempt to consume the response body again
    }

    // Convert raw Firebase expired error into friendly message if it escaped
    if (errorDetail.includes("Token expired") || errorDetail.includes("Invalid Firebase ID token")) {
      errorDetail = "Your session has expired. Please sign in again with Google to continue.";
    }

    throw new Error(errorDetail);
  }

  return res.json();
}

export type Scene = {
  scene_id: string;
  collection: string;
  provider: string;
  platform: string;
  instrument: string;
  sensor: string;
  processing_level: string;
  acquisition_datetime: string;
  cloud_cover: number | null;
  bbox: number[];
  geometry: any;
  preview_url: string | null;
  available_bands: string[];
  assets: Record<string, any>;
};

export type AOIPreview = {
  geometry: any;
  bbox: number[];
  centroid: [number, number];
  area_sq_km: number;
};

export type SystemHealth = {
  status: string;
  gpu_available: boolean;
  gpu_name: string;
  vram_total_mb: number;
  vram_allocated_mb: number;
  vram_free_mb: number;
  cuda_version: string;
  preferred_device: string;
  cpu_usage_pct: number;
  ram_total_mb: number;
  ram_available_mb: number;
  active_jobs_count: number;
  models_status: Record<string, string>;
  providers: Record<string, string>;
  database_status: string;
};

export type AnalysisJobStatus = {
  analysis_id: string;
  status: "queued" | "running" | "completed" | "failed";
  current_stage: string;
  progress_pct: number;
  error?: string | null;
};

export type AnalysisRecord = {
  analysis_id: string;
  uid: string;
  query: string;
  task: string;
  input: string;
  date: string;
  time: string;
  confidence: "High" | "Moderate" | "Low";
  confidence_score?: number;
  agreements: Array<{ label: string; state: "agree" | "partial" | "absent" }>;
  confidence_basis?: string;
  status: "Complete" | "Draft";
  answer: string;
  observed_evidence?: string;
  model_interpretation?: string;
  model_used?: string;
  device_used?: string;
  primary_image_path?: string;
  before_image_path?: string;
  sar_image_path?: string;
  evidence_path?: string;
  boxes?: Array<{
    x: number;
    y: number;
    w: number;
    h: number;
    confidence: number;
    class_name: string;
    geo_bbox?: number[];
    polygon?: Array<[number, number]>;
    centroid?: [number, number];
    pointer?: [number, number, number, number];
  }>;
  aoi?: AOIPreview;
  execution_trace?: Array<{
    name: string;
    detail: string;
    duration: string;
  }>;
  created_at: string;
  completed_at?: string;
};

export type ReportItem = {
  report_id: string;
  analysis_id: string;
  uid: string;
  query: string;
  task: string;
  input: string;
  date: string;
  time: string;
  confidence: "High" | "Moderate" | "Low";
  status: string;
  answer: string;
  generated_at: string;
  pdf_filename?: string;
  json_filename?: string;
};

function parseContentDispositionFilename(header: string | null): string | null {
  if (!header) return null;
  const match = header.match(/filename\*?=(?:UTF-8'')?"?([^";\r\n]+)"?/i);
  if (match && match[1]) {
    return decodeURIComponent(match[1].replace(/["']/g, "").trim());
  }
  return null;
}

export function resolveSafeDownloadFilename(
  format: "pdf" | "json",
  disposition?: string | null,
  custom?: string,
  reportId?: string
): string {
  const extension = `.${format}`;
  const dateStr = new Date().toISOString().slice(0, 10);

  let candidate = (custom || disposition || "").trim().replace(/^["']+|["']+$/g, "");

  const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
    candidate.replace(/\.(pdf|json)$/i, "")
  );

  if (!candidate || isUuid || candidate.toLowerCase() === "blob" || candidate.toLowerCase() === "download") {
    const cleanId = (reportId || "report")
      .replace(/[^a-zA-Z0-9_-]/g, "_")
      .replace(/^REP-/, "")
      .replace(/^AN-/, "");
    candidate = `Satya_Dristi_Analysis_${cleanId}_${dateStr}${extension}`;
  }

  if (!candidate.startsWith("Satya_Dristi_")) {
    candidate = `Satya_Dristi_Analysis_${candidate}`;
  }

  if (!candidate.toLowerCase().endsWith(extension)) {
    candidate = `${candidate.replace(/\.[a-zA-Z0-9]+$/, "")}${extension}`;
  }

  return candidate;
}

export function getAnalysisImageUrl(
  analysisId: string,
  type: "primary" | "before" | "after" | "sar" | "evidence"
): string {
  const token = typeof window !== "undefined" ? localStorage.getItem("sd_auth_token") : null;
  const validToken = token && !isJwtExpired(token, 0) ? token : null;
  const tokenParam = validToken ? `?token=${encodeURIComponent(validToken)}` : "";
  if (type === "evidence") {
    return `${API_BASE}/analyses/${encodeURIComponent(analysisId)}/evidence${tokenParam}`;
  }
  return `${API_BASE}/analyses/${encodeURIComponent(analysisId)}/image/${type}${tokenParam}`;
}

export async function downloadReportPdf(
  reportId: string,
  customFilename?: string
): Promise<string> {
  try {
    const token = await getAuthToken();
    const endpoint = `${API_BASE}/reports/${encodeURIComponent(reportId)}/download`;

    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(endpoint, {
      method: "GET",
      headers,
    });

    if (!res.ok) {
      throw new Error(`PDF download returned ${res.status}`);
    }

    const contentType = (res.headers.get("content-type") || "").toLowerCase();
    if (!contentType.includes("application/pdf")) {
      throw new Error(`Expected application/pdf but received ${contentType}`);
    }

    const blob = await res.blob();
    if (!blob || blob.size === 0) {
      throw new Error("Downloaded PDF is empty");
    }

    const disposition = res.headers.get("content-disposition");
    const dispositionFilename = parseContentDispositionFilename(disposition);
    const finalFilename = resolveSafeDownloadFilename("pdf", dispositionFilename, customFilename, reportId);

    const blobUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.style.position = "fixed";
    link.style.top = "-9999px";
    link.style.left = "-9999px";
    link.style.opacity = "0";
    link.href = blobUrl;
    link.download = finalFilename;
    link.setAttribute("download", finalFilename);
    link.rel = "noopener noreferrer";
    document.body.appendChild(link);

    try {
      link.click();
    } catch {
      link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
    }

    setTimeout(() => {
      try {
        link.remove();
        URL.revokeObjectURL(blobUrl);
      } catch {}
    }, 1000);

    return finalFilename;
  } catch (err) {
    console.error("Server PDF download failed:", err);
    throw err;
  }
}

export async function downloadReportJson(
  reportId: string,
  customFilename?: string
): Promise<string> {
  try {
    const token = await getAuthToken();
    const endpoint = `${API_BASE}/reports/${encodeURIComponent(reportId)}/json`;

    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(endpoint, {
      method: "GET",
      headers,
    });

    if (!res.ok) {
      throw new Error(`JSON download returned ${res.status}`);
    }

    const data = await res.json();
    const jsonStr = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonStr], { type: "application/json" });

    const disposition = res.headers.get("content-disposition");
    const dispositionFilename = parseContentDispositionFilename(disposition);
    const finalFilename = resolveSafeDownloadFilename("json", dispositionFilename, customFilename, reportId);

    const blobUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.style.position = "fixed";
    link.style.top = "-9999px";
    link.style.left = "-9999px";
    link.style.opacity = "0";
    link.href = blobUrl;
    link.download = finalFilename;
    link.setAttribute("download", finalFilename);
    link.rel = "noopener noreferrer";
    document.body.appendChild(link);

    try {
      link.click();
    } catch {
      link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
    }

    setTimeout(() => {
      try {
        link.remove();
        URL.revokeObjectURL(blobUrl);
      } catch {}
    }, 1000);

    return finalFilename;
  } catch (err) {
    console.error("Server JSON download failed:", err);
    throw err;
  }
}

export async function downloadReportFile(
  reportId: string,
  format: "pdf" | "json",
  customFilename?: string
): Promise<string> {
  if (format === "pdf") {
    return downloadReportPdf(reportId, customFilename);
  } else {
    return downloadReportJson(reportId, customFilename);
  }
}

export const api = {
  auth: {
    getMe: async () => {
      return await request<{ uid: string; email: string; name: string; picture: string }>("/auth/me");
    },
  },

  earth: {
    searchScenes: async (params: {
      location?: string;
      bbox?: number[];
      year?: number;
      sensor?: "sentinel2" | "sentinel1" | "optical" | "sar";
      cloud_cover_max?: number;
      limit?: number;
    }): Promise<Scene[]> => {
      return await request<Scene[]>("/earth/scenes/search", { method: "POST", body: JSON.stringify(params) });
    },

    getScene: async (sceneId: string): Promise<Scene> => {
      return await request<Scene>(`/earth/scenes/${sceneId}`);
    },

    previewAOI: async (aoi: { geometry?: any; bbox?: number[] }): Promise<AOIPreview> => {
      return await request<AOIPreview>("/earth/aoi/preview", { method: "POST", body: JSON.stringify(aoi) });
    },

    checkCompatibility: async (data: { scene_ids?: string[]; aoi?: any }) => {
      return await request<{ compatible: boolean; reason: string; overlap_pct: number }>("/earth/compatibility", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
  },

  analyses: {
    create: async (data: {
      mode: string;
      query: string;
      scene_id?: string;
      aoi?: any;
      before_scene_id?: string;
      after_scene_id?: string;
      optical_scene_id?: string;
      sar_scene_id?: string;
    }): Promise<AnalysisJobStatus> => {
      return await request<AnalysisJobStatus>("/analyses", { method: "POST", body: JSON.stringify(data) });
    },

    createUpload: async (formData: FormData): Promise<AnalysisJobStatus> => {
      return await request<AnalysisJobStatus>("/analyses/upload", { method: "POST", body: formData });
    },

    getStatus: async (analysisId: string): Promise<AnalysisJobStatus> => {
      return await request<AnalysisJobStatus>(`/analyses/${analysisId}/status`);
    },

    getDetail: async (analysisId: string): Promise<AnalysisRecord> => {
      return await request<AnalysisRecord>(`/analyses/${analysisId}`);
    },

    delete: async (analysisId: string): Promise<{ deleted: boolean; analysis_id: string }> => {
      return await request<{ deleted: boolean; analysis_id: string }>(`/analyses/${analysisId}`, {
        method: "DELETE",
      });
    },
  },

  history: {
    list: async (params?: { task?: string; q?: string; limit?: number }): Promise<AnalysisRecord[]> => {
      const qp = new URLSearchParams();
      if (params?.task) qp.append("task", params.task);
      if (params?.q) qp.append("q", params.q);
      if (params?.limit) qp.append("limit", String(params.limit));
      return await request<AnalysisRecord[]>(`/history?${qp.toString()}`);
    },
  },

  reports: {
    list: async (): Promise<ReportItem[]> => {
      return await request<ReportItem[]>("/reports");
    },

    getDetail: async (reportId: string): Promise<ReportItem> => {
      return await request<ReportItem>(`/reports/${reportId}`);
    },

    downloadPdf: async (reportId: string, filename?: string): Promise<string> => {
      return downloadReportPdf(reportId, filename);
    },

    downloadJson: async (reportId: string, filename?: string): Promise<string> => {
      return downloadReportJson(reportId, filename);
    },
  },

  system: {
    getHealth: async (): Promise<SystemHealth> => {
      return await request<SystemHealth>("/system/health");
    },
  },
};
