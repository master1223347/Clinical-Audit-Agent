import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchAnalyzeResponse, postReviewClaim } from "@/lib/api";
import type { AnalyzeResponse } from "@shared/types";

const MOCK_ANALYZE_RESPONSE: AnalyzeResponse = {
  inputId: "transcript-001",
  promptVersionHash: "abc123",
  modelId: "claude-sonnet-4-6",
  claims: [],
  escalationMessage: null,
  redFlagOnlySpans: [],
  createdAt: "2026-04-29T00:00:00Z",
};

describe("fetchAnalyzeResponse", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed AnalyzeResponse on 200", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(MOCK_ANALYZE_RESPONSE),
    } as Response);

    const result = await fetchAnalyzeResponse("transcript-001");

    expect(result).toEqual(MOCK_ANALYZE_RESPONSE);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/analyze/cached/transcript-001"),
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("returns null and emits stale-cache warning on 404", async () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 404,
    } as Response);

    const result = await fetchAnalyzeResponse("transcript-001");

    expect(result).toBeNull();
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining("stale-cache"),
    );
    warnSpy.mockRestore();
  });

  it("throws with status in message on unexpected error status", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 500,
    } as Response);

    await expect(fetchAnalyzeResponse("transcript-001")).rejects.toThrow("500");
  });

  it("throws when 200 body is missing the required claims array", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ inputId: "t1" }), // no claims field
    } as Response);

    await expect(fetchAnalyzeResponse("transcript-001")).rejects.toThrow(
      "claims",
    );
  });

  it("encodes the transcript ID in the request URL", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(MOCK_ANALYZE_RESPONSE),
    } as Response);

    await fetchAnalyzeResponse("transcript/with spaces");

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("transcript%2Fwith%20spaces"),
      expect.anything(),
    );
  });
});

describe("postReviewClaim", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("POSTs JSON payload to /review-claim", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      status: 200,
    } as Response);

    await postReviewClaim({ claimId: "claim-1", action: "accepted" });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/review-claim"),
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claimId: "claim-1", action: "accepted" }),
      }),
    );
  });

  it("includes optional fields in payload when provided", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      status: 200,
    } as Response);

    await postReviewClaim({
      claimId: "claim-2",
      action: "edited",
      correctedClaim: "Patient reported nausea",
      doctorEditOrigin: "minor_wording",
      reason: "Simplified phrasing",
    });

    const body = JSON.parse(
      (vi.mocked(fetch).mock.calls[0]?.[1] as RequestInit)?.body as string,
    );
    expect(body.correctedClaim).toBe("Patient reported nausea");
    expect(body.doctorEditOrigin).toBe("minor_wording");
    expect(body.reason).toBe("Simplified phrasing");
  });

  it("throws with status in message on non-2xx response", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 503,
    } as Response);

    await expect(
      postReviewClaim({ claimId: "claim-1", action: "rejected" }),
    ).rejects.toThrow("503");
  });
});
