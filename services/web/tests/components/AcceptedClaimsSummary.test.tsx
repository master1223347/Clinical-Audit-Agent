import { describe, expect, test } from "vitest";
import { render, screen } from "@testing-library/react";

import AcceptedClaimsSummary from "@/components/AcceptedClaimsSummary";
import { getAnalyzeResponseFor } from "@/lib/fixtures";
import type { ClinicalClaim } from "@shared/types";

function fixtureClaim(inputId: string): ClinicalClaim {
  return getAnalyzeResponseFor(inputId)!.claims[0]!;
}

function withStatus(
  claim: ClinicalClaim,
  status: ClinicalClaim["doctorReviewStatus"],
): ClinicalClaim {
  return { ...claim, doctorReviewStatus: status };
}

describe("AcceptedClaimsSummary", () => {
  test("renders only accepted and edited claims; hides pending and rejected", () => {
    const accepted = withStatus(fixtureClaim("input-fixture-001"), "accepted");
    const editedClaim = fixtureClaim("input-fixture-002");
    const edited: ClinicalClaim = {
      ...editedClaim,
      doctorReviewStatus: "edited",
      originalClaimText: editedClaim.claimText,
      claimText: "Patient reported skipping a prescribed antibiotic dose.",
    };
    const pending = withStatus(fixtureClaim("input-fixture-003"), "pending");
    const rejected = withStatus(fixtureClaim("input-fixture-004"), "rejected");

    render(
      <AcceptedClaimsSummary
        claims={[accepted, edited, pending, rejected]}
      />,
    );

    expect(screen.getByText(accepted.claimText)).toBeInTheDocument();
    expect(screen.getByText(edited.claimText)).toBeInTheDocument();
    expect(screen.queryByText(pending.claimText)).toBeNull();
    expect(screen.queryByText(rejected.claimText)).toBeNull();
  });

  test("renders an empty state when no claims have been accepted or edited", () => {
    const pending = withStatus(fixtureClaim("input-fixture-003"), "pending");
    render(<AcceptedClaimsSummary claims={[pending]} />);
    expect(
      screen.getByText(/no claims have been verified yet/i),
    ).toBeInTheDocument();
  });

  test("shows a verified-count summary heading", () => {
    const accepted = withStatus(fixtureClaim("input-fixture-001"), "accepted");
    const edited = withStatus(fixtureClaim("input-fixture-002"), "edited");
    render(<AcceptedClaimsSummary claims={[accepted, edited]} />);
    expect(screen.getByText(/verified claims \(2\)/i)).toBeInTheDocument();
  });

  test("does NOT render an entry for a rejected claim even if it has originalClaimText set", () => {
    const claim = fixtureClaim("input-fixture-001");
    const rejectedAfterEdit: ClinicalClaim = {
      ...claim,
      doctorReviewStatus: "rejected",
      originalClaimText: claim.claimText,
      claimText: "edited then rejected",
    };
    render(<AcceptedClaimsSummary claims={[rejectedAfterEdit]} />);
    expect(screen.queryByText("edited then rejected")).toBeNull();
  });

  test("does NOT contain audience-leak strings", () => {
    const accepted = withStatus(fixtureClaim("input-fixture-001"), "accepted");
    const { container } = render(
      <AcceptedClaimsSummary claims={[accepted]} />,
    );
    const lower = (container.textContent ?? "").toLowerCase();
    expect(lower).not.toContain("internal");
    expect(lower).not.toContain("debug");
    expect(lower).not.toContain("test mode");
    expect(lower).not.toContain("reviewer mode");
  });
});
