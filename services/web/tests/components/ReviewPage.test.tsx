import { describe, expect, test } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ReviewPage from "@/components/ReviewPage";
import { getAnalyzeResponseFor, listTranscripts } from "@/lib/fixtures";

function urgentTranscript() {
  const t = listTranscripts().find((x) => x.inputId === "input-fixture-001")!;
  const response = getAnalyzeResponseFor(t.inputId)!;
  return { transcript: t, response };
}

function missedMedTranscript() {
  const t = listTranscripts().find((x) => x.inputId === "input-fixture-002")!;
  const response = getAnalyzeResponseFor(t.inputId)!;
  return { transcript: t, response };
}

describe("ReviewPage", () => {
  test("renders the transcript title, the rawText, and one AuditCard per claim", () => {
    const { transcript, response } = urgentTranscript();
    const { container } = render(
      <ReviewPage
        title={transcript.title}
        rawText={transcript.rawText}
        response={response}
      />,
    );
    expect(screen.getByRole("heading", { name: transcript.title })).toBeInTheDocument();
    // DualLayerInputView splits text into runs — concatenated textContent
    // reproduces the rawText verbatim.
    expect(container.textContent ?? "").toContain(transcript.rawText);
    // One claim → one Accept/Edit/Reject button trio
    expect(screen.getAllByRole("button", { name: /^accept$/i })).toHaveLength(
      response.claims.length,
    );
  });

  test("renders the §13.4 escalation message when the response has one", () => {
    const { transcript, response } = urgentTranscript();
    render(
      <ReviewPage
        title={transcript.title}
        rawText={transcript.rawText}
        response={response}
      />,
    );
    const banner = screen.getByRole("alert");
    expect(banner.textContent).toMatch(/urgent|emergency|prompt medical/i);
  });

  test("does NOT render an escalation banner when the response has no escalation", () => {
    const { transcript, response } = missedMedTranscript();
    render(
      <ReviewPage
        title={transcript.title}
        rawText={transcript.rawText}
        response={response}
      />,
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  test("clicking Accept moves the claim into the verified-claims summary", async () => {
    const user = userEvent.setup();
    const { transcript, response } = missedMedTranscript();
    render(
      <ReviewPage
        title={transcript.title}
        rawText={transcript.rawText}
        response={response}
      />,
    );

    const summary = screen.getByLabelText(/verified claims/i);
    expect(within(summary).queryByText(response.claims[0]!.claimText)).toBeNull();

    await user.click(screen.getByRole("button", { name: /accept/i }));

    expect(
      within(summary).getByText(response.claims[0]!.claimText),
    ).toBeInTheDocument();
  });

  test("clicking Reject removes the claim from the verified summary even after Accept", async () => {
    const user = userEvent.setup();
    const { transcript, response } = missedMedTranscript();
    render(
      <ReviewPage
        title={transcript.title}
        rawText={transcript.rawText}
        response={response}
      />,
    );

    await user.click(screen.getByRole("button", { name: /accept/i }));
    const summary = screen.getByLabelText(/verified claims/i);
    expect(
      within(summary).getByText(response.claims[0]!.claimText),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /reject/i }));
    expect(
      within(summary).queryByText(response.claims[0]!.claimText),
    ).toBeNull();
  });

  test("Edit opens the modal; saving updates the claim with the corrected text and origin", async () => {
    const user = userEvent.setup();
    const { transcript, response } = missedMedTranscript();
    const claim = response.claims[0]!;

    render(
      <ReviewPage
        title={transcript.title}
        rawText={transcript.rawText}
        response={response}
      />,
    );

    expect(screen.queryByRole("dialog")).toBeNull();
    await user.click(screen.getByRole("button", { name: /edit/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    const textarea = screen.getByLabelText(
      /corrected claim/i,
    ) as HTMLTextAreaElement;
    await user.clear(textarea);
    await user.type(textarea, "Patient reported skipping a prescribed dose.");
    await user.click(screen.getByRole("radio", { name: /minor wording/i }));
    await user.click(screen.getByRole("button", { name: /save/i }));

    expect(screen.queryByRole("dialog")).toBeNull();
    // Card shows the corrected text in the AuditCard claim slot...
    expect(
      screen.getByTestId("audit-card-claim-text").textContent,
    ).toBe("Patient reported skipping a prescribed dose.");
    // ...with the original strikethrough overlay above it.
    const original = screen.getByTestId("audit-card-original-claim");
    expect(original.textContent).toBe(claim.claimText);
    // ...and the verified summary lists the corrected text.
    const summary = screen.getByLabelText(/verified claims/i);
    expect(
      within(summary).getByText(
        "Patient reported skipping a prescribed dose.",
      ),
    ).toBeInTheDocument();
  });

  test("Cancel closes the modal without changing the claim", async () => {
    const user = userEvent.setup();
    const { transcript, response } = missedMedTranscript();
    render(
      <ReviewPage
        title={transcript.title}
        rawText={transcript.rawText}
        response={response}
      />,
    );

    await user.click(screen.getByRole("button", { name: /edit/i }));
    await user.click(screen.getByRole("button", { name: /cancel/i }));

    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.queryByTestId("audit-card-original-claim")).toBeNull();
  });

  test("does NOT contain audience-leak strings", () => {
    const { transcript, response } = urgentTranscript();
    const { container } = render(
      <ReviewPage
        title={transcript.title}
        rawText={transcript.rawText}
        response={response}
      />,
    );
    const lower = (container.textContent ?? "").toLowerCase();
    expect(lower).not.toContain("internal");
    expect(lower).not.toContain("debug");
    expect(lower).not.toContain("test mode");
    expect(lower).not.toContain("reviewer mode");
  });
});
