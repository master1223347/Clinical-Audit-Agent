"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import type { AnalyzeResponse, ClinicalClaim } from "@shared/types";

import AcceptedClaimsSummary from "@/components/AcceptedClaimsSummary";
import AuditCard from "@/components/AuditCard";
import ClaimEditModal, {
  type ClaimEditPayload,
} from "@/components/ClaimEditModal";
import DualLayerInputView, {
  type EvidenceSpan,
} from "@/components/DualLayerInputView";

export interface ReviewPageProps {
  title: string;
  rawText: string;
  response: AnalyzeResponse;
}

export default function ReviewPage({
  title,
  rawText,
  response,
}: ReviewPageProps) {
  const [claims, setClaims] = useState<ClinicalClaim[]>(response.claims);
  const [editingClaimId, setEditingClaimId] = useState<string | null>(null);

  const evidenceSpans: EvidenceSpan[] = useMemo(
    () =>
      claims
        .filter(
          (c) =>
            c.evidence.startChar !== null && c.evidence.endChar !== null,
        )
        .map((c) => ({
          startChar: c.evidence.startChar!,
          endChar: c.evidence.endChar!,
          claimId: c.claimId,
        })),
    [claims],
  );

  const editingClaim =
    editingClaimId !== null
      ? claims.find((c) => c.claimId === editingClaimId) ?? null
      : null;

  function updateClaim(
    claimId: string,
    transform: (c: ClinicalClaim) => ClinicalClaim,
  ): void {
    setClaims((prev) =>
      prev.map((c) => (c.claimId === claimId ? transform(c) : c)),
    );
  }

  function handleAccept(claimId: string): void {
    updateClaim(claimId, (c) => ({
      ...c,
      doctorReviewStatus: "accepted",
    }));
  }

  function handleReject(claimId: string): void {
    updateClaim(claimId, (c) => ({
      ...c,
      doctorReviewStatus: "rejected",
    }));
  }

  function handleEditRequest(claimId: string): void {
    setEditingClaimId(claimId);
  }

  function handleSaveEdit(payload: ClaimEditPayload): void {
    updateClaim(payload.claimId, (c) => ({
      ...c,
      doctorReviewStatus: "edited",
      // Preserve original AI claim verbatim on first edit (SPEC §8.9, A.3).
      // Subsequent edits do not overwrite originalClaimText.
      originalClaimText: c.originalClaimText ?? c.claimText,
      claimText: payload.correctedClaim,
      doctorEditOrigin: payload.doctorEditOrigin,
    }));
    setEditingClaimId(null);
  }

  function handleCancelEdit(): void {
    setEditingClaimId(null);
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-8">
      <nav className="mb-4 text-sm">
        <Link
          href="/"
          className="text-slate-600 hover:text-slate-900 hover:underline"
        >
          ← All transcripts
        </Link>
      </nav>

      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
        <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">
          {response.inputId}
        </p>
      </header>

      {response.escalationMessage && (
        <div
          role="alert"
          className="mb-6 rounded-md border-l-4 border-red-600 bg-red-50 px-4 py-3 text-sm font-medium text-red-800"
        >
          {response.escalationMessage}
        </div>
      )}

      <section className="mb-8">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-700">
          Original input
        </h2>
        <DualLayerInputView
          rawText={rawText}
          evidenceSpans={evidenceSpans}
          redFlagOnlySpans={response.redFlagOnlySpans}
        />
        <DualLayerLegend />
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-700">
          Claims ({claims.length})
        </h2>
        <div className="space-y-4">
          {claims.map((c) => (
            <AuditCard
              key={c.claimId}
              claim={c}
              onAccept={() => handleAccept(c.claimId)}
              onEditRequest={() => handleEditRequest(c.claimId)}
              onReject={() => handleReject(c.claimId)}
            />
          ))}
        </div>
      </section>

      <section>
        <AcceptedClaimsSummary claims={claims} />
      </section>

      {editingClaim && (
        <ClaimEditModal
          open
          claim={editingClaim}
          onSave={handleSaveEdit}
          onCancel={handleCancelEdit}
        />
      )}
    </main>
  );
}

function DualLayerLegend() {
  return (
    <p className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-500">
      <span className="inline-flex items-center gap-1">
        <span className="inline-block h-2 w-3 rounded-sm bg-evidence-200 ring-1 ring-evidence-500" />
        Claim evidence
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="inline-block h-2 w-3 rounded-sm bg-redflag-200 ring-1 ring-redflag-500" />
        Red-flag rule match without a claim
      </span>
    </p>
  );
}
