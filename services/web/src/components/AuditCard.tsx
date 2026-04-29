import { useId } from "react";

import type {
  ClinicalClaim,
  DoctorReviewStatus,
  RiskLevel,
  SafetyStatus,
} from "@shared/types";

export interface AuditCardProps {
  claim: ClinicalClaim;
  onAccept: () => void;
  onEditRequest: () => void;
  onReject: () => void;
}

// SPEC §A.1, M1a — exact copy required by the dispatch brief. Kept verbatim
// here so a content reviewer can grep for it.
const INTERPRETATION_TOOLTIP =
  "Direct: claim text closely paraphrases the cited evidence span. Interpretation: the AI inferred this beyond what's directly quoted — review carefully.";

const RISK_LABEL: Record<RiskLevel, string> = {
  low: "Low risk",
  medium: "Medium risk",
  high: "High risk",
  urgent: "Urgent",
  "needs-review": "Needs review",
};

const RISK_CLASSES: Record<RiskLevel, string> = {
  low: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  medium: "bg-amber-100 text-amber-800 ring-amber-200",
  high: "bg-orange-100 text-orange-800 ring-orange-200",
  urgent: "bg-red-100 text-red-800 ring-red-300",
  "needs-review": "bg-slate-100 text-slate-700 ring-slate-200",
};

const SAFETY_LABEL: Record<SafetyStatus, string> = {
  safe: "Safe",
  medicationAdviceBlocked: "Medication advice blocked",
  diagnosisNotConfirmed: "Diagnosis not confirmed",
  needsReview: "Needs review",
};

const REVIEW_STATUS_LABEL: Record<DoctorReviewStatus, string> = {
  pending: "Pending",
  accepted: "Accepted",
  edited: "Edited",
  rejected: "Rejected",
};

export default function AuditCard({
  claim,
  onAccept,
  onEditRequest,
  onReject,
}: AuditCardProps) {
  const tooltipId = useId();
  const confidencePct = Math.round(claim.confidence * 100);
  const isEdited =
    claim.doctorReviewStatus === "edited" && claim.originalClaimText;
  const isInterpretation = claim.extractionType === "interpretation";

  return (
    <article className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-5 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${RISK_CLASSES[claim.riskLevel]}`}
          >
            {RISK_LABEL[claim.riskLevel]}
          </span>
          <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700 ring-1 ring-inset ring-slate-200">
            {SAFETY_LABEL[claim.safetyStatus]}
          </span>
          {isInterpretation && (
            <InterpretationBadge tooltipId={tooltipId} />
          )}
          <span className="inline-flex items-center rounded-full bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-600 ring-1 ring-inset ring-slate-200">
            {REVIEW_STATUS_LABEL[claim.doctorReviewStatus]}
          </span>
        </div>
        <div className="text-xs text-slate-500">
          {claim.eventType}
        </div>
      </header>

      <div className="space-y-4 px-5 py-4">
        {isEdited && (
          <p
            data-testid="audit-card-original-claim"
            className="text-sm italic text-slate-500 line-through"
          >
            {claim.originalClaimText}
          </p>
        )}
        <p
          data-testid="audit-card-claim-text"
          className="text-base font-medium text-slate-900"
        >
          {claim.claimText}
        </p>

        {claim.displayWarning && (
          <p className="rounded-md bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-200">
            {claim.displayWarning}
          </p>
        )}

        <figure className="rounded-md border-l-4 border-evidence-500 bg-evidence-50 px-3 py-2">
          <figcaption className="text-xs uppercase tracking-wide text-evidence-700">
            Evidence
          </figcaption>
          <blockquote className="mt-1 text-sm text-slate-800">
            <span>“</span>
            <span>{claim.evidence.evidenceText}</span>
            <span>”</span>
          </blockquote>
        </figure>

        <div>
          <div className="flex items-center justify-between text-xs text-slate-600">
            <span>Confidence</span>
            <span>{confidencePct}%</span>
          </div>
          <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full bg-slate-700"
              style={{ width: `${confidencePct}%` }}
              aria-hidden
            />
          </div>
        </div>

        {claim.missingInfo.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Missing information
            </p>
            <ul className="mt-1 list-disc pl-5 text-sm text-slate-700">
              {claim.missingInfo.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <footer className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-100 px-5 py-3">
        <button
          type="button"
          onClick={onReject}
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
        >
          Reject
        </button>
        <button
          type="button"
          onClick={onEditRequest}
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
        >
          Edit
        </button>
        <button
          type="button"
          onClick={onAccept}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-700"
        >
          Accept
        </button>
      </footer>
    </article>
  );
}

function InterpretationBadge({ tooltipId }: { tooltipId: string }) {
  return (
    <span className="relative inline-flex">
      <span
        data-testid="interpretation-badge-trigger"
        tabIndex={0}
        role="button"
        aria-describedby={tooltipId}
        className="group inline-flex cursor-help items-center rounded-full bg-interpretation-200 px-2.5 py-1 text-xs font-semibold text-interpretation-700 ring-1 ring-inset ring-interpretation-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-interpretation-700"
      >
        Interpretation
      </span>
      <span
        id={tooltipId}
        role="tooltip"
        className="pointer-events-none absolute left-0 top-full z-10 mt-1 w-72 rounded-md bg-slate-900 px-3 py-2 text-xs text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
      >
        {INTERPRETATION_TOOLTIP}
      </span>
    </span>
  );
}
