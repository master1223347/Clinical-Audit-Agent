import { describe, expect, test, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ClaimEditModal from "@/components/ClaimEditModal";
import { getAnalyzeResponseFor } from "@/lib/fixtures";
import type { ClinicalClaim } from "@shared/types";

function fixtureClaim(): ClinicalClaim {
  return getAnalyzeResponseFor("input-fixture-002")!.claims[0]!;
}

describe("ClaimEditModal", () => {
  test("does not render when open is false", () => {
    render(
      <ClaimEditModal
        open={false}
        claim={fixtureClaim()}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test("renders the original claim text and the evidence as read-only context", () => {
    const claim = fixtureClaim();
    render(
      <ClaimEditModal
        open
        claim={claim}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    // The original claim text appears in the read-only display AND in the
    // pre-filled "corrected claim" textarea — both are intentional.
    expect(screen.getAllByText(claim.claimText).length).toBeGreaterThanOrEqual(
      1,
    );
    expect(screen.getByText(claim.evidence.evidenceText)).toBeInTheDocument();
  });

  test("renders the three Appendix A.3 self-classification radio options", () => {
    render(
      <ClaimEditModal
        open
        claim={fixtureClaim()}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("radio", { name: /minor wording/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("radio", { name: /correction/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("radio", { name: /external knowledge override/i }),
    ).toBeInTheDocument();
  });

  test("Save is disabled until a radio is selected", async () => {
    const user = userEvent.setup();
    render(
      <ClaimEditModal
        open
        claim={fixtureClaim()}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    const save = screen.getByRole("button", { name: /save/i });
    expect(save).toBeDisabled();
    await user.click(screen.getByRole("radio", { name: /minor wording/i }));
    expect(save).not.toBeDisabled();
  });

  test("Save calls onSave with correctedClaim, doctorEditOrigin, and reason", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn();
    const claim = fixtureClaim();
    render(
      <ClaimEditModal
        open
        claim={claim}
        onSave={onSave}
        onCancel={vi.fn()}
      />,
    );

    // Edit corrected text
    const textarea = screen.getByLabelText(/corrected claim/i) as HTMLTextAreaElement;
    await user.clear(textarea);
    await user.type(textarea, "Patient reported skipping a prescribed antibiotic dose.");

    // Pick a self-classification
    await user.click(
      screen.getByRole("radio", { name: /external knowledge override/i }),
    );

    // Optional reason
    const reason = screen.getByLabelText(/reason/i);
    await user.type(reason, "Removed causal implication.");

    await user.click(screen.getByRole("button", { name: /save/i }));

    expect(onSave).toHaveBeenCalledTimes(1);
    expect(onSave).toHaveBeenCalledWith({
      claimId: claim.claimId,
      correctedClaim:
        "Patient reported skipping a prescribed antibiotic dose.",
      doctorEditOrigin: "external_knowledge_override",
      reason: "Removed causal implication.",
    });
  });

  test("Cancel calls onCancel", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(
      <ClaimEditModal
        open
        claim={fixtureClaim()}
        onSave={vi.fn()}
        onCancel={onCancel}
      />,
    );
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  test("pre-fills the corrected-claim textarea with the current claim text", () => {
    const claim = fixtureClaim();
    render(
      <ClaimEditModal
        open
        claim={claim}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    const textarea = screen.getByLabelText(/corrected claim/i) as HTMLTextAreaElement;
    expect(textarea.value).toBe(claim.claimText);
  });

  test("dialog does NOT contain audience-leak strings", () => {
    const { container } = render(
      <ClaimEditModal
        open
        claim={fixtureClaim()}
        onSave={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    const lower = (container.textContent ?? "").toLowerCase();
    expect(lower).not.toContain("internal");
    expect(lower).not.toContain("debug");
    expect(lower).not.toContain("test mode");
    expect(lower).not.toContain("reviewer mode");
  });
});
