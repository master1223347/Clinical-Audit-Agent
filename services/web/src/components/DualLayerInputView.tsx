import type { RedFlagOnlySpan } from "@shared/types";

export interface EvidenceSpan {
  startChar: number;
  endChar: number;
  claimId: string;
}

export interface DualLayerInputViewProps {
  rawText: string;
  evidenceSpans: EvidenceSpan[];
  redFlagOnlySpans: RedFlagOnlySpan[];
}

type Layer = "none" | "evidence" | "redflag" | "both";

interface Run {
  text: string;
  layer: Layer;
}

const LAYER_CLASSES: Record<Layer, string> = {
  none: "",
  evidence:
    "bg-evidence-200 text-evidence-700 underline decoration-evidence-500 decoration-2 underline-offset-2",
  redflag:
    "bg-redflag-200 text-redflag-700 underline decoration-redflag-500 decoration-2 underline-offset-2",
  both: "bg-redflag-200 text-redflag-700 outline outline-2 outline-evidence-500 underline decoration-redflag-700 decoration-2 underline-offset-2",
};

const LAYER_LABEL: Record<Layer, string | undefined> = {
  none: undefined,
  evidence: "claim evidence",
  redflag: "red-flag rule match without a claim",
  both: "claim evidence and red-flag rule match",
};

export default function DualLayerInputView({
  rawText,
  evidenceSpans,
  redFlagOnlySpans,
}: DualLayerInputViewProps) {
  const layers = computeLayers(rawText.length, evidenceSpans, redFlagOnlySpans);
  const runs = collapseRuns(rawText, layers);

  return (
    <p className="whitespace-pre-wrap rounded-md border border-slate-200 bg-white p-4 text-base leading-7 text-slate-800">
      {runs.map((run, i) =>
        run.layer === "none" ? (
          <span key={i}>{run.text}</span>
        ) : (
          <mark
            key={i}
            data-layer={run.layer}
            aria-label={LAYER_LABEL[run.layer]}
            className={LAYER_CLASSES[run.layer]}
          >
            {run.text}
          </mark>
        ),
      )}
    </p>
  );
}

function computeLayers(
  length: number,
  evidenceSpans: EvidenceSpan[],
  redFlagOnlySpans: RedFlagOnlySpan[],
): Layer[] {
  const layers: Layer[] = new Array(length).fill("none");
  applySpans(layers, evidenceSpans, "evidence");
  applySpans(layers, redFlagOnlySpans, "redflag");
  return layers;
}

function applySpans(
  layers: Layer[],
  spans: { startChar: number; endChar: number }[],
  layer: "evidence" | "redflag",
): void {
  const length = layers.length;
  for (const span of spans) {
    const start = clamp(span.startChar, 0, length);
    const end = clamp(span.endChar, 0, length);
    if (end <= start) continue;
    for (let i = start; i < end; i++) {
      const existing = layers[i] ?? "none";
      if (existing === "none") {
        layers[i] = layer;
      } else if (existing !== layer) {
        layers[i] = "both";
      }
    }
  }
}

function clamp(value: number, min: number, max: number): number {
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

function collapseRuns(rawText: string, layers: Layer[]): Run[] {
  const runs: Run[] = [];
  let i = 0;
  while (i < rawText.length) {
    const layer = layers[i] ?? "none";
    let j = i + 1;
    while (j < rawText.length && (layers[j] ?? "none") === layer) j++;
    runs.push({ text: rawText.slice(i, j), layer });
    i = j;
  }
  return runs;
}
