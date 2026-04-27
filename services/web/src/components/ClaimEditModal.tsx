"use client";

import { useEffect, useId, useState } from "react";

import type { ClinicalClaim, DoctorEditOrigin } from "@shared/types";

export interface ClaimEditPayload {
  claimId: string;
  correctedClaim: string;
  doctorEditOrigin: DoctorEditOrigin;
  reason: string;
}

export interface ClaimEditModalProps {
  open: boolean;
  claim: ClinicalClaim;
  onSave: (payload: ClaimEditPayload) => void;
  onCancel: () => void;
}

interface RadioOption {
  value: DoctorEditOrigin;
  label: string;
  description: string;
}

const ORIGIN_OPTIONS: RadioOption[] = [
  {
    value: "minor_wording",
    label: "Minor wording",
    description:
      "Phrasing change only — same meaning. Counts as a lightly edited acceptance.",
  },
  {
    value: "correction",
    label: "Correction",
    description:
      "Doctor saw an extraction error and corrected it. Tracked as an extraction-quality signal.",
  },
  {
    value: "external_knowledge_override",
    label: "External knowledge override",
    description:
      "Doctor is overriding from outside the transcript (e.g., last-visit chart). Original evidence span is preserved.",
  },
];

export default function ClaimEditModal({
  open,
  claim,
  onSave,
  onCancel,
}: ClaimEditModalProps) {
  const titleId = useId();
  const [correctedClaim, setCorrectedClaim] = useState(claim.claimText);
  const [origin, setOrigin] = useState<DoctorEditOrigin | null>(null);
  const [reason, setReason] = useState("");

  useEffect(() => {
    if (open) {
      setCorrectedClaim(claim.claimText);
      setOrigin(null);
      setReason("");
    }
  }, [open, claim.claimText, claim.claimId]);

  if (!open) return null;

  const canSave = origin !== null;

  function handleSave() {
    if (!canSave || origin === null) return;
    onSave({
      claimId: claim.claimId,
      correctedClaim,
      doctorEditOrigin: origin,
      reason,
    });
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4"
    >
      <div className="w-full max-w-2xl rounded-lg bg-white shadow-xl">
        <header className="border-b border-slate-200 px-6 py-4">
          <h2 id={titleId} className="text-lg font-semibold text-slate-900">
            Edit claim
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            The original AI claim and evidence span are preserved. Your edit is
            saved alongside them.
          </p>
        </header>

        <div className="space-y-4 px-6 py-4">
          <section>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Original claim
            </p>
            <p className="mt-1 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-800">
              {claim.claimText}
            </p>
          </section>

          <section>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Evidence
            </p>
            <p className="mt-1 rounded-md border-l-4 border-evidence-500 bg-evidence-50 px-3 py-2 text-sm italic text-slate-800">
              {claim.evidence.evidenceText}
            </p>
          </section>

          <section>
            <label
              htmlFor="corrected-claim"
              className="block text-xs font-semibold uppercase tracking-wide text-slate-500"
            >
              Corrected claim
            </label>
            <textarea
              id="corrected-claim"
              value={correctedClaim}
              onChange={(e) => setCorrectedClaim(e.target.value)}
              rows={3}
              className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
            />
          </section>

          <fieldset>
            <legend className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Edit type
            </legend>
            <div
              role="radiogroup"
              aria-label="Edit type"
              className="mt-2 space-y-2"
            >
              {ORIGIN_OPTIONS.map((opt) => (
                <label
                  key={opt.value}
                  className="flex cursor-pointer items-start gap-3 rounded-md border border-slate-200 px-3 py-2 hover:bg-slate-50"
                >
                  <input
                    type="radio"
                    name="doctor-edit-origin"
                    value={opt.value}
                    checked={origin === opt.value}
                    onChange={() => setOrigin(opt.value)}
                    className="mt-1"
                  />
                  <span className="flex flex-col">
                    <span className="text-sm font-medium text-slate-900">
                      {opt.label}
                    </span>
                    <span className="text-xs text-slate-600">
                      {opt.description}
                    </span>
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <section>
            <label
              htmlFor="edit-reason"
              className="block text-xs font-semibold uppercase tracking-wide text-slate-500"
            >
              Reason (optional)
            </label>
            <textarea
              id="edit-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={2}
              className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
            />
          </section>
        </div>

        <footer className="flex items-center justify-end gap-2 border-t border-slate-200 px-6 py-4">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={!canSave}
            className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-700 disabled:cursor-not-allowed disabled:bg-slate-400"
          >
            Save
          </button>
        </footer>
      </div>
    </div>
  );
}
