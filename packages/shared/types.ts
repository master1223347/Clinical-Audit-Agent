// Clinical Proof Mode pilot — single source of truth for the claim object schema.
//
// SPEC.md §8.1, §8.2, §8.3 + Appendix A.1 (extractionType), §8.7, §8.9 + Appendix A.3
// (doctorEditOrigin), §11.1, §13.4, §17. pilot.md §1.1 (canonical TS schema), §2 (no
// claim without evidence; sticky escalations live on the response, not the claim).
//
// Pydantic models in app/models/ MUST keep field names byte-for-byte aligned with
// these declarations. scripts/check-schema-drift.py enforces parity in CI.
//
// Date fields are ISO-8601 strings on the wire. The Pydantic side stores them as
// datetime; serialization handles the conversion.

// ---------------------------------------------------------------------------
// Enum-shaped string unions
// ---------------------------------------------------------------------------

export type InputType = "text" | "voice" | "image" | "conversation";

export type EventType =
  | "vomiting"
  | "nausea"
  | "stomachPain"
  | "feverPresent"
  | "feverAbsent"
  | "dizziness"
  | "missedMedication"
  | "takenMedication"
  | "mealLogged"
  | "possibleFoodTrigger"
  | "painIncrease"
  | "painDecrease"
  | "symptomImproved"
  | "symptomWorsened"
  | "doctorInstruction"
  | "labReportUploaded"
  | "patientConcern"
  | "unknownHealthNote";

// "needs-review" added per Appendix A.1 — interpretation claims with overlap < 0.5
// are force-downgraded here regardless of the LLM's self-classification.
export type RiskLevel =
  | "low"
  | "medium"
  | "high"
  | "urgent"
  | "needs-review";

export type SafetyStatus =
  | "safe"
  | "medicationAdviceBlocked"
  | "diagnosisNotConfirmed"
  | "needsReview";

export type DoctorReviewStatus =
  | "pending"
  | "accepted"
  | "edited"
  | "rejected";

export type DoctorAction = "accepted" | "edited" | "rejected";

// Appendix A.1 — direct: claim text closely paraphrases the cited evidence span.
// interpretation: the AI inferred this beyond what's directly quoted.
export type ExtractionType = "direct" | "interpretation";

// Appendix A.3 — set when a doctor saves an edit; preserved alongside the original
// AI claim text. minor_wording counts toward "lightly edited" (eval bar #1).
export type DoctorEditOrigin =
  | "minor_wording"
  | "correction"
  | "external_knowledge_override";

// ---------------------------------------------------------------------------
// Object types
// ---------------------------------------------------------------------------

export interface Evidence {
  evidenceText: string;
  sourceType: InputType;
  sourceId: string;
  startChar: number | null;
  endChar: number | null;
  transcriptOffsetMs: number | null;
  imageRegion: { x: number; y: number; w: number; h: number } | null;
}

export interface ClinicalClaim {
  claimId: string;
  patientId: string;
  inputId: string;
  claimText: string;
  // null on first emission; set verbatim on first doctor edit and never overwritten
  // by subsequent edits (§8.9, Appendix A.3).
  originalClaimText: string | null;
  eventType: EventType;
  eventTime: string | null;
  confidence: number;
  evidence: Evidence;
  attributes: Record<string, unknown>;
  missingInfo: string[];
  riskLevel: RiskLevel;
  safetyStatus: SafetyStatus;
  doctorReviewStatus: DoctorReviewStatus;
  doctorEditOrigin: DoctorEditOrigin | null;
  extractionType: ExtractionType;
  displayWarning: string | null;
  createdAt: string;
}

// Appendix A.2 — red-flag-rule matches that did NOT become a claim. Rendered as
// the red layer in the dual-layer highlight. Char offsets index into rawText.
export interface RedFlagOnlySpan {
  startChar: number;
  endChar: number;
  ruleKey: string;
}

// Response wrapper. The escalationMessage and redFlagOnlySpans fields live on the
// response, not on individual claims, because the sticky-escalation rule (pilot.md
// §2 + C4) requires that doctor actions on individual claims cannot retract a
// response-level urgent escalation. The two-table SQLite schema enforces this
// structurally — analyze_responses is immutable after creation.
export interface AnalyzeResponse {
  inputId: string;
  promptVersionHash: string;
  modelId: string;
  claims: ClinicalClaim[];
  // §13.4 verbatim string from app/rules/risk_messages.py. null when not urgent.
  escalationMessage: string | null;
  redFlagOnlySpans: RedFlagOnlySpan[];
  createdAt: string;
}

export interface RiskAssessment {
  riskAssessmentId: string;
  patientId: string;
  claimIds: string[];
  riskLevel: RiskLevel;
  reasons: string[];
  urgentRedFlagsFound: boolean;
  missingCriticalInfo: string[];
  patientMessage: string;
}

export interface SafetyBlock {
  safetyBlockId: string;
  patientId: string;
  inputId: string;
  blockedText: string;
  blockedReason: string;
  // Verbatim from app/rules/blocked_advice.py:SAFE_REPLACEMENTS. Never authored
  // by the LLM — rule-first design (SPEC §8.7).
  safeReplacement: string;
  createdAt: string;
}

export interface FollowUpQuestion {
  question: string;
  purpose: string;
  // "high" | "medium" | "low" — kept as plain string to match Pydantic field
  // typing. The runtime values are validated by the follow-up generator.
  priority: string;
}
