import type { ClinicalClaim } from "@shared/types";

export interface AcceptedClaimsSummaryProps {
  claims: ClinicalClaim[];
}

export default function AcceptedClaimsSummary({
  claims,
}: AcceptedClaimsSummaryProps) {
  // SPEC §A.4 — pilot replaces the report generator with a filtered list of
  // accepted-and-edited claims. Pending and rejected claims are intentionally
  // excluded from the doctor-facing summary even when they still carry edits.
  const verified = claims.filter(
    (c) =>
      c.doctorReviewStatus === "accepted" || c.doctorReviewStatus === "edited",
  );

  return (
    <section
      aria-label="Verified claims"
      className="rounded-lg border border-slate-200 bg-white shadow-sm"
    >
      <header className="border-b border-slate-100 px-5 py-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-700">
          Verified claims ({verified.length})
        </h2>
        <p className="mt-1 text-xs text-slate-500">
          Final list for the doctor report. Includes accepted and edited
          claims; excludes pending and rejected.
        </p>
      </header>

      {verified.length === 0 ? (
        <p className="px-5 py-6 text-sm text-slate-500">
          No claims have been verified yet.
        </p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {verified.map((c) => (
            <li key={c.claimId} className="px-5 py-3">
              <p className="text-sm text-slate-900">{c.claimText}</p>
              <p className="mt-1 text-xs text-slate-500">
                {c.eventType}
                {c.doctorReviewStatus === "edited" ? " · edited" : null}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
