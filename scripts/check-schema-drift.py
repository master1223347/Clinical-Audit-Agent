#!/usr/bin/env python
"""Fail CI if Pydantic field sets diverge from packages/shared/types.ts.

The TS file is the single source of truth (pilot.md §1.1, R2 in the risk
register). This script parses the TS interfaces / type unions with regex,
introspects the Pydantic models, and compares field-name sets and enum-value
sets. Any mismatch exits non-zero with a readable diff.

The script intentionally does NOT compare types or optionality — Python's
`int | None = None` and TS's `number | null` are semantically the same here,
and trying to align type spellings produces brittle, low-signal failures. The
field-name parity check is what catches drift in practice.

Run: python scripts/check-schema-drift.py
"""

from __future__ import annotations

import re
import sys
from enum import Enum
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
TS_PATH = REPO_ROOT / "packages" / "shared" / "types.ts"

# Make `app` importable regardless of where the script is invoked from.
sys.path.insert(0, str(REPO_ROOT))

from app.models.analyze import AnalyzeResponse, RedFlagOnlySpan  # noqa: E402
from app.models.claim import ClinicalClaim, Evidence  # noqa: E402
from app.models.enums import (  # noqa: E402
    DoctorAction,
    DoctorEditOrigin,
    DoctorReviewStatus,
    EventType,
    ExtractionType,
    InputType,
    RiskLevel,
    SafetyStatus,
)
from app.models.follow_up import FollowUpQuestion  # noqa: E402
from app.models.risk import RiskAssessment  # noqa: E402
from app.models.safety_block import SafetyBlock  # noqa: E402

# Strip line and block comments before parsing so commented-out fields can't
# leak into the field-name set.
_LINE_COMMENT = re.compile(r"//[^\n]*")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_comments(text: str) -> str:
    return _LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", text))


def parse_ts_interface(text: str, name: str) -> set[str]:
    """Return field names declared inside `export interface NAME { ... }`.

    Handles required (`name:`) and optional (`name?:`) fields. Nested objects
    are skipped — inline anonymous types in the SOT are intentionally rare and
    are matched by regex, not parsed as recursive structures.
    """
    cleaned = _strip_comments(text)
    pattern = rf"export\s+interface\s+{re.escape(name)}\s*\{{(.*?)\n\}}"
    m = re.search(pattern, cleaned, re.DOTALL)
    if not m:
        raise SystemExit(f"interface {name!r} not found in {TS_PATH}")
    body = m.group(1)

    fields: set[str] = set()
    depth = 0
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Track nested {} so anonymous inline objects don't pollute the set.
        # We attribute the field name on the line where depth was 0 *before*
        # the line is processed.
        if depth == 0:
            m2 = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\??\s*:", line)
            if m2:
                fields.add(m2.group(1))
        depth += line.count("{") - line.count("}")
    return fields


def parse_ts_union(text: str, name: str) -> set[str]:
    """Return string-literal members of `export type NAME = "a" | "b" | ...;`."""
    cleaned = _strip_comments(text)
    pattern = rf"export\s+type\s+{re.escape(name)}\s*=\s*([^;]+);"
    m = re.search(pattern, cleaned, re.DOTALL)
    if not m:
        raise SystemExit(f"type {name!r} not found in {TS_PATH}")
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def py_model_fields(model: Any) -> set[str]:
    return set(model.model_fields.keys())


def py_enum_values(enum_cls: type[Enum]) -> set[str]:
    return {member.value for member in enum_cls}


_INTERFACE_PAIRS: list[tuple[str, Any]] = [
    ("Evidence", Evidence),
    ("ClinicalClaim", ClinicalClaim),
    ("RedFlagOnlySpan", RedFlagOnlySpan),
    ("AnalyzeResponse", AnalyzeResponse),
    ("RiskAssessment", RiskAssessment),
    ("SafetyBlock", SafetyBlock),
    ("FollowUpQuestion", FollowUpQuestion),
]

_UNION_PAIRS: list[tuple[str, type[Enum]]] = [
    ("InputType", InputType),
    ("EventType", EventType),
    ("RiskLevel", RiskLevel),
    ("SafetyStatus", SafetyStatus),
    ("DoctorReviewStatus", DoctorReviewStatus),
    ("DoctorAction", DoctorAction),
    ("ExtractionType", ExtractionType),
    ("DoctorEditOrigin", DoctorEditOrigin),
]


def _diff(label: str, kind: str, ts: set[str], py: set[str]) -> str | None:
    if ts == py:
        return None
    only_ts = sorted(ts - py)
    only_py = sorted(py - ts)
    lines = [f"DRIFT in {kind} {label}:"]
    if only_ts:
        lines.append(f"  only in TS:       {only_ts}")
    if only_py:
        lines.append(f"  only in Pydantic: {only_py}")
    return "\n".join(lines)


def main() -> int:
    if not TS_PATH.exists():
        sys.stderr.write(f"missing canonical TS schema at {TS_PATH}\n")
        return 1

    ts_text = TS_PATH.read_text(encoding="utf-8")

    failures: list[str] = []
    for name, model in _INTERFACE_PAIRS:
        ts = parse_ts_interface(ts_text, name)
        py = py_model_fields(model)
        diff = _diff(name, "interface", ts, py)
        if diff:
            failures.append(diff)

    for name, enum_cls in _UNION_PAIRS:
        ts = parse_ts_union(ts_text, name)
        py = py_enum_values(enum_cls)
        diff = _diff(name, "union", ts, py)
        if diff:
            failures.append(diff)

    if failures:
        sys.stderr.write("Schema drift detected (TS is the source of truth).\n\n")
        sys.stderr.write("\n\n".join(failures) + "\n\n")
        sys.stderr.write(
            "Fix by aligning Pydantic field names / enum values to the TS schema in\n"
            "packages/shared/types.ts, or update the TS schema and the Pydantic side\n"
            "in the same commit.\n"
        )
        return 1

    interface_count = len(_INTERFACE_PAIRS)
    union_count = len(_UNION_PAIRS)
    print(
        f"Schema drift check OK — {interface_count} interfaces and {union_count} "
        "unions in sync between TS and Pydantic."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
