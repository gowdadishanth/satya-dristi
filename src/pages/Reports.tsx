import { useEffect, useState } from "react";
import { Panel, Button, Badge, Eyebrow, cn } from "../components/ui";
import { SatImage, OverlayChange, OverlayGrounding, REGIONS, OverlayImageLayer } from "../components/SatImage";
import { ConfBadge, TaskIcon } from "../components/bits";
import { IconDownload, IconClose, IconTrace, IconCheck, IconTriangle } from "../components/icons";
import { api, type ReportItem } from "../lib/api";

export function Reports() {
  const [reports, setReports] = useState<any[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ kind: "ok" | "err"; text: string } | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const notify = (kind: "ok" | "err", text: string) => {
    setToast({ kind, text });
    window.setTimeout(() => setToast(null), 3500);
  };

  const loadReports = () => {
    setLoading(true);
    setError(null);
    api.reports.list()
      .then((data) => {
        if (data && data.length > 0) {
          setReports(data.map((r) => ({
            id: r.report_id,
            analysis_id: r.analysis_id,
            query: r.query,
            task: r.task,
            input: r.input,
            date: r.date,
            time: r.time,
            confidence: r.confidence,
            status: r.status,
            answer: r.answer,
            pdf_filename: r.pdf_filename,
            json_filename: r.json_filename,
          })));
        } else {
          setReports([]);
        }
        setLoading(false);
      })
      .catch((err: any) => {
        setReports([]);
        const rawMsg = err?.message || "";
        if (rawMsg.includes("Authorization") || rawMsg.includes("UNAUTHORIZED")) {
          setError("Authentication required. Please sign in to view verified reports.");
        } else {
          setError(rawMsg || "Failed to load reports from server.");
        }
        setLoading(false);
      });
  };

  useEffect(() => {
    loadReports();
  }, []);

  const report = reports.find((a) => a.id === openId);

  const downloadPdf = async (rep: any) => {
    if (busyId) return;
    setBusyId(rep.id);
    notify("ok", "Generating verified ReportLab PDF with embedded satellite evidence…");
    try {
      await api.reports.downloadPdf(rep.id, rep.pdf_filename);
      notify("ok", `Downloaded ${rep.pdf_filename || `SatyaDristi_Report_${rep.id}.pdf`}`);
    } catch (err: any) {
      notify("err", err.message || "Report download failed");
    } finally {
      setBusyId(null);
    }
  };

  const downloadJson = async (rep: any) => {
    try {
      await api.reports.downloadJson(rep.id, rep.json_filename);
      notify("ok", `Downloaded ${rep.json_filename || `SatyaDristi_Report_${rep.id}.json`}`);
    } catch (err: any) {
      notify("err", err.message || "Download failed");
    }
  };

  return (
    <div className="space-y-4">
      {toast && (
        <div
          className={cn(
            "fixed bottom-5 right-5 z-50 flex items-center gap-2 rounded-md px-4 py-2.5 text-[12.5px] font-medium shadow-lg fade-up",
            toast.kind === "ok" ? "bg-[color:var(--primary)] text-white" : "bg-[color:var(--err)] text-white"
          )}
        >
          {toast.kind === "ok" ? <IconCheck className="h-4 w-4" /> : <IconTriangle className="h-4 w-4" />}
          <span>{toast.text}</span>
        </div>
      )}

      {error && !loading && (
        <Panel className="p-8 text-center text-[13px] text-[color:var(--err)] space-y-3">
          <div>{error}</div>
          {error.toLowerCase().includes("sign in") && (
            <div>
              <button
                type="button"
                onClick={() => window.dispatchEvent(new CustomEvent("open-auth-modal"))}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:opacity-90 transition-opacity cursor-pointer"
              >
                Sign In with Google →
              </button>
            </div>
          )}
        </Panel>
      )}

      {loading && (
        <Panel className="p-8 text-center text-[13px] text-muted-foreground">
          Loading verified reports...
        </Panel>
      )}

      {!loading && !error && reports.length === 0 && (
        <Panel className="p-10 text-center text-[13px] text-muted-foreground">
          No reports generated yet. Run an analysis in the workbench to generate verified reports.
        </Panel>
      )}

      {reports.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {reports.map((a) => (
            <Panel key={a.id} className="flex flex-col overflow-hidden p-0">
              <SatImage bbox={REGIONS.corridor} className="h-28 w-full border-b border-border">
                {a.task === "Bi-Temporal Change" && <OverlayChange />}
                {a.task === "Grounding" && <OverlayGrounding />}
              </SatImage>
              <div className="flex flex-1 flex-col p-4">
                <div className="flex items-center gap-2">
                  <TaskIcon task={a.task} className="h-4 w-4 text-muted-foreground" />
                  <span className="mono text-[10.5px] uppercase tracking-wide text-muted-foreground">{a.id}</span>
                  <span className="ml-auto"><ConfBadge level={a.confidence} /></span>
                </div>
                <p className="mt-2 line-clamp-2 text-[13.5px] font-medium leading-snug">{a.query}</p>
                <dl className="mono mt-3 grid grid-cols-2 gap-y-1 text-[10.5px] text-muted-foreground">
                  <dt>Task</dt><dd className="text-right text-foreground">{a.task}</dd>
                  <dt>Input</dt><dd className="text-right text-foreground">{a.input}</dd>
                  <dt>Created</dt><dd className="text-right text-foreground">{a.date}</dd>
                  <dt>Status</dt><dd className="text-right" style={{ color: "var(--ok)" }}>{a.status}</dd>
                </dl>
                <div className="mt-4 flex gap-2 border-t border-border pt-3">
                  <Button size="sm" variant="outline" className="flex-1" onClick={() => setOpenId(a.id)}>
                    View
                  </Button>
                  <Button
                    size="sm"
                    variant="accent"
                    icon={<IconDownload className="h-3.5 w-3.5" />}
                    disabled={busyId === a.id}
                    onClick={() => downloadPdf(a)}
                  >
                    {busyId === a.id ? "…" : "PDF"}
                  </Button>
                </div>
              </div>
            </Panel>
          ))}
        </div>
      )}

      {/* Report detail dialog */}
      {report && (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/45 p-4 backdrop-blur-sm"
          onClick={() => setOpenId(null)}
        >
          <Panel raised className="my-6 w-full max-w-3xl p-0 fade-up">
            <div onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center gap-2 border-b border-border px-5 py-3">
                <span className="mono text-[10.5px] uppercase tracking-wide text-muted-foreground">Report {report.id}</span>
                <Badge tone="accent">{report.task}</Badge>
                <button
                  className="focus-ring ml-auto rounded p-1 hover:bg-muted"
                  onClick={() => setOpenId(null)}
                  aria-label="Close"
                >
                  <IconClose />
                </button>
              </div>
              <div className="space-y-5 p-5">
                <section>
                  <Eyebrow>Executive Result</Eyebrow>
                  <p className="mt-1.5 text-[15px] font-medium leading-snug">{report.answer}</p>
                </section>
                <div className="grid gap-4 sm:grid-cols-[1.4fr_1fr]">
                  <SatImage bbox={REGIONS.corridor} className="aspect-[4/3] w-full rounded-md border border-border">
                    {report.task === "Bi-Temporal Change" && <OverlayChange />}
                    {report.task === "Grounding" && <OverlayGrounding />}
                  </SatImage>
                  <div className="space-y-3">
                    <section>
                      <Eyebrow>Observation Parameters</Eyebrow>
                      <dl className="mono mt-1.5 space-y-1 text-[11px]">
                        <div className="flex justify-between"><dt className="text-muted-foreground">Input</dt><dd className="text-foreground">{report.input}</dd></div>
                        <div className="flex justify-between"><dt className="text-muted-foreground">Sensor</dt><dd className="text-foreground">Sentinel-2 / Sentinel-1</dd></div>
                        <div className="flex justify-between"><dt className="text-muted-foreground">CRS</dt><dd className="text-foreground">EPSG:4326</dd></div>
                        <div className="flex justify-between"><dt className="text-muted-foreground">Format</dt><dd className="text-foreground">Cloud GeoTIFF</dd></div>
                      </dl>
                    </section>
                    <section className="border-t border-border pt-3">
                      <Eyebrow>Calibrated Confidence</Eyebrow>
                      <div className="mt-1.5">
                        <ConfBadge level={report.confidence} />
                        <p className="mono mt-1.5 text-[10px] text-muted-foreground">
                          Cross-checked against spectral thresholding & spatial registration.
                        </p>
                      </div>
                    </section>
                  </div>
                </div>
                <div className="flex items-center justify-end gap-2 border-t border-border pt-4">
                  <Button variant="outline" size="sm" onClick={() => downloadJson(report)}>
                    JSON Metadata
                  </Button>
                  <Button
                    variant="accent"
                    size="sm"
                    icon={<IconDownload className="h-4 w-4" />}
                    disabled={busyId === report.id}
                    onClick={() => downloadPdf(report)}
                  >
                    {busyId === report.id ? "Generating PDF…" : "Download Official PDF Report"}
                  </Button>
                </div>
              </div>
            </div>
          </Panel>
        </div>
      )}
    </div>
  );
}
