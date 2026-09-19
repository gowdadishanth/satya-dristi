export type TaskType =
  | "Single-Image VQA"
  | "Bi-Temporal Change"
  | "Optical + SAR Fusion"
  | "Grounding";

export type InputType = "Single image" | "Optical + SAR" | "Before + After";
export type Conf = "High" | "Moderate" | "Low";

export type Analysis = {
  id: string;
  query: string;
  task: TaskType;
  input: InputType;
  date: string;
  time: string;
  confidence: Conf;
  status: "Complete" | "Draft";
  answer: string;
};

export const analyses: Analysis[] = [
  {
    id: "AN-2041",
    query: "What changed between these two dates along the river corridor?",
    task: "Bi-Temporal Change",
    input: "Before + After",
    date: "2026-09-14",
    time: "11:24",
    confidence: "Moderate",
    status: "Complete",
    answer: "Built-up area increased primarily along the eastern corridor; a new water surface appears south of the settlement.",
  },
  {
    id: "AN-2038",
    query: "Use the optical and SAR images together to identify built-up and water-covered regions.",
    task: "Optical + SAR Fusion",
    input: "Optical + SAR",
    date: "2026-09-13",
    time: "16:02",
    confidence: "High",
    status: "Complete",
    answer: "Dense built-up structures confirmed by SAR backscatter align with optical urban texture; two contiguous water bodies identified in the north-west.",
  },
  {
    id: "AN-2035",
    query: "Describe the major land-cover types visible in this image.",
    task: "Single-Image VQA",
    input: "Single image",
    date: "2026-09-12",
    time: "09:47",
    confidence: "High",
    status: "Complete",
    answer: "Predominantly irrigated cropland with a fragmented settlement in the south-east and a linear road network crossing east–west.",
  },
  {
    id: "AN-2030",
    query: "Highlight the water body referred to in the query.",
    task: "Grounding",
    input: "Single image",
    date: "2026-09-10",
    time: "14:18",
    confidence: "High",
    status: "Complete",
    answer: "Located a single contiguous reservoir in the central-west quadrant matching the described water body.",
  },
  {
    id: "AN-2026",
    query: "Has the built-up area increased since the previous acquisition?",
    task: "Bi-Temporal Change",
    input: "Before + After",
    date: "2026-09-08",
    time: "10:05",
    confidence: "Low",
    status: "Complete",
    answer: "Marginal built-up expansion detected, but optical and SAR evidence disagree — result flagged as uncertain.",
  },
];

export const capabilities = [
  {
    key: "vqa",
    title: "Single-Image VQA",
    body: "Ask questions about a satellite image.",
    icon: "optical",
  },
  {
    key: "ground",
    title: "Grounding & Classification",
    body: "Locate and identify regions described by text.",
    icon: "grounding",
  },
  {
    key: "change",
    title: "Bi-Temporal Change Analysis",
    body: "Compare imagery across two dates.",
    icon: "change",
  },
  {
    key: "fusion",
    title: "Optical + SAR Analysis",
    body: "Combine complementary information from both modalities.",
    icon: "sar",
  },
] as const;

export const pipelineSteps = [
  "Multimodal ingestion",
  "Input compatibility check",
  "Agentic query interpretation",
  "Specialist tool selection",
  "Model processing",
  "Evidence fusion",
  "Confidence estimation",
  "Auditable output",
];

export type Stage = {
  name: string;
  detail: string;
  duration: string;
};

export const executionStages: Stage[] = [
  { name: "Query interpretation", detail: "Parsed intent → bi-temporal change", duration: "0.4s" },
  { name: "Input validation", detail: "2 images, CRS matched, co-registered", duration: "0.7s" },
  { name: "Task selection", detail: "Bi-temporal change analysis", duration: "0.2s" },
  { name: "Specialist tool routing", detail: "Change Understanding · Grounding", duration: "0.3s" },
  { name: "Model inference", detail: "Change map + region description", duration: "3.1s" },
  { name: "Evidence fusion", detail: "Overlay reconciliation", duration: "0.9s" },
  { name: "Confidence estimation", detail: "Cross-model agreement", duration: "0.3s" },
  { name: "Result generation", detail: "Answer + evidence + trace", duration: "0.5s" },
];

export const domains = [
  { title: "Agriculture", body: "Crop extent, irrigation and seasonal change." },
  { title: "Disaster management", body: "Flood extent and post-event damage assessment." },
  { title: "Urban planning", body: "Built-up growth and land-use monitoring." },
  { title: "Forest monitoring", body: "Canopy loss and encroachment detection." },
  { title: "Water-resource assessment", body: "Surface-water extent and reservoir levels." },
  { title: "Infrastructure analysis", body: "Road, port and structure identification." },
  { title: "Environmental monitoring", body: "Coastline, wetland and terrain change." },
];
