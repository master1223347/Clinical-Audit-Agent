import { describe, expect, test } from "vitest";
import { render, screen } from "@testing-library/react";

import TranscriptPickerPage from "@/components/TranscriptPickerPage";
import { listTranscripts } from "@/lib/fixtures";

describe("TranscriptPickerPage", () => {
  test("renders a heading appropriate for a clinical reviewer", () => {
    render(<TranscriptPickerPage />);
    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading.textContent).toMatch(/clinical proof mode/i);
  });

  test("renders one row per transcript with title text", () => {
    render(<TranscriptPickerPage />);
    for (const t of listTranscripts()) {
      expect(screen.getByText(t.title)).toBeInTheDocument();
    }
  });

  test("each row links to /review/{inputId}", () => {
    render(<TranscriptPickerPage />);
    for (const t of listTranscripts()) {
      const link = screen.getByRole("link", { name: new RegExp(t.title, "i") });
      expect(link.getAttribute("href")).toBe(`/review/${t.inputId}`);
    }
  });

  test("shows the claim count for each transcript", () => {
    render(<TranscriptPickerPage />);
    const transcripts = listTranscripts();
    expect(transcripts.length).toBeGreaterThan(0);
    expect(screen.getAllByText(/1\s+claim/i).length).toBeGreaterThanOrEqual(
      transcripts.length,
    );
  });

  test("does NOT contain audience-leak strings in the rendered DOM", () => {
    const { container } = render(<TranscriptPickerPage />);
    const text = container.textContent ?? "";
    expect(text.toLowerCase()).not.toMatch(/internal/);
    expect(text.toLowerCase()).not.toMatch(/debug/);
    expect(text.toLowerCase()).not.toMatch(/test mode/);
    expect(text.toLowerCase()).not.toMatch(/reviewer mode/);
  });
});
