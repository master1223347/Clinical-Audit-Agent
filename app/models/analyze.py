from datetime import datetime

from pydantic import BaseModel, Field

from app.models.claim import ClinicalClaim


class RedFlagOnlySpan(BaseModel):
    """Appendix A.2 — red-flag-rule match with no corresponding urgent claim.

    Char offsets index into the original raw_text. Rendered as the red layer in
    the doctor portal's dual-layer highlight; the eval harness counts any such
    span as a missed escalation if it lacks a matching urgent claim.
    """

    startChar: int
    endChar: int
    ruleKey: str


class AnalyzeResponse(BaseModel):
    """`POST /analyze` and `GET /analyze/cached/{id}` response wrapper.

    Per pilot.md §2 + C4, `escalationMessage` and `redFlagOnlySpans` are
    response-level fields persisted on the immutable `analyze_responses` table.
    They are populated by `/analyze` and `/precompute` and never written to by
    `/review-claim` — the structural separation makes the sticky-escalation
    rule a guarantee rather than a discipline.
    """

    inputId: str
    promptVersionHash: str
    modelId: str
    claims: list[ClinicalClaim] = Field(default_factory=list)
    escalationMessage: str | None = None
    redFlagOnlySpans: list[RedFlagOnlySpan] = Field(default_factory=list)
    createdAt: datetime
