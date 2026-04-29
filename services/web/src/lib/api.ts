import type { AnalyzeResponse, DoctorAction, DoctorEditOrigin } from "@shared/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface ReviewClaimPayload {
  claimId: string;
  action: DoctorAction;
  correctedClaim?: string;
  doctorEditOrigin?: DoctorEditOrigin;
  reason?: string;
}

/**
 * Fetches the cached analyze response for a transcript.
 * Returns null on 404 (stale cache) — caller should fall back to fixture.
 * Throws on other non-2xx responses.
 */
export async function fetchAnalyzeResponse(
  transcriptId: string,
): Promise<AnalyzeResponse | null> {
  const res = await fetch(
    `${API_BASE}/analyze/cached/${encodeURIComponent(transcriptId)}`,
    { cache: "no-store" },
  );
  if (res.status === 404) {
    console.warn(
      `[stale-cache] /analyze/cached/${transcriptId} returned 404 — falling back to fixture data.`,
    );
    return null;
  }
  if (!res.ok) {
    throw new Error(
      `fetchAnalyzeResponse: unexpected status ${res.status} for transcript ${transcriptId}`,
    );
  }
  const data: unknown = await res.json();
  if (
    !data ||
    typeof data !== "object" ||
    !Array.isArray((data as AnalyzeResponse).claims)
  ) {
    throw new Error(
      `fetchAnalyzeResponse: response missing required 'claims' array for transcript ${transcriptId}`,
    );
  }
  return data as AnalyzeResponse;
}

/**
 * Posts a doctor review action for a single claim.
 * Fire-and-forget safe: callers catch the returned Promise.
 * NEVER triggers a re-fetch of /analyze/cached — structural invariant (pilot.md §2, C4).
 */
export async function postReviewClaim(
  payload: ReviewClaimPayload,
): Promise<void> {
  const res = await fetch(`${API_BASE}/review-claim`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`postReviewClaim: unexpected status ${res.status}`);
  }
}
