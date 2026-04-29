"""PHI scanner build gate: scripts/scan-phi.py must exit 0 for the eval dataset.

Also tests false-positive/false-negative boundaries (the security tradeoff boundary
for scan-phi.py per the dispatch brief).
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent.parent
SCAN_SCRIPT = _ROOT / "scripts/scan-phi.py"
DATASET_PATH = _ROOT / "docs/eval/pilot-set.json"


def test_scan_phi_script_exists():
    assert SCAN_SCRIPT.exists(), (
        f"scripts/scan-phi.py not found at {SCAN_SCRIPT}. "
        "The PHI scanner is a build gate — it must exist before the dataset is committed."
    )


def test_dataset_is_phi_clean():
    """The eval dataset must contain no PHI (exit code 0)."""
    result = subprocess.run(
        [sys.executable, str(SCAN_SCRIPT), str(DATASET_PATH)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"PHI detected in {DATASET_PATH}!\nScanner output:\n{result.stdout}\n{result.stderr}"
    )


def test_phi_scanner_detects_indian_phone_number(tmp_path):
    """False-negative prevention: 10-digit Indian phone numbers must be caught."""
    fake = tmp_path / "fake.json"
    fake.write_text(
        '{"transcripts":[{"id":"t99","patientId":"synthetic-999",'
        '"rawText":"Call me at 9876543210 if needed.","context":{},"edge_cases":[]}]}'
    )
    result = subprocess.run(
        [sys.executable, str(SCAN_SCRIPT), str(fake)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        "Scanner failed to detect Indian phone number 9876543210. "
        "False negative — real phone numbers would pass undetected."
    )


def test_phi_scanner_detects_email_address(tmp_path):
    """False-negative prevention: email addresses must be caught."""
    fake = tmp_path / "fake.json"
    fake.write_text(
        '{"transcripts":[{"id":"t99","patientId":"synthetic-999",'
        '"rawText":"Contact me at patient@example.com.","context":{},"edge_cases":[]}]}'
    )
    result = subprocess.run(
        [sys.executable, str(SCAN_SCRIPT), str(fake)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        "Scanner failed to detect email address. False negative."
    )


def test_phi_scanner_does_not_flag_medical_dose(tmp_path):
    """False-positive prevention: '500mg metformin' must NOT trip the scanner."""
    fake = tmp_path / "fake.json"
    fake.write_text(
        '{"transcripts":[{"id":"t99","patientId":"synthetic-999",'
        '"rawText":"patient took 500mg metformin twice daily.","context":{},"edge_cases":[]}]}'
    )
    result = subprocess.run(
        [sys.executable, str(SCAN_SCRIPT), str(fake)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Scanner false-positive on '500mg metformin'. "
        f"Medical dose values must not trip PHI patterns.\nOutput:\n{result.stdout}"
    )


def test_phi_scanner_detects_aadhaar_pattern(tmp_path):
    """False-negative prevention: Aadhaar-like 12-digit IDs must be caught."""
    fake = tmp_path / "fake.json"
    fake.write_text(
        '{"transcripts":[{"id":"t99","patientId":"synthetic-999",'
        '"rawText":"My ID is 1234 5678 9012.","context":{},"edge_cases":[]}]}'
    )
    result = subprocess.run(
        [sys.executable, str(SCAN_SCRIPT), str(fake)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        "Scanner failed to detect Aadhaar-like pattern '1234 5678 9012'. False negative."
    )


def test_phi_scanner_rejects_non_synthetic_patient_id(tmp_path):
    """Non-synthetic patientId format must be flagged."""
    fake = tmp_path / "fake.json"
    fake.write_text(
        '{"transcripts":[{"id":"t99","patientId":"patient-real-123",'
        '"rawText":"Feeling fine today.","context":{},"edge_cases":[]}]}'
    )
    result = subprocess.run(
        [sys.executable, str(SCAN_SCRIPT), str(fake)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        "Scanner failed to reject non-synthetic patientId 'patient-real-123'. "
        "Only 'synthetic-NNN' format is allowed."
    )
