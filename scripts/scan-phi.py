#!/usr/bin/env python3
"""PHI scanner for the eval dataset.

Build gate: exits with a count of PHI matches found (0 = clean, non-zero = blocked).

Patterns blocked (per pilot-set-spec.md §PHI-scanner):
  - 10-digit Indian phone numbers starting with 6-9
  - Aadhaar-like 12-digit IDs (groups of 4 digits, optionally space-separated)
  - PAN card format (5 uppercase letters, 4 digits, 1 uppercase letter)
  - Email addresses
  - Patient IDs that do not match the synthetic-NNN format

False-positive tradeoff: medical dose values like "500mg metformin" must NOT
trip any pattern. The patterns below are designed to be conservative:
  - The Aadhaar pattern requires three groups of exactly 4 digits — "500mg"
    (3 digits followed by letters) cannot satisfy this.
  - The PAN pattern requires a very specific alphanumeric structure unlikely
    in plain medical text.
  - The phone pattern requires exactly 10 digits starting with 6-9 at a word
    boundary — standalone dose numbers don't reach 10 digits.

Usage:
    python scripts/scan-phi.py [path ...]
    # default path: docs/eval/pilot-set.json

Exit code = number of PHI findings (0 = clean).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# ── PHI patterns ──────────────────────────────────────────────────────────────

# 10-digit Indian phone number starting with 6-9 at a word boundary,
# or ISD-prefixed form (+91XXXXXXXXXX). "9876543210" and "+919876543210" both match.
# "500mg" (3 digits) does not.
_PHONE = re.compile(r"(?<!\d)(?:\+91[\s\-]?)?[6-9]\d{9}(?!\d)")

# Aadhaar-like: three groups of exactly 4 digits, optional single space between.
# "1234 5678 9012" and "123456789012" both match.
# "1000mg" does not because the letter immediately prevents the next \d{4} group.
_AADHAAR = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")

# PAN card: AAAAA9999A where position 4 (0-indexed) must be a valid NSDL taxpayer
# category letter (A, B, C, F, G, H, J, L, P, T). This excludes medical lab codes
# whose 4th character is typically a domain letter (M, D, S, X, etc.).
_PAN = re.compile(r"\b[A-Z]{3}[ABCFGHJLPT][A-Z]\d{4}[A-Z]\b")

# Email address: anything@domain.tld
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# Real doctor / clinic deny-list (empty for pilot; add names when sourcing begins).
_DENY_LISTED_NAMES: list[str] = []

# Patient IDs must match this format — anything else is suspicious.
_SYNTHETIC_ID = re.compile(r"^synthetic-\d{3,}$")


def _scan_text(text: str, source: str) -> list[str]:
    findings: list[str] = []
    for match in _PHONE.finditer(text):
        findings.append(f"{source}: Indian phone number: {match.group()!r} at pos {match.start()}")
    for match in _AADHAAR.finditer(text):
        findings.append(f"{source}: Aadhaar-like ID: {match.group()!r} at pos {match.start()}")
    for match in _PAN.finditer(text):
        findings.append(f"{source}: PAN pattern: {match.group()!r} at pos {match.start()}")
    for match in _EMAIL.finditer(text):
        findings.append(f"{source}: email address: {match.group()!r} at pos {match.start()}")
    for name in _DENY_LISTED_NAMES:
        if name.lower() in text.lower():
            findings.append(f"{source}: deny-listed name: {name!r}")
    return findings


def _scan_file(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    findings = _scan_text(raw, str(path))

    # Additionally validate every patientId is synthetic.
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        findings.append(f"{path}: invalid JSON — {exc}")
        return findings

    for transcript in data.get("transcripts", []):
        pid = transcript.get("patientId", "")
        if not pid or not _SYNTHETIC_ID.match(pid):
            findings.append(
                f"{path}: non-synthetic patientId {pid!r} "
                "(must match synthetic-\\d{3,})"
            )

    return findings


def main(argv: list[str]) -> int:
    paths = [Path(p) for p in argv[1:]] if len(argv) > 1 else [Path("docs/eval/pilot-set.json")]

    all_findings: list[str] = []
    for path in paths:
        if not path.exists():
            print(f"ERROR: {path} not found", file=sys.stderr)
            return 1
        all_findings.extend(_scan_file(path))

    if all_findings:
        for finding in all_findings:
            print(f"PHI DETECTED: {finding}")
        print(f"\nTotal: {len(all_findings)} PHI finding(s). Build blocked.")
        return 1

    print(f"PHI scan clean: 0 matches across {[str(p) for p in paths]}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
