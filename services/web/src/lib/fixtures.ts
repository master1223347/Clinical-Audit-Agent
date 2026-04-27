import type {
  AnalyzeResponse,
  ClinicalClaim,
  RedFlagOnlySpan,
} from "@shared/types";

import sampleClaims from "../../../../docs/eval/fixtures/sample-claims.json";

// Phase 2 renders against this fixture only; the live API wiring lands in
// Phase 3 once wt/01 publishes /analyze. The fixture file owns claim shapes;
// this module owns the synthetic transcript text that the claims index into,
// plus response-level fields (escalationMessage, redFlagOnlySpans) that the
// /analyze response wrapper would carry but are absent from the per-claim
// fixture (sample-claims.json schema is ClinicalClaim[], not AnalyzeResponse).

type FixtureClaim = ClinicalClaim & {
  expected_doctor_action?: string;
};

const FIXTURE_CLAIMS = sampleClaims as FixtureClaim[];

const FIXTURE_PROMPT_VERSION_HASH = "fixture-v1";
const FIXTURE_MODEL_ID = "fixture-mode";

interface TranscriptFixture {
  inputId: string;
  title: string;
  rawText: string;
}

// Synthetic narratives. Each transcript pads the per-claim evidence span with
// realistic Indian-GP-style context. The padding is sized so that the claim's
// (startChar, endChar) offsets in sample-claims.json index into the evidence
// substring exactly — the test suite asserts this byte-for-byte.
const TRANSCRIPTS: TranscriptFixture[] = [
  {
    inputId: "input-fixture-001",
    title: "Urgent: vomiting with blood and fainting",
    rawText:
      "Today blood in my vomit and I fainted briefly. I feel very dizzy and cannot keep water down.",
  },
  {
    inputId: "input-fixture-002",
    title: "Missed antibiotic dose",
    rawText:
      "Yesterday I skipped my antibiotic because I thought it caused vomiting.",
  },
  {
    inputId: "input-fixture-003",
    title: "Vague gastrointestinal complaint",
    rawText:
      "I felt weird today after lunch and have been queasy on and off.",
  },
  {
    inputId: "input-fixture-004",
    title: "Patient self-diagnosis",
    rawText:
      "I think I have food poisoning. I had street food yesterday and feel awful.",
  },
  {
    inputId: "input-fixture-005",
    title: "Low-confidence food trigger",
    rawText: "I felt a bit off after lunch.",
  },
];

// Response-level red-flag spans for the urgent transcript. These are rule
// matches that did NOT become a claim — the dual-layer renderer paints them
// red on top of the rawText so the doctor can see what the LLM missed.
const RED_FLAG_ONLY_SPANS: Record<string, RedFlagOnlySpan[]> = {
  "input-fixture-001": (() => {
    const rawText = TRANSCRIPTS[0]!.rawText;
    const phrase = "cannot keep water down";
    const startChar = rawText.indexOf(phrase);
    return [
      {
        startChar,
        endChar: startChar + phrase.length,
        ruleKey: "unable_to_keep_fluids_down",
      },
    ];
  })(),
};

// SPEC §13.4 verbatim — production code reads this from
// app/rules/risk_messages.py. In Phase 2 we mirror it locally so the dual-layer
// view can render against the fixture without a backend.
const URGENT_ESCALATION_MESSAGE =
  "This may be urgent. Please seek emergency medical help now if you are experiencing severe symptoms.";

const ESCALATION_MESSAGES: Record<string, string> = {
  "input-fixture-001": URGENT_ESCALATION_MESSAGE,
};

export const FIXTURE_INPUT_IDS = TRANSCRIPTS.map((t) => t.inputId);

export function listTranscripts(): TranscriptFixture[] {
  return TRANSCRIPTS.map((t) => ({ ...t }));
}

export function getTranscript(
  inputId: string,
): TranscriptFixture | null {
  return TRANSCRIPTS.find((t) => t.inputId === inputId) ?? null;
}

export function getAnalyzeResponseFor(
  inputId: string,
): AnalyzeResponse | null {
  const transcript = getTranscript(inputId);
  if (!transcript) return null;

  const claims = FIXTURE_CLAIMS.filter((c) => c.inputId === inputId).map(
    (c) => stripExpected(c),
  );
  if (claims.length === 0) return null;

  return {
    inputId,
    promptVersionHash: FIXTURE_PROMPT_VERSION_HASH,
    modelId: FIXTURE_MODEL_ID,
    claims,
    escalationMessage: ESCALATION_MESSAGES[inputId] ?? null,
    redFlagOnlySpans: RED_FLAG_ONLY_SPANS[inputId] ?? [],
    createdAt: new Date(0).toISOString(),
  };
}

function stripExpected(claim: FixtureClaim): ClinicalClaim {
  // The fixture carries an expected_doctor_action used by the eval harness;
  // the portal renders the schema-typed claim only.
  const { expected_doctor_action: _ignored, ...rest } = claim;
  return rest;
}
