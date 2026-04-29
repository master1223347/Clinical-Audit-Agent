import { notFound } from "next/navigation";

import ReviewPage from "@/components/ReviewPage";
import { fetchAnalyzeResponse } from "@/lib/api";
import { getAnalyzeResponseFor, getTranscript } from "@/lib/fixtures";

interface PageProps {
  params: { id: string };
}

export default async function ReviewRoute({ params }: PageProps) {
  const transcript = getTranscript(params.id);
  if (!transcript) return notFound();

  // Server-only (no NEXT_PUBLIC_ prefix) so it resolves at request time, not
  // baked into the bundle at build time. Set USE_FIXTURE=1 for offline dev.
  const useFixture = process.env.USE_FIXTURE === "1";

  let response = null;

  if (useFixture) {
    response = getAnalyzeResponseFor(params.id);
  } else {
    try {
      response = await fetchAnalyzeResponse(params.id);
    } catch (err) {
      console.warn(
        `[api-error] fetchAnalyzeResponse failed for ${params.id} — falling back to fixture`,
        err,
      );
    }
    // null here means 404 (stale cache) or a network error fell through above
    if (!response) {
      response = getAnalyzeResponseFor(params.id);
    }
  }

  if (!response) return notFound();

  return (
    <ReviewPage
      title={transcript.title}
      rawText={transcript.rawText}
      response={response}
    />
  );
}
