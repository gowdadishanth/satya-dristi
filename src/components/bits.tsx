import { Badge } from "./ui";
import { IconOptical, IconSar, IconChange, IconGrounding } from "./icons";
import type { Conf, TaskType } from "../lib/data";

export function ConfBadge({ level }: { level: Conf }) {
  const tone = level === "High" ? "ok" : level === "Moderate" ? "warn" : "err";
  return <Badge tone={tone as any}>{level}</Badge>;
}

export function TaskIcon({ task, className }: { task: TaskType; className?: string }) {
  const Icon =
    task === "Optical + SAR Fusion" ? IconSar
      : task === "Bi-Temporal Change" ? IconChange
        : task === "Grounding" ? IconGrounding
          : IconOptical;
  return <Icon className={className} />;
}
