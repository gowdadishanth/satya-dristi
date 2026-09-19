/**
 * Satya Dristi API Client Service Layer
 * Connects frontend directly to the FastAPI backend.
 */

const API_BASE = "/api/v1";

function getAuthToken(): string {
  if (typeof window !== "undefined") {
    return localStorage.getItem("sd_auth_token") || "dev-token-analyst_01";
  }
  return "dev-token-analyst_01";
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
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

  if (!res.ok) {
    let errorDetail = `API request failed (${res.status})`;
    try {
      const contentType = res.headers.get("content-type") || "";
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

  // If candidate is missing, is a bare UUID, or generic placeholder
  const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(candidate.replace(/\.(pdf|json)$/i, ""));
  
  if (!candidate || isUuid || candidate.toLowerCase() === "blob" || candidate.toLowerCase() === "download") {
    const cleanId = (reportId || "report").replace(/[^a-zA-Z0-9_-]/g, "_").replace(/^REP-/, "").replace(/^AN-/, "");
    candidate = `Satya_Dristi_Analysis_${cleanId}_${dateStr}${extension}`;
  }

  // Ensure Satya_Dristi_ prefix
  if (!candidate.startsWith("Satya_Dristi_")) {
    candidate = `Satya_Dristi_Analysis_${candidate}`;
  }

  // Ensure exact target extension
  if (!candidate.toLowerCase().endsWith(extension)) {
    candidate = `${candidate.replace(/\.[a-zA-Z0-9]+$/, "")}${extension}`;
  }

  return candidate;
}

export async function downloadReportPdf(
  reportId: string,
  customFilename?: string
): Promise<string> {
  const token = getAuthToken();
  const endpoint = `${API_BASE}/reports/${encodeURIComponent(reportId)}/download`;

  const res = await fetch(endpoint, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    let message = `PDF download failed (${res.status})`;
    try {
      const contentType = res.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const errorData = await res.json();
        message = errorData.detail?.message || errorData.detail || errorData.message || message;
      } else {
        const errorText = await res.text();
        if (errorText) message = errorText.slice(0, 300);
      }
    } catch {
      // Do not attempt to consume the response body again
    }
    throw new Error(message);
  }

  const contentType = (res.headers.get("content-type") || "").toLowerCase();
  if (!contentType.includes("application/pdf")) {
    throw new Error(`Expected application/pdf but received ${contentType || "unknown content type"}`);
  }

  const blob = await res.blob();
  if (!blob || blob.size === 0) {
    throw new Error("Downloaded PDF is empty (0 bytes).");
  }

  const disposition = res.headers.get("content-disposition");
  const dispositionFilename = parseContentDispositionFilename(disposition);
  const finalFilename = resolveSafeDownloadFilename("pdf", dispositionFilename, customFilename, reportId);

  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.style.display = "none";
  link.href = blobUrl;
  link.download = finalFilename;
  link.setAttribute("download", finalFilename);
  document.body.appendChild(link);
  
  try {
    link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
  } catch {
    link.click();
  }
  link.remove();

  setTimeout(() => {
    try {
      URL.revokeObjectURL(blobUrl);
    } catch {}
  }, 60000);

  return finalFilename;
}

export async function downloadReportJson(
  reportId: string,
  customFilename?: string
): Promise<string> {
  const token = getAuthToken();
  const endpoint = `${API_BASE}/reports/${encodeURIComponent(reportId)}/json`;

  const res = await fetch(endpoint, {
    method: "GET",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    let message = `JSON download failed (${res.status})`;
    try {
      const contentType = res.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const errorData = await res.json();
        message = errorData.detail?.message || errorData.detail || errorData.message || message;
      } else {
        const errorText = await res.text();
        if (errorText) message = errorText.slice(0, 300);
      }
    } catch {
      // Do not attempt to consume the response body again
    }
    throw new Error(message);
  }

  const contentType = (res.headers.get("content-type") || "").toLowerCase();
  if (!contentType.includes("application/json")) {
    throw new Error(`Expected application/json but received ${contentType || "unknown content type"}`);
  }

  const data = await res.json();
  const jsonStr = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonStr], { type: "application/json" });

  const disposition = res.headers.get("content-disposition");
  const dispositionFilename = parseContentDispositionFilename(disposition);
  const finalFilename = resolveSafeDownloadFilename("json", dispositionFilename, customFilename, reportId);

  const blobUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.style.display = "none";
  link.href = blobUrl;
  link.download = finalFilename;
  link.setAttribute("download", finalFilename);
  document.body.appendChild(link);

  try {
    link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
  } catch {
    link.click();
  }
  link.remove();

  setTimeout(() => {
    try {
      URL.revokeObjectURL(blobUrl);
    } catch {}
  }, 60000);

  return finalFilename;
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
    getMe: () => request<{ uid: string; email: string; name: string; picture: string }>("/auth/me"),
  },

  earth: {
    searchScenes: (params: {
      location?: string;
      bbox?: number[];
      year?: number;
      sensor?: "sentinel2" | "sentinel1";
      cloud_cover_max?: number;
      limit?: number;
    }) => request<Scene[]>("/earth/scenes/search", { method: "POST", body: JSON.stringify(params) }),

    getScene: (sceneId: string) => request<Scene>(`/earth/scenes/${sceneId}`),

    previewAOI: (aoi: { geometry?: any; bbox?: number[] }) =>
      request<AOIPreview>("/earth/aoi/preview", { method: "POST", body: JSON.stringify(aoi) }),

    checkCompatibility: (data: { scene_ids?: string[]; aoi?: any }) =>
      request<{ compatible: boolean; reason: string; overlap_pct: number }>("/earth/compatibility", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  analyses: {
    create: (data: {
      mode: string;
      query: string;
      scene_id?: string;
      aoi?: any;
      before_scene_id?: string;
      after_scene_id?: string;
      optical_scene_id?: string;
      sar_scene_id?: string;
    }) => request<AnalysisJobStatus>("/analyses", { method: "POST", body: JSON.stringify(data) }),

    createUpload: (formData: FormData) =>
      request<AnalysisJobStatus>("/analyses/upload", { method: "POST", body: formData }),

    getStatus: (analysisId: string) => request<AnalysisJobStatus>(`/analyses/${analysisId}/status`),

    getDetail: (analysisId: string) => request<AnalysisRecord>(`/analyses/${analysisId}`),

    delete: (analysisId: string) => request<{ deleted: boolean; analysis_id: string }>(`/analyses/${analysisId}`, { method: "DELETE" }),
  },

  history: {
    list: (params?: { task?: string; q?: string; limit?: number }) => {
      const qp = new URLSearchParams();
      if (params?.task) qp.append("task", params.task);
      if (params?.q) qp.append("q", params.q);
      if (params?.limit) qp.append("limit", String(params.limit));
      return request<AnalysisRecord[]>(`/history?${qp.toString()}`);
    },
  },

  reports: {
    list: () => request<ReportItem[]>("/reports"),

    getDetail: (reportId: string) => request<ReportItem>(`/reports/${reportId}`),

    downloadPdf: (reportId: string, filename?: string) => downloadReportPdf(reportId, filename),

    downloadJson: (reportId: string, filename?: string) => downloadReportJson(reportId, filename),
  },

  system: {
    getHealth: () => request<SystemHealth>("/system/health"),
  },
};
