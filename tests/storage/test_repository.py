"""SQLite two-table repository tests — pilot.md §6.1.7, C4."""

import sqlite3
import os
import tempfile
from datetime import datetime, timezone

import pytest

from app.storage.repository import ClaimsRepository


def _make_repo(tmp_path: str) -> ClaimsRepository:
    return ClaimsRepository(db_path=tmp_path)


def _ts() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class TestFKEnforcement:
    """FK enforcement test — wt-01.md required test #10."""

    def test_fk_enforcement_rejects_orphan_claim(self, tmp_path) -> None:
        """Insert claim with bogus FK triple; assert IntegrityError."""
        repo = _make_repo(str(tmp_path / "claims.db"))

        with pytest.raises(sqlite3.IntegrityError):
            repo.insert_claim_raw(
                claim_id="c-orphan",
                input_id="no-such-input",
                prompt_version_hash="no-such-hash",
                model_id="no-such-model",
                patient_id="p1",
                claim_text="orphan claim",
                original_claim_text=None,
                event_type="vomiting",
                evidence_text="test",
                evidence_start=0,
                evidence_end=4,
                confidence=0.9,
                extraction_type="direct",
                risk_level="low",
                safety_status="safe",
                doctor_review_status="pending",
                doctor_edit_origin=None,
                created_at=_ts(),
            )


class TestAnalyzeResponsesTable:

    def test_insert_and_retrieve_analyze_response(self, tmp_path) -> None:
        repo = _make_repo(str(tmp_path / "claims.db"))

        repo.insert_analyze_response(
            input_id="inp-1",
            prompt_version_hash="hash-abc",
            model_id="claude-sonnet-4-6",
            patient_id="p1",
            raw_text="I threw up twice.",
            escalation_message=None,
            red_flag_only_spans_json=None,
            created_at=_ts(),
        )

        row = repo.get_analyze_response("inp-1", "hash-abc", "claude-sonnet-4-6")
        assert row is not None
        assert row["input_id"] == "inp-1"
        assert row["patient_id"] == "p1"

    def test_get_analyze_response_returns_none_when_missing(self, tmp_path) -> None:
        repo = _make_repo(str(tmp_path / "claims.db"))
        row = repo.get_analyze_response("no-id", "no-hash", "no-model")
        assert row is None

    def test_analyze_response_stores_escalation_message(self, tmp_path) -> None:
        repo = _make_repo(str(tmp_path / "claims.db"))

        escalation = "This may be urgent. Please seek emergency medical help now."
        repo.insert_analyze_response(
            input_id="inp-2",
            prompt_version_hash="hash-abc",
            model_id="claude-sonnet-4-6",
            patient_id="p1",
            raw_text="chest pain severe",
            escalation_message=escalation,
            red_flag_only_spans_json=None,
            created_at=_ts(),
        )

        row = repo.get_analyze_response("inp-2", "hash-abc", "claude-sonnet-4-6")
        assert row["escalation_message"] == escalation

    def test_analyze_response_immutable_no_update_method(self, tmp_path) -> None:
        """analyze_responses has no update method — structural immutability."""
        repo = _make_repo(str(tmp_path / "claims.db"))
        assert not hasattr(repo, "update_analyze_response"), (
            "Repository must not have update_analyze_response — "
            "analyze_responses rows are immutable after creation"
        )


class TestClaimsTable:

    def _insert_parent(self, repo: ClaimsRepository) -> None:
        repo.insert_analyze_response(
            input_id="inp-1",
            prompt_version_hash="hash-abc",
            model_id="claude-sonnet-4-6",
            patient_id="p1",
            raw_text="test",
            escalation_message=None,
            red_flag_only_spans_json=None,
            created_at=_ts(),
        )

    def test_insert_and_retrieve_claim(self, tmp_path) -> None:
        repo = _make_repo(str(tmp_path / "claims.db"))
        self._insert_parent(repo)

        repo.insert_claim_raw(
            claim_id="claim-1",
            input_id="inp-1",
            prompt_version_hash="hash-abc",
            model_id="claude-sonnet-4-6",
            patient_id="p1",
            claim_text="Patient reported vomiting.",
            original_claim_text=None,
            event_type="vomiting",
            evidence_text="threw up",
            evidence_start=0,
            evidence_end=8,
            confidence=0.9,
            extraction_type="direct",
            risk_level="low",
            safety_status="safe",
            doctor_review_status="pending",
            doctor_edit_origin=None,
            created_at=_ts(),
        )

        claim = repo.get_claim("claim-1")
        assert claim is not None
        assert claim["claim_text"] == "Patient reported vomiting."
        assert claim["doctor_review_status"] == "pending"

    def test_update_claim_review_status(self, tmp_path) -> None:
        repo = _make_repo(str(tmp_path / "claims.db"))
        self._insert_parent(repo)

        repo.insert_claim_raw(
            claim_id="claim-2",
            input_id="inp-1",
            prompt_version_hash="hash-abc",
            model_id="claude-sonnet-4-6",
            patient_id="p1",
            claim_text="Patient reported dizziness.",
            original_claim_text=None,
            event_type="dizziness",
            evidence_text="felt dizzy",
            evidence_start=0,
            evidence_end=10,
            confidence=0.8,
            extraction_type="direct",
            risk_level="low",
            safety_status="safe",
            doctor_review_status="pending",
            doctor_edit_origin=None,
            created_at=_ts(),
        )

        repo.update_claim(
            claim_id="claim-2",
            doctor_review_status="accepted",
            claim_text=None,
            original_claim_text=None,
            doctor_edit_origin=None,
        )

        claim = repo.get_claim("claim-2")
        assert claim["doctor_review_status"] == "accepted"

    def test_update_claim_preserves_original_claim_text(self, tmp_path) -> None:
        repo = _make_repo(str(tmp_path / "claims.db"))
        self._insert_parent(repo)

        original = "Patient reported vomiting."
        repo.insert_claim_raw(
            claim_id="claim-3",
            input_id="inp-1",
            prompt_version_hash="hash-abc",
            model_id="claude-sonnet-4-6",
            patient_id="p1",
            claim_text=original,
            original_claim_text=None,
            event_type="vomiting",
            evidence_text="threw up",
            evidence_start=0,
            evidence_end=8,
            confidence=0.9,
            extraction_type="direct",
            risk_level="low",
            safety_status="safe",
            doctor_review_status="pending",
            doctor_edit_origin=None,
            created_at=_ts(),
        )

        repo.update_claim(
            claim_id="claim-3",
            doctor_review_status="edited",
            claim_text="Patient reported vomiting twice after dinner.",
            original_claim_text=original,
            doctor_edit_origin="minor_wording",
        )

        claim = repo.get_claim("claim-3")
        assert claim["original_claim_text"] == original
        assert claim["claim_text"] == "Patient reported vomiting twice after dinner."

    def test_list_claims_by_response_key(self, tmp_path) -> None:
        repo = _make_repo(str(tmp_path / "claims.db"))
        self._insert_parent(repo)

        for i in range(3):
            repo.insert_claim_raw(
                claim_id=f"claim-{i}",
                input_id="inp-1",
                prompt_version_hash="hash-abc",
                model_id="claude-sonnet-4-6",
                patient_id="p1",
                claim_text=f"Claim {i}.",
                original_claim_text=None,
                event_type="vomiting",
                evidence_text="threw up",
                evidence_start=0,
                evidence_end=8,
                confidence=0.9,
                extraction_type="direct",
                risk_level="low",
                safety_status="safe",
                doctor_review_status="pending",
                doctor_edit_origin=None,
                created_at=_ts(),
            )

        claims = repo.list_claims_for_response("inp-1", "hash-abc", "claude-sonnet-4-6")
        assert len(claims) == 3

    def test_zero_claims_returns_empty_list(self, tmp_path) -> None:
        repo = _make_repo(str(tmp_path / "claims.db"))
        self._insert_parent(repo)

        claims = repo.list_claims_for_response("inp-1", "hash-abc", "claude-sonnet-4-6")
        assert claims == []

    def test_truncate_both_tables(self, tmp_path) -> None:
        repo = _make_repo(str(tmp_path / "claims.db"))
        self._insert_parent(repo)
        repo.insert_claim_raw(
            claim_id="c1",
            input_id="inp-1",
            prompt_version_hash="hash-abc",
            model_id="claude-sonnet-4-6",
            patient_id="p1",
            claim_text="x",
            original_claim_text=None,
            event_type="vomiting",
            evidence_text="x",
            evidence_start=0,
            evidence_end=1,
            confidence=0.5,
            extraction_type="direct",
            risk_level="low",
            safety_status="safe",
            doctor_review_status="pending",
            doctor_edit_origin=None,
            created_at=_ts(),
        )

        repo.truncate_all()

        assert repo.get_analyze_response("inp-1", "hash-abc", "claude-sonnet-4-6") is None
        assert repo.get_claim("c1") is None
