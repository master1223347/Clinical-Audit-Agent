"""Persistence boundary. Replace in-memory stubs with the real backend later."""

from typing import Protocol

from app.models import (
    AuditLogEntry,
    ClinicalClaim,
    DoctorFeedback,
    PatientInput,
    PatternCard,
    RiskAssessment,
    SafetyBlock,
)


class Repository(Protocol):
    # inputs
    def save_input(self, patient_input: PatientInput) -> None: ...
    def get_input(self, input_id: str) -> PatientInput | None: ...

    # claims
    def save_claim(self, claim: ClinicalClaim) -> None: ...
    def get_claim(self, claim_id: str) -> ClinicalClaim | None: ...
    def list_claims(self, patient_id: str) -> list[ClinicalClaim]: ...

    # risk + safety
    def save_risk(self, risk: RiskAssessment) -> None: ...
    def save_safety_block(self, block: SafetyBlock) -> None: ...
    def list_safety_blocks(self, patient_id: str) -> list[SafetyBlock]: ...

    # doctor feedback
    def save_feedback(self, feedback: DoctorFeedback) -> None: ...
    def list_feedback(self, patient_id: str | None = None) -> list[DoctorFeedback]: ...

    # patterns + audit
    def save_pattern(self, pattern: PatternCard) -> None: ...
    def list_patterns(self, patient_id: str) -> list[PatternCard]: ...
    def append_audit(self, entry: AuditLogEntry) -> None: ...


class InMemoryRepository:
    def __init__(self) -> None:
        self.inputs: dict[str, PatientInput] = {}
        self.claims: dict[str, ClinicalClaim] = {}
        self.risks: dict[str, RiskAssessment] = {}
        self.safety_blocks: dict[str, SafetyBlock] = {}
        self.feedback: dict[str, DoctorFeedback] = {}
        self.patterns: dict[str, PatternCard] = {}
        self.audit: list[AuditLogEntry] = []

    def save_input(self, patient_input: PatientInput) -> None:
        self.inputs[patient_input.inputId] = patient_input

    def get_input(self, input_id: str) -> PatientInput | None:
        return self.inputs.get(input_id)

    def save_claim(self, claim: ClinicalClaim) -> None:
        self.claims[claim.claimId] = claim

    def get_claim(self, claim_id: str) -> ClinicalClaim | None:
        return self.claims.get(claim_id)

    def list_claims(self, patient_id: str) -> list[ClinicalClaim]:
        return [c for c in self.claims.values() if c.patientId == patient_id]

    def save_risk(self, risk: RiskAssessment) -> None:
        self.risks[risk.riskAssessmentId] = risk

    def save_safety_block(self, block: SafetyBlock) -> None:
        self.safety_blocks[block.safetyBlockId] = block

    def list_safety_blocks(self, patient_id: str) -> list[SafetyBlock]:
        return [b for b in self.safety_blocks.values() if b.patientId == patient_id]

    def save_feedback(self, feedback: DoctorFeedback) -> None:
        self.feedback[feedback.feedbackId] = feedback

    def list_feedback(self, patient_id: str | None = None) -> list[DoctorFeedback]:
        items = list(self.feedback.values())
        if patient_id is None:
            return items
        claim_ids = {c.claimId for c in self.claims.values() if c.patientId == patient_id}
        return [f for f in items if f.claimId in claim_ids]

    def save_pattern(self, pattern: PatternCard) -> None:
        self.patterns[pattern.patternId] = pattern

    def list_patterns(self, patient_id: str) -> list[PatternCard]:
        return [p for p in self.patterns.values() if p.patientId == patient_id]

    def append_audit(self, entry: AuditLogEntry) -> None:
        self.audit.append(entry)
