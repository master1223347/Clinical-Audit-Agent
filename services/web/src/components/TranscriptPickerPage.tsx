import Link from "next/link";

import {
  getAnalyzeResponseFor,
  listTranscripts,
} from "@/lib/fixtures";

export default function TranscriptPickerPage() {
  const transcripts = listTranscripts();

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-slate-900">
          Clinical Proof Mode
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Review AI-extracted clinical claims for each patient transcript.
          Every claim links to the evidence span the LLM grounded it in.
        </p>
      </header>

      <ul className="divide-y divide-slate-200 overflow-hidden rounded-lg border border-slate-200 bg-white">
        {transcripts.map((t) => {
          const response = getAnalyzeResponseFor(t.inputId);
          const claimCount = response?.claims.length ?? 0;
          return (
            <li key={t.inputId}>
              <Link
                href={`/review/${t.inputId}`}
                className="flex items-center justify-between gap-4 px-5 py-4 transition hover:bg-slate-50 focus:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
              >
                <span className="flex flex-col gap-1">
                  <span className="text-base font-medium text-slate-900">
                    {t.title}
                  </span>
                  <span className="text-xs uppercase tracking-wide text-slate-500">
                    {t.inputId}
                  </span>
                </span>
                <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600">
                  {claimCount} claim{claimCount === 1 ? "" : "s"}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </main>
  );
}
