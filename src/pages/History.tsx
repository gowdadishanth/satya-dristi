import { useEffect, useState } from "react";
import type { Route } from "../App";
import { Panel, Eyebrow, cn } from "../components/ui";
import { analyses as initialAnalyses, type TaskType } from "../lib/data";
import { ConfBadge, TaskIcon } from "../components/bits";
import { IconSearch, IconArrow } from "../components/icons";
import { api, type AnalysisRecord } from "../lib/api";

const taskFilters: (TaskType | "All")[] = [
  "All",
  "Single-Image VQA",
  "Bi-Temporal Change",
  "Optical + SAR Fusion",
  "Grounding",
];

export function History({ navigate }: { navigate: (r: Route) => void }) {
  const [q, setQ] = useState("");
  const [task, setTask] = useState<TaskType | "All">("All");
  const [records, setRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);

    api.history.list({
      task: task === "All" ? undefined : task,
      q: q.trim() || undefined,
    })
      .then((data) => {
        if (mounted) {
          if (data && data.length > 0) {
            setRecords(data.map((d) => ({
              id: d.analysis_id,
              query: d.query,
              task: d.task,
              date: d.date,
              input: d.input,
              confidence: d.confidence,
              answer: d.answer,
            })));
          } else {
            // If no user analyses in DB yet, show fallback sample rows
            setRecords(
              initialAnalyses.filter(
                (a) => (task === "All" || a.task === task) && a.query.toLowerCase().includes(q.toLowerCase())
              )
            );
          }
          setLoading(false);
        }
      })
      .catch(() => {
        if (mounted) {
          setRecords(
            initialAnalyses.filter(
              (a) => (task === "All" || a.task === task) && a.query.toLowerCase().includes(q.toLowerCase())
            )
          );
          setLoading(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, [q, task]);

  return (
    <div className="space-y-4">
      <Panel className="p-3">
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <div className="relative flex-1">
            <IconSearch className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search historical queries…"
              className="w-full rounded-md border border-border bg-background/60 py-2 pl-9 pr-3 text-[13px] focus-ring"
            />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {taskFilters.map((t) => (
              <button
                key={t}
                onClick={() => setTask(t)}
                className={cn(
                  "focus-ring rounded-md border px-2.5 py-1.5 text-[11.5px] font-medium transition-colors",
                  task === t ? "border-accent bg-accent/10 text-accent font-semibold" : "border-border text-muted-foreground hover:bg-muted",
                )}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </Panel>

      <Panel className="p-0">
        <div className="hidden grid-cols-[1fr_160px_110px_110px_90px_40px] gap-3 border-b border-border px-4 py-2.5 md:grid">
          {["Query", "Task", "Date", "Input", "Confidence", ""].map((h) => (
            <Eyebrow key={h}>{h}</Eyebrow>
          ))}
        </div>
        {records.map((a) => (
          <button
            key={a.id}
            onClick={() => navigate("analyze")}
            className="grid w-full grid-cols-1 gap-1 border-b border-border px-4 py-3 text-left last:border-0 hover:bg-muted focus-ring md:grid-cols-[1fr_160px_110px_110px_90px_40px] md:items-center md:gap-3"
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <TaskIcon task={a.task} className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="truncate text-[13px] font-medium">{a.query}</span>
            </div>
            <span className="mono text-[11px] text-muted-foreground">{a.task}</span>
            <span className="mono text-[11px] text-muted-foreground">{a.date}</span>
            <span className="mono text-[11px] text-muted-foreground">{a.input}</span>
            <span><ConfBadge level={a.confidence} /></span>
            <IconArrow className="hidden h-4 w-4 text-muted-foreground md:block" />
          </button>
        ))}
        {records.length === 0 && !loading && (
          <div className="px-4 py-10 text-center text-[13px] text-muted-foreground">
            No analyses match your search criteria.
          </div>
        )}
        {loading && (
          <div className="px-4 py-8 text-center text-[13px] text-muted-foreground">
            Loading historical analyses...
          </div>
        )}
      </Panel>
    </div>
  );
}
