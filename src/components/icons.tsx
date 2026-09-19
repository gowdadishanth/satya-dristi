import type { SVGProps } from "react";

type P = SVGProps<SVGSVGElement>;

function Base({ children, ...p }: P & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      width={18}
      height={18}
      aria-hidden="true"
      {...p}
    >
      {children}
    </svg>
  );
}

export const IconSatellite = (p: P) => (
  <Base {...p}>
    <path d="M5 13l6 6M8.5 6.5l3 3M11 4l9 9M4 11l9 9" />
    <path d="M6.5 9.5L14.5 17.5" />
    <path d="M15 3l6 6-2 2-6-6z" />
    <path d="M17 15a4 4 0 01-4 4M20 15a7 7 0 01-7 7" />
  </Base>
);
export const IconDashboard = (p: P) => (
  <Base {...p}>
    <rect x="3" y="3" width="7" height="9" rx="1" />
    <rect x="14" y="3" width="7" height="5" rx="1" />
    <rect x="14" y="12" width="7" height="9" rx="1" />
    <rect x="3" y="16" width="7" height="5" rx="1" />
  </Base>
);
export const IconAnalyze = (p: P) => (
  <Base {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="M11 8v6M8 11h6M20 20l-3.5-3.5" />
  </Base>
);
export const IconHistory = (p: P) => (
  <Base {...p}>
    <path d="M3 12a9 9 0 109-9 9 9 0 00-7.5 4" />
    <path d="M3 3v4h4" />
    <path d="M12 8v4l3 2" />
  </Base>
);
export const IconReports = (p: P) => (
  <Base {...p}>
    <path d="M6 3h8l4 4v14H6z" />
    <path d="M14 3v4h4" />
    <path d="M9 12h6M9 16h6" />
  </Base>
);
export const IconSettings = (p: P) => (
  <Base {...p}>
    <circle cx="12" cy="12" r="3" />
    <path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" />
  </Base>
);
export const IconUpload = (p: P) => (
  <Base {...p}>
    <path d="M12 15V4M8 8l4-4 4 4" />
    <path d="M4 15v3a2 2 0 002 2h12a2 2 0 002-2v-3" />
  </Base>
);
export const IconOptical = (p: P) => (
  <Base {...p}>
    <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" />
    <circle cx="12" cy="12" r="3" />
  </Base>
);
export const IconSar = (p: P) => (
  <Base {...p}>
    <path d="M4 20a8 8 0 018-8M4 20a12 12 0 0112-12M4 20a16 16 0 0116-16" />
    <circle cx="5" cy="19" r="1.4" />
  </Base>
);
export const IconChange = (p: P) => (
  <Base {...p}>
    <path d="M4 7h13M13 3l4 4-4 4" />
    <path d="M20 17H7M11 21l-4-4 4-4" />
  </Base>
);
export const IconGrounding = (p: P) => (
  <Base {...p}>
    <path d="M12 21s7-5.5 7-11a7 7 0 10-14 0c0 5.5 7 11 7 11z" />
    <circle cx="12" cy="10" r="2.5" />
  </Base>
);
export const IconLayers = (p: P) => (
  <Base {...p}>
    <path d="M12 3l9 5-9 5-9-5 9-5z" />
    <path d="M3 13l9 5 9-5M3 17l9 5 9-5" />
  </Base>
);
export const IconEvidence = (p: P) => (
  <Base {...p}>
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <path d="M3 15l5-5 4 4 3-3 6 6" />
    <circle cx="8.5" cy="8.5" r="1.5" />
  </Base>
);
export const IconTrace = (p: P) => (
  <Base {...p}>
    <circle cx="6" cy="6" r="2" />
    <circle cx="6" cy="18" r="2" />
    <circle cx="18" cy="12" r="2" />
    <path d="M6 8v8M8 6h6M8 18h6M12 6a6 6 0 004 6M12 18a6 6 0 004-6" />
  </Base>
);
export const IconDownload = (p: P) => (
  <Base {...p}>
    <path d="M12 3v12M8 11l4 4 4-4" />
    <path d="M4 21h16" />
  </Base>
);
export const IconStatus = (p: P) => (
  <Base {...p}>
    <path d="M3 12h4l2 6 4-14 2 8h6" />
  </Base>
);
export const IconClose = (p: P) => (
  <Base {...p}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Base>
);
export const IconCheck = (p: P) => (
  <Base {...p}>
    <path d="M4 12l5 5L20 6" />
  </Base>
);
export const IconChevron = (p: P) => (
  <Base {...p}>
    <path d="M9 6l6 6-6 6" />
  </Base>
);
export const IconArrow = (p: P) => (
  <Base {...p}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </Base>
);
export const IconSearch = (p: P) => (
  <Base {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="M20 20l-3.5-3.5" />
  </Base>
);
export const IconClock = (p: P) => (
  <Base {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 2" />
  </Base>
);
export const IconTriangle = (p: P) => (
  <Base {...p}>
    <path d="M12 4l9 16H3z" />
    <path d="M12 10v4M12 17.5v.01" />
  </Base>
);
export const IconMenu = (p: P) => (
  <Base {...p}>
    <path d="M4 7h16M4 12h16M4 17h16" />
  </Base>
);
export const IconZoomIn = (p: P) => (
  <Base {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="M11 8v6M8 11h6M20 20l-3.5-3.5" />
  </Base>
);
export const IconZoomOut = (p: P) => (
  <Base {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="M8 11h6M20 20l-3.5-3.5" />
  </Base>
);
export const IconReset = (p: P) => (
  <Base {...p}>
    <path d="M4 4v5h5" />
    <path d="M20 20v-5h-5" />
    <path d="M4 9a8 8 0 0114-3M20 15a8 8 0 01-14 3" />
  </Base>
);

export const IconGlobe = (p: P) => (
  <Base {...p}>
    <circle cx="12" cy="12" r="10" />
    <path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
  </Base>
);

export const IconFile = (p: P) => (
  <Base {...p}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
  </Base>
);


