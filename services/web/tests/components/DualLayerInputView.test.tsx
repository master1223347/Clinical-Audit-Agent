import { describe, expect, test } from "vitest";
import { render } from "@testing-library/react";

import DualLayerInputView from "@/components/DualLayerInputView";
import { getAnalyzeResponseFor, listTranscripts } from "@/lib/fixtures";

describe("DualLayerInputView", () => {
  test("renders rawText verbatim, character-for-character", () => {
    const rawText = "Hello world. I felt sick yesterday.";
    const { container } = render(
      <DualLayerInputView
        rawText={rawText}
        evidenceSpans={[]}
        redFlagOnlySpans={[]}
      />,
    );
    expect(container.textContent).toBe(rawText);
  });

  test("highlights an evidence span in green and a red-flag-only span in red", () => {
    const rawText = "Today I felt dizzy and could not keep water down.";
    // "felt dizzy" → evidence span. "could not keep water down" → red-flag only.
    const evStart = rawText.indexOf("felt dizzy");
    const evEnd = evStart + "felt dizzy".length;
    const rfStart = rawText.indexOf("could not keep water down");
    const rfEnd = rfStart + "could not keep water down".length;

    const { container } = render(
      <DualLayerInputView
        rawText={rawText}
        evidenceSpans={[
          { startChar: evStart, endChar: evEnd, claimId: "claim-x" },
        ]}
        redFlagOnlySpans={[
          { startChar: rfStart, endChar: rfEnd, ruleKey: "no_fluids" },
        ]}
      />,
    );

    expect(container.textContent).toBe(rawText);

    const evMark = container.querySelector('mark[data-layer="evidence"]');
    expect(evMark).not.toBeNull();
    expect(evMark!.textContent).toBe("felt dizzy");

    const rfMark = container.querySelector('mark[data-layer="redflag"]');
    expect(rfMark).not.toBeNull();
    expect(rfMark!.textContent).toBe("could not keep water down");
  });

  test("handles overlapping evidence and red-flag spans without duplicating text", () => {
    const rawText = "I have severe pain and bleeding, very bad pain";
    // Evidence covers "severe pain" [7..18). Red-flag covers "pain and bleeding" [14..31).
    // Overlap is "pain" at [14..18). Renderer must produce rawText verbatim and
    // assign each character to exactly one rendered run.
    const evStart = rawText.indexOf("severe pain");
    const evEnd = evStart + "severe pain".length;
    const rfStart = rawText.indexOf("pain and bleeding");
    const rfEnd = rfStart + "pain and bleeding".length;

    const { container } = render(
      <DualLayerInputView
        rawText={rawText}
        evidenceSpans={[
          { startChar: evStart, endChar: evEnd, claimId: "c1" },
        ]}
        redFlagOnlySpans={[
          { startChar: rfStart, endChar: rfEnd, ruleKey: "blood_in_vomit" },
        ]}
      />,
    );

    expect(container.textContent).toBe(rawText);
    // The overlapping region should be rendered as a "both" layer so a single
    // visual element carries both highlights — no duplicated characters.
    const both = container.querySelector('mark[data-layer="both"]');
    expect(both).not.toBeNull();
    expect(both!.textContent).toBe("pain");
  });

  test("ignores spans whose offsets fall outside rawText bounds", () => {
    const rawText = "short";
    const { container } = render(
      <DualLayerInputView
        rawText={rawText}
        evidenceSpans={[
          { startChar: 100, endChar: 200, claimId: "out-of-bounds" },
        ]}
        redFlagOnlySpans={[]}
      />,
    );
    expect(container.textContent).toBe(rawText);
    expect(
      container.querySelector('mark[data-layer="evidence"]'),
    ).toBeNull();
  });

  test("snapshot: urgent fixture transcript renders both layers", () => {
    const transcript = listTranscripts().find(
      (t) => t.inputId === "input-fixture-001",
    )!;
    const response = getAnalyzeResponseFor("input-fixture-001")!;
    const evidenceSpans = response.claims.map((c) => ({
      startChar: c.evidence.startChar!,
      endChar: c.evidence.endChar!,
      claimId: c.claimId,
    }));
    const { container } = render(
      <DualLayerInputView
        rawText={transcript.rawText}
        evidenceSpans={evidenceSpans}
        redFlagOnlySpans={response.redFlagOnlySpans}
      />,
    );
    expect(container.firstChild).toMatchSnapshot();
  });
});
