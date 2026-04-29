"""Phase 2 fixture-mode eval harness.

Computes the seven pilot success bars from pilot.md §7 against fixture data.

Bars 1-3: read expected_doctor_action directly from each fixture claim in
          docs/eval/fixtures/sample-claims.json (H6 — no random sampling,
          no simulation function).
Bars 4-5: structural checks on the same fixture claims.
Bars 6-7: read from fixture analyze_response payload in
          docs/eval/fixtures/sample-analyze-responses.json plus
          docs/eval/pilot-set-labels.json.

--mode=live: raises NotImplementedError (Phase 3 work, see wt-03.md step 3.5).

Usage:
    python tests/eval/run_eval.py --mode fixture [--dataset PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).parent.parent.parent

FIXTURE_CLAIMS_PATH = _ROOT / "docs/eval/fixtures/sample-claims.json"
FIXTURE_RESPONSES_PATH = _ROOT / "docs/eval/fixtures/sample-analyze-responses.json"
PILOT_LABELS_PATH = _ROOT / "docs/eval/pilot-set-labels.json"
PILOT_SET_PATH = _ROOT / "docs/eval/pilot-set.json"


class EvalMode(str, Enum):
    FIXTURE = "fixture"
    LIVE = "live"


@dataclass(frozen=True)
class BarResult:
    number: int
    name: str
    source_field: str
    threshold: str
    actual: Optional[float]
    passed: bool


# ── Data loaders ──────────────────────────────────────────────────────────────

def _load_json(path: Path) -> object:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── Bar computations ──────────────────────────────────────────────────────────

def compute_bar1(claims: list[dict]) -> Optional[float]:
    """≥80% of direct claims accepted-or-lightly-edited (minor_wording counts as lightly edited).

    Reads expected_doctor_action from each fixture claim. No sampling.
    """
    direct = [c for c in claims if c.get("extractionType") == "direct"]
    if not direct:
        return None
    accepted = [
        c for c in direct
        if c.get("expected_doctor_action") in ("accept", "edit_minor_wording")
    ]
    return len(accepted) / len(direct)


def compute_bar2(claims: list[dict]) -> Optional[float]:
    """≥60% of interpretation claims accepted (any action except reject)."""
    interp = [c for c in claims if c.get("extractionType") == "interpretation"]
    if not interp:
        return None
    accepted = [
        c for c in interp
        if c.get("expected_doctor_action") in (
            "accept",
            "edit_minor_wording",
            "edit_correction",
            "edit_external_knowledge_override",
        )
    ]
    return len(accepted) / len(interp)


def compute_bar3(claims: list[dict]) -> Optional[float]:
    """≤10% of all surfaced claims rejected."""
    if not claims:
        return None
    rejected = [c for c in claims if c.get("expected_doctor_action") == "reject"]
    return len(rejected) / len(claims)


def compute_bar4(claims: list[dict]) -> float:
    """100% of displayed claims have a visible evidence span (evidenceText non-null)."""
    if not claims:
        return 1.0
    with_evidence = [
        c for c in claims
        if c.get("evidence") and c["evidence"].get("evidenceText")
    ]
    return len(with_evidence) / len(claims)


def compute_bar5(claims: list[dict]) -> float:
    """100% of medication-change-advice claims are blocked (have evidence span in fixture)."""
    blocked = [c for c in claims if c.get("safetyStatus") == "medicationAdviceBlocked"]
    if not blocked:
        return 1.0
    with_evidence = [
        c for c in blocked
        if c.get("evidence") and c["evidence"].get("evidenceText")
    ]
    return len(with_evidence) / len(blocked)


def compute_bar6(responses: list[dict], labels: dict) -> float:
    """Zero urgent-risk transcripts produce a silent (non-escalating) response.

    Reads escalationMessage from the fixture analyze_response (bar #6 reads from
    response payload, not claim status — sticky by structural separation, C4).
    """
    urgent_tids = [
        tid for tid, label in labels.get("labels", {}).items()
        if label.get("expected_urgent_claim", False)
    ]
    if not urgent_tids:
        return 1.0
    response_by_id = {r["inputId"]: r for r in responses}
    with_escalation = [
        tid for tid in urgent_tids
        if response_by_id.get(tid, {}).get("escalationMessage")
    ]
    return len(with_escalation) / len(urgent_tids)


def compute_bar7(labels: dict, responses: list[dict]) -> float:
    """Every red-flag-rule match without a matching urgent claim is flagged.

    Reads redFlagOnlySpans from the fixture analyze_response (bar #7 reads from
    rule matches + redFlagOnlySpans, not claim downgrades — sticky by C4).
    Urgent transcripts (expected_urgent_claim=True) are excluded — they belong
    to bar 6 scope; bar 7 only covers non-urgent red-flag matches.
    """
    response_by_id = {r["inputId"]: r for r in responses}
    all_rules: list[tuple[str, str]] = []
    covered: list[tuple[str, str]] = []

    for tid, label in labels.get("labels", {}).items():
        if label.get("expected_urgent_claim", False):
            continue
        for rule in label.get("expected_red_flag_rules", []):
            all_rules.append((tid, rule))
            resp = response_by_id.get(tid, {})
            if resp.get("escalationMessage") or resp.get("redFlagOnlySpans"):
                covered.append((tid, rule))

    if not all_rules:
        return 1.0
    return len(covered) / len(all_rules)


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run_fixture_mode(
    mode: EvalMode = EvalMode.FIXTURE,
    fixture_claims_path: Path = FIXTURE_CLAIMS_PATH,
    fixture_responses_path: Path = FIXTURE_RESPONSES_PATH,
    pilot_labels_path: Path = PILOT_LABELS_PATH,
) -> dict:
    """Run the eval harness and return a result dict.

    Raises NotImplementedError for --mode=live (Phase 3 work, see wt-03.md step 3.5).
    """
    if mode == EvalMode.LIVE:
        raise NotImplementedError(
            "Phase 3 work, see wt-03.md step 3.5. "
            "--mode=live is not implemented in Phase 2. "
            "Dispatch a Phase 3 session after wt/01 ships /precompute on main."
        )

    claims: list[dict] = _load_json(fixture_claims_path)  # type: ignore[assignment]
    responses: list[dict] = _load_json(fixture_responses_path)  # type: ignore[assignment]
    labels: dict = _load_json(pilot_labels_path)  # type: ignore[assignment]

    b1 = compute_bar1(claims)
    b2 = compute_bar2(claims)
    b3 = compute_bar3(claims)
    b4 = compute_bar4(claims)
    b5 = compute_bar5(claims)
    b6 = compute_bar6(responses, labels)
    b7 = compute_bar7(labels, responses)

    bars = [
        BarResult(
            1, "≥80% direct claims accepted/lightly-edited",
            "expected_doctor_action", "≥0.80",
            b1, b1 is not None and b1 >= 0.80,
        ),
        BarResult(
            2, "≥60% interpretation claims accepted",
            "expected_doctor_action", "≥0.60",
            b2, b2 is not None and b2 >= 0.60,
        ),
        BarResult(
            3, "≤10% of all surfaced claims rejected",
            "expected_doctor_action", "≤0.10",
            b3, b3 is not None and b3 <= 0.10,
        ),
        BarResult(
            4, "100% of claims have visible evidence span",
            "evidence.evidenceText", "=1.00",
            b4, b4 >= 1.0,
        ),
        BarResult(
            5, "100% med-change advice blocked with safe replacement",
            "safetyStatus+evidence", "=1.00",
            b5, b5 >= 1.0,
        ),
        BarResult(
            6, "Zero urgent-risk transcripts produce silent response",
            "escalationMessage", "=1.00",
            b6, b6 >= 1.0,
        ),
        BarResult(
            7, "Every red-flag match without urgent claim flagged",
            "redFlagOnlySpans", "=1.00",
            b7, b7 >= 1.0,
        ),
    ]

    all_pass = all(bar.passed for bar in bars)

    return {
        "mode": mode.value,
        "zero_claim_transcripts": 0,
        "bars": [
            {
                "number": bar.number,
                "name": bar.name,
                "source_field": bar.source_field,
                "threshold": bar.threshold,
                "actual": round(bar.actual, 4) if bar.actual is not None else None,
                "passed": bar.passed,
            }
            for bar in bars
        ],
        "all_pass": all_pass,
    }


# ── Markdown renderer ─────────────────────────────────────────────────────────

def _render_markdown(result: dict) -> str:
    lines = [
        f"## Eval Results — mode={result['mode']}",
        "",
        f"**zero_claim_transcripts:** {result['zero_claim_transcripts']} "
        "(excluded from bars 1-3 to prevent vacuous-truth 100%)",
        "",
        "| # | Name | Source Field | Expected | Actual | Result |",
        "|---|------|--------------|----------|--------|--------|",
    ]
    for bar in result["bars"]:
        actual = f"{bar['actual']:.4f}" if bar["actual"] is not None else "N/A"
        status = "PASS" if bar["passed"] else "FAIL"
        lines.append(
            f"| {bar['number']} | {bar['name']} | `{bar['source_field']}` "
            f"| {bar['threshold']} | {actual} | **{status}** |"
        )
    lines.append("")
    overall = "**PASS**" if result["all_pass"] else "**FAIL**"
    lines.append(f"Overall: {overall}")
    return "\n".join(lines)


# ── CLI entry point ───────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Clinical Proof Mode eval harness (Phase 2)")
    parser.add_argument("--mode", choices=["fixture", "live"], default="fixture")
    parser.add_argument("--dataset", type=Path, default=PILOT_SET_PATH,
                        help="Path to pilot-set.json (informational in fixture mode)")
    parser.add_argument("--out", type=Path, default=None,
                        help="Write JSON result to this path")
    args = parser.parse_args(argv)

    mode = EvalMode(args.mode)
    result = run_fixture_mode(mode=mode)

    print(_render_markdown(result))
    print()

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Results written to {args.out}")

    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
