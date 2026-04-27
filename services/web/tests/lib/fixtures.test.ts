import { describe, expect, test } from "vitest";

import {
  FIXTURE_INPUT_IDS,
  getAnalyzeResponseFor,
  listTranscripts,
} from "@/lib/fixtures";

describe("fixture data layer", () => {
  test("listTranscripts returns one entry per fixture inputId, sorted stably", () => {
    const transcripts = listTranscripts();
    expect(transcripts).toHaveLength(FIXTURE_INPUT_IDS.length);
    const ids = transcripts.map((t) => t.inputId);
    expect(ids).toEqual([...FIXTURE_INPUT_IDS]);
    for (const t of transcripts) {
      expect(t.title.length).toBeGreaterThan(0);
      expect(t.rawText.length).toBeGreaterThan(0);
    }
  });

  test("getAnalyzeResponseFor returns a populated AnalyzeResponse for each fixture id", () => {
    for (const id of FIXTURE_INPUT_IDS) {
      const response = getAnalyzeResponseFor(id);
      expect(response).not.toBeNull();
      expect(response!.inputId).toBe(id);
      expect(response!.claims.length).toBeGreaterThan(0);
      expect(typeof response!.promptVersionHash).toBe("string");
      expect(typeof response!.modelId).toBe("string");
    }
  });

  test("getAnalyzeResponseFor returns null for unknown inputId", () => {
    expect(getAnalyzeResponseFor("unknown-input")).toBeNull();
  });

  test("each claim's evidence offsets index into the rawText exactly", () => {
    for (const id of FIXTURE_INPUT_IDS) {
      const response = getAnalyzeResponseFor(id)!;
      const { rawText } = listTranscripts().find((t) => t.inputId === id)!;
      for (const claim of response.claims) {
        const { startChar, endChar, evidenceText } = claim.evidence;
        expect(startChar).not.toBeNull();
        expect(endChar).not.toBeNull();
        expect(rawText.slice(startChar!, endChar!)).toBe(evidenceText);
      }
    }
  });

  test("urgent-risk fixture exposes an escalationMessage and at least one redFlagOnlySpan", () => {
    const response = getAnalyzeResponseFor("input-fixture-001")!;
    expect(response.escalationMessage).toBeTruthy();
    expect(response.escalationMessage).toMatch(/urgent|emergency|prompt medical/i);
    expect(response.redFlagOnlySpans.length).toBeGreaterThan(0);
    const { rawText } = listTranscripts().find(
      (t) => t.inputId === "input-fixture-001",
    )!;
    for (const span of response.redFlagOnlySpans) {
      expect(rawText.slice(span.startChar, span.endChar).length).toBeGreaterThan(
        0,
      );
      expect(span.ruleKey.length).toBeGreaterThan(0);
    }
  });

  test("non-urgent fixtures have no escalationMessage", () => {
    const non = FIXTURE_INPUT_IDS.filter((id) => id !== "input-fixture-001");
    for (const id of non) {
      expect(getAnalyzeResponseFor(id)!.escalationMessage).toBeNull();
    }
  });
});
