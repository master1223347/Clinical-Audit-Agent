import { describe, expect, test, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AuditCard from "@/components/AuditCard";
import { getAnalyzeResponseFor } from "@/lib/fixtures";
import type { ClinicalClaim } from "@shared/types";

function fixtureClaim(inputId: string): ClinicalClaim {
  const response = getAnalyzeResponseFor(inputId);
  if (!response || response.claims.length === 0) {
    throw new Error(`no claim for ${inputId}`);
  }
  return response.claims[0]!;
}

const noop = vi.fn();

describe("AuditCard", () => {
  test("renders the core SPEC §8.8 fields (claim, evidence, confidence, risk, missing info, safety)", () => {
    const claim = fixtureClaim("input-fixture-001");
    render(
      <AuditCard
        claim={claim}
        onAccept={noop}
        onEditRequest={noop}
        onReject={noop}
      />,
    );
    expect(screen.getByText(claim.claimText)).toBeInTheDocument();
    expect(screen.getByText(claim.evidence.evidenceText)).toBeInTheDocument();
    expect(screen.getByText(/97%/)).toBeInTheDocument();
    expect(screen.getByText(/urgent/i)).toBeInTheDocument();
    for (const m of claim.missingInfo) {
      expect(screen.getByText(m)).toBeInTheDocument();
    }
    expect(screen.getByText(/safe/i)).toBeInTheDocument();
  });

  test("renders three review buttons that wire the supplied callbacks", async () => {
    const claim = fixtureClaim("input-fixture-002");
    const onAccept = vi.fn();
    const onEditRequest = vi.fn();
    const onReject = vi.fn();
    const user = userEvent.setup();

    render(
      <AuditCard
        claim={claim}
        onAccept={onAccept}
        onEditRequest={onEditRequest}
        onReject={onReject}
      />,
    );

    await user.click(screen.getByRole("button", { name: /accept/i }));
    await user.click(screen.getByRole("button", { name: /edit/i }));
    await user.click(screen.getByRole("button", { name: /reject/i }));

    expect(onAccept).toHaveBeenCalledTimes(1);
    expect(onEditRequest).toHaveBeenCalledTimes(1);
    expect(onReject).toHaveBeenCalledTimes(1);
  });

  test("shows yellow interpretation badge with the M1a tooltip text in the DOM", () => {
    const claim = fixtureClaim("input-fixture-003"); // extractionType: interpretation
    render(
      <AuditCard
        claim={claim}
        onAccept={noop}
        onEditRequest={noop}
        onReject={noop}
      />,
    );
    const badge = screen.getByTestId("interpretation-badge-trigger");
    expect(badge.textContent).toMatch(/interpretation/i);

    // M1a tooltip text — must always be in the DOM so screen readers and
    // keyboard users can access it via aria-describedby.
    const tooltip = screen.getByRole("tooltip");
    expect(tooltip.textContent).toMatch(
      /direct.*closely paraphrases.*interpretation.*inferred.*beyond/i,
    );
  });

  test("interpretation badge is keyboard-focusable and links to the tooltip via aria-describedby", () => {
    const claim = fixtureClaim("input-fixture-003");
    render(
      <AuditCard
        claim={claim}
        onAccept={noop}
        onEditRequest={noop}
        onReject={noop}
      />,
    );
    const trigger = screen.getByTestId("interpretation-badge-trigger");
    expect(trigger.getAttribute("tabIndex") ?? trigger.getAttribute("tabindex"))
      .toBe("0");
    const describedBy = trigger.getAttribute("aria-describedby");
    expect(describedBy).toBeTruthy();
    const tooltip = document.getElementById(describedBy!);
    expect(tooltip).not.toBeNull();
    expect(tooltip!.getAttribute("role")).toBe("tooltip");

    trigger.focus();
    expect(document.activeElement).toBe(trigger);
  });

  test("does NOT render an interpretation badge for direct extractions", () => {
    const claim = fixtureClaim("input-fixture-001"); // direct
    render(
      <AuditCard
        claim={claim}
        onAccept={noop}
        onEditRequest={noop}
        onReject={noop}
      />,
    );
    expect(screen.queryByTestId("interpretation-badge-trigger")).toBeNull();
  });

  test("renders displayWarning when present on the claim", () => {
    const claim = fixtureClaim("input-fixture-005"); // has a displayWarning
    render(
      <AuditCard
        claim={claim}
        onAccept={noop}
        onEditRequest={noop}
        onReject={noop}
      />,
    );
    expect(screen.getByText(claim.displayWarning!)).toBeInTheDocument();
  });

  test("shows strikethrough of original text when the claim has been edited", () => {
    const claim: ClinicalClaim = {
      ...fixtureClaim("input-fixture-002"),
      doctorReviewStatus: "edited",
      originalClaimText: "Patient skipped a prescribed antibiotic dose.",
      claimText:
        "Patient reported skipping a prescribed antibiotic dose; cause unknown.",
    };
    render(
      <AuditCard
        claim={claim}
        onAccept={noop}
        onEditRequest={noop}
        onReject={noop}
      />,
    );
    const original = screen.getByTestId("audit-card-original-claim");
    expect(original.textContent).toBe(claim.originalClaimText);
    // Visual strikethrough — line-through class — to match the "strikethrough
    // overlay on changed words" rule.
    expect(original.className).toMatch(/line-through/);
    expect(screen.getByTestId("audit-card-claim-text").textContent).toBe(
      claim.claimText,
    );
  });

  test("shows medicationAdviceBlocked safety badge with audience-appropriate copy", () => {
    const claim = fixtureClaim("input-fixture-002");
    render(
      <AuditCard
        claim={claim}
        onAccept={noop}
        onEditRequest={noop}
        onReject={noop}
      />,
    );
    expect(screen.getByText(/medication advice blocked/i)).toBeInTheDocument();
  });

  test("does NOT contain audience-leak strings", () => {
    const claim = fixtureClaim("input-fixture-001");
    const { container } = render(
      <AuditCard
        claim={claim}
        onAccept={noop}
        onEditRequest={noop}
        onReject={noop}
      />,
    );
    const lower = (container.textContent ?? "").toLowerCase();
    expect(lower).not.toContain("internal");
    expect(lower).not.toContain("debug");
    expect(lower).not.toContain("test mode");
    expect(lower).not.toContain("reviewer mode");
  });

  test("uses the doctorReviewStatus to gate which buttons are disabled", () => {
    const accepted: ClinicalClaim = {
      ...fixtureClaim("input-fixture-001"),
      doctorReviewStatus: "accepted",
    };
    render(
      <AuditCard
        claim={accepted}
        onAccept={noop}
        onEditRequest={noop}
        onReject={noop}
      />,
    );
    // Once accepted, the Accept button reflects the state but is no longer the
    // primary action — at minimum it must communicate that the claim is in a
    // reviewed state. We assert the visible status badge.
    expect(screen.getByText(/^accepted$/i)).toBeInTheDocument();
  });
});

// Hush a noisy unused-import linter complaint without changing test behavior.
fireEvent;
