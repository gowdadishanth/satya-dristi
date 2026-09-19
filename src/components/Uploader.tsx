import { useRef, useState } from "react";
import { Eyebrow, cn } from "./ui";
import { IconUpload, IconCheck, IconTriangle, IconClose, IconReset } from "./icons";

/** Supported remote-sensing upload formats. */
const ACCEPT = ".tif,.tiff,.png,.jpg,.jpeg,image/tiff,image/png,image/jpeg";

export type UploadedFile = {
  file: File;
  name: string;
  size: number;
  format: string;
  previewUrl: string | null;
  status: "ready" | "invalid";
  error?: string;
};

function detectFormat(name: string): string | null {
  const ext = name.toLowerCase().split(".").pop() ?? "";
  if (ext === "tif" || ext === "tiff") return "GeoTIFF";
  if (ext === "png") return "PNG";
  if (ext === "jpg" || ext === "jpeg") return "JPEG";
  return null;
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

/** Validate a File and build an UploadedFile (creating a preview URL when renderable). */
export function makeUploadedFile(file: File): UploadedFile {
  const format = detectFormat(file.name);
  if (!format) {
    return {
      file,
      name: file.name,
      size: file.size,
      format: file.name.split(".").pop()?.toUpperCase() ?? "Unknown",
      previewUrl: null,
      status: "invalid",
      error: "Unsupported file — use GeoTIFF, TIFF, PNG or JPEG.",
    };
  }
  // Browsers cannot render TIFF/GeoTIFF inline; those show a glyph instead.
  const renderable = format === "PNG" || format === "JPEG";
  return {
    file,
    name: file.name,
    size: file.size,
    format,
    previewUrl: renderable ? URL.createObjectURL(file) : null,
    status: "ready",
  };
}

export function revokeUploaded(u: UploadedFile | null) {
  if (u?.previewUrl) URL.revokeObjectURL(u.previewUrl);
}

/** A single drag-and-drop / browse upload slot with preview and metadata. */
export function UploadSlot({
  label,
  value,
  onFile,
  onRemove,
}: {
  label: string;
  value: UploadedFile | null;
  onFile: (file: File) => void;
  onRemove: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);

  const pick = () => inputRef.current?.click();

  const handleFiles = (files: FileList | null) => {
    const f = files?.[0];
    if (f) onFile(f);
  };

  const hidden = (
    <input
      ref={inputRef}
      type="file"
      accept={ACCEPT}
      className="hidden"
      onChange={(e) => {
        handleFiles(e.target.files);
        e.target.value = "";
      }}
    />
  );

  if (!value) {
    return (
      <div>
        <Eyebrow className="mb-1.5">{label}</Eyebrow>
        <button
          type="button"
          onClick={pick}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            handleFiles(e.dataTransfer.files);
          }}
          className={cn(
            "flex w-full flex-col items-center gap-2 rounded-md border border-dashed px-4 py-6 text-center transition-colors focus-ring",
            drag ? "border-accent bg-accent/8" : "border-border bg-muted/40 hover:border-accent",
          )}
        >
          <IconUpload className="h-6 w-6 text-muted-foreground" />
          <span className="text-[13px] font-medium">Drag &amp; drop, or browse files</span>
          <span className="mono text-[10px] uppercase tracking-wide text-muted-foreground">
            GeoTIFF · TIFF · PNG · JPEG
          </span>
        </button>
        {hidden}
      </div>
    );
  }

  const invalid = value.status === "invalid";

  return (
    <div>
      <Eyebrow className="mb-1.5">{label}</Eyebrow>
      <div
        className={cn(
          "overflow-hidden rounded-md border bg-muted/40",
          invalid ? "border-[color:var(--err)]/45" : "border-border",
        )}
      >
        <div className="relative h-28 w-full bg-background/60">
          {value.previewUrl ? (
            <img src={value.previewUrl} alt={value.name} className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full w-full flex-col items-center justify-center gap-1 text-muted-foreground">
              <IconUpload className="h-5 w-5" />
              <span className="mono text-[9.5px] uppercase tracking-wide">
                {invalid ? "No preview" : `${value.format} · preview unavailable`}
              </span>
            </div>
          )}
        </div>
        <div className="p-2.5">
          <div className="flex items-center gap-2">
            <span className="mono truncate text-[11.5px] font-medium">{value.name}</span>
            <span
              className="ml-auto inline-flex items-center gap-1 text-[10.5px] font-medium"
              style={{ color: invalid ? "var(--err)" : "var(--ok)" }}
            >
              {invalid ? <IconTriangle className="h-3 w-3" /> : <IconCheck className="h-3 w-3" />}
              {invalid ? "Invalid" : "Ready"}
            </span>
          </div>
          {invalid ? (
            <p className="mt-1.5 text-[11px] leading-snug text-[color:var(--err)]">{value.error}</p>
          ) : (
            <div className="mono mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
              <Field k="Format" v={value.format} />
              <Field k="Size" v={formatBytes(value.size)} />
            </div>
          )}
          <div className="mt-2.5 flex gap-3">
            <button
              type="button"
              onClick={pick}
              className="mono inline-flex items-center gap-1 rounded text-[10.5px] text-muted-foreground hover:text-foreground focus-ring"
            >
              <IconReset className="h-3 w-3" /> Replace
            </button>
            <button
              type="button"
              onClick={onRemove}
              className="mono inline-flex items-center gap-1 rounded text-[10.5px] text-muted-foreground hover:text-foreground focus-ring"
            >
              <IconClose className="h-3 w-3" /> Remove
            </button>
          </div>
        </div>
      </div>
      {hidden}
    </div>
  );
}

function Field({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="uppercase tracking-wide">{k}</span>
      <span className="truncate text-right text-foreground">{v}</span>
    </div>
  );
}
