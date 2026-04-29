"""Two-table SQLite persistence — pilot.md §6.1.7, C4.

analyze_responses: one row per /analyze call, IMMUTABLE after creation.
claims: zero or more rows per response, MUTABLE via /review-claim.

The structural separation enforces the sticky-escalation rule: /review-claim
operates on claims only and has no code path to analyze_responses.
All connections go through db._connect() to ensure foreign_keys = ON.
"""

import os
from typing import Any

from app.storage.db import _connect

_DEFAULT_DB_PATH = ".data/claims.db"

_DDL_ANALYZE_RESPONSES = """
CREATE TABLE IF NOT EXISTS analyze_responses (
    input_id              TEXT NOT NULL,
    prompt_version_hash   TEXT NOT NULL,
    model_id              TEXT NOT NULL,
    patient_id            TEXT NOT NULL,
    raw_text              TEXT NOT NULL,
    escalation_message    TEXT,
    red_flag_only_spans_json TEXT,
    created_at            TEXT NOT NULL,
    PRIMARY KEY (input_id, prompt_version_hash, model_id)
);
"""

_DDL_CLAIMS = """
CREATE TABLE IF NOT EXISTS claims (
    claim_id              TEXT PRIMARY KEY,
    input_id              TEXT NOT NULL,
    prompt_version_hash   TEXT NOT NULL,
    model_id              TEXT NOT NULL,
    patient_id            TEXT NOT NULL,
    claim_text            TEXT NOT NULL,
    original_claim_text   TEXT,
    event_type            TEXT NOT NULL,
    evidence_text         TEXT NOT NULL,
    evidence_start        INTEGER NOT NULL,
    evidence_end          INTEGER NOT NULL,
    confidence            REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    extraction_type       TEXT NOT NULL CHECK (extraction_type IN ('direct','interpretation')),
    risk_level            TEXT NOT NULL CHECK (risk_level IN ('low','medium','high','urgent','needs-review')),
    safety_status         TEXT NOT NULL,
    doctor_review_status  TEXT NOT NULL DEFAULT 'pending',
    doctor_edit_origin    TEXT CHECK (doctor_edit_origin IN ('minor_wording','correction','external_knowledge_override')),
    created_at            TEXT NOT NULL,
    FOREIGN KEY (input_id, prompt_version_hash, model_id)
        REFERENCES analyze_responses(input_id, prompt_version_hash, model_id)
);
"""

_DDL_CLAIMS_INDEX = """
CREATE INDEX IF NOT EXISTS claims_response_lookup
    ON claims(input_id, prompt_version_hash, model_id);
"""


class ClaimsRepository:
    """Persistent two-table SQLite repository."""

    def __init__(self, db_path: str | None = None) -> None:
        self._path = db_path or os.environ.get("CLAIMS_DB_PATH", _DEFAULT_DB_PATH)
        os.makedirs(os.path.dirname(self._path) if os.path.dirname(self._path) else ".", exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        with _connect(self._path) as conn:
            conn.execute(_DDL_ANALYZE_RESPONSES)
            conn.execute(_DDL_CLAIMS)
            conn.execute(_DDL_CLAIMS_INDEX)
            conn.commit()

    # ------------------------------------------------------------------ #
    # analyze_responses (immutable after creation)
    # ------------------------------------------------------------------ #

    def insert_analyze_response(
        self,
        *,
        input_id: str,
        prompt_version_hash: str,
        model_id: str,
        patient_id: str,
        raw_text: str,
        escalation_message: str | None,
        red_flag_only_spans_json: str | None,
        created_at: str,
    ) -> None:
        with _connect(self._path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO analyze_responses
                  (input_id, prompt_version_hash, model_id, patient_id, raw_text,
                   escalation_message, red_flag_only_spans_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    input_id, prompt_version_hash, model_id, patient_id, raw_text,
                    escalation_message, red_flag_only_spans_json, created_at,
                ),
            )
            conn.commit()

    def get_analyze_response(
        self,
        input_id: str,
        prompt_version_hash: str,
        model_id: str,
    ) -> dict[str, Any] | None:
        with _connect(self._path) as conn:
            row = conn.execute(
                """
                SELECT * FROM analyze_responses
                WHERE input_id = ? AND prompt_version_hash = ? AND model_id = ?
                """,
                (input_id, prompt_version_hash, model_id),
            ).fetchone()
        if row is None:
            return None
        return dict(row)

    # ------------------------------------------------------------------ #
    # claims (mutable via /review-claim)
    # ------------------------------------------------------------------ #

    def insert_claim_raw(
        self,
        *,
        claim_id: str,
        input_id: str,
        prompt_version_hash: str,
        model_id: str,
        patient_id: str,
        claim_text: str,
        original_claim_text: str | None,
        event_type: str,
        evidence_text: str,
        evidence_start: int,
        evidence_end: int,
        confidence: float,
        extraction_type: str,
        risk_level: str,
        safety_status: str,
        doctor_review_status: str,
        doctor_edit_origin: str | None,
        created_at: str,
    ) -> None:
        with _connect(self._path) as conn:
            conn.execute(
                """
                INSERT INTO claims
                  (claim_id, input_id, prompt_version_hash, model_id,
                   patient_id, claim_text, original_claim_text, event_type,
                   evidence_text, evidence_start, evidence_end,
                   confidence, extraction_type, risk_level, safety_status,
                   doctor_review_status, doctor_edit_origin, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim_id, input_id, prompt_version_hash, model_id,
                    patient_id, claim_text, original_claim_text, event_type,
                    evidence_text, evidence_start, evidence_end,
                    confidence, extraction_type, risk_level, safety_status,
                    doctor_review_status, doctor_edit_origin, created_at,
                ),
            )
            conn.commit()

    def get_claim(self, claim_id: str) -> dict[str, Any] | None:
        with _connect(self._path) as conn:
            row = conn.execute(
                "SELECT * FROM claims WHERE claim_id = ?",
                (claim_id,),
            ).fetchone()
        if row is None:
            return None
        return dict(row)

    def update_claim(
        self,
        *,
        claim_id: str,
        doctor_review_status: str,
        claim_text: str | None,
        original_claim_text: str | None,
        doctor_edit_origin: str | None,
    ) -> None:
        """Update mutable claim fields. NEVER touches analyze_responses."""
        with _connect(self._path) as conn:
            if claim_text is not None:
                conn.execute(
                    """
                    UPDATE claims
                    SET doctor_review_status = ?,
                        claim_text = ?,
                        original_claim_text = COALESCE(original_claim_text, ?),
                        doctor_edit_origin = ?
                    WHERE claim_id = ?
                    """,
                    (doctor_review_status, claim_text, original_claim_text,
                     doctor_edit_origin, claim_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE claims
                    SET doctor_review_status = ?
                    WHERE claim_id = ?
                    """,
                    (doctor_review_status, claim_id),
                )
            conn.commit()

    def list_claims_for_response(
        self,
        input_id: str,
        prompt_version_hash: str,
        model_id: str,
    ) -> list[dict[str, Any]]:
        with _connect(self._path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM claims
                WHERE input_id = ? AND prompt_version_hash = ? AND model_id = ?
                """,
                (input_id, prompt_version_hash, model_id),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ #
    # Destructive operations (make precompute-fresh)
    # ------------------------------------------------------------------ #

    def truncate_all(self) -> None:
        """Truncate BOTH tables. Destructive — wipes all demo state."""
        with _connect(self._path) as conn:
            conn.execute("DELETE FROM claims")
            conn.execute("DELETE FROM analyze_responses")
            conn.commit()
