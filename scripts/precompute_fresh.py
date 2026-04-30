"""Destructive precompute helper for `make precompute-fresh`.

Truncates BOTH ``analyze_responses`` and ``claims`` tables in the SQLite
backend, then POSTs all transcripts in ``docs/eval/pilot-set.json`` to the
running wt-01 ``/precompute`` endpoint. Wipes any demo reviewer-click state.

Usage:
    python scripts/precompute_fresh.py [--host http://localhost:8000]
                                       [--dataset docs/eval/pilot-set.json]
                                       [--db-path .data/claims.db]

Designed to be invoked from the root Makefile. Hard-fails (exit 1) if either
the truncate or the /precompute roundtrip fails — the caller (Makefile)
relies on this exit code.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.storage.repository import ClaimsRepository  # noqa: E402  — sys.path

DEFAULT_HOST = "http://localhost:8000"
DEFAULT_DATASET = _REPO_ROOT / "docs/eval/pilot-set.json"
DEFAULT_DB_PATH = ".data/claims.db"
PRECOMPUTE_TIMEOUT_S = 120.0


def _load_transcripts(dataset_path: Path) -> list[dict[str, Any]]:
    with open(dataset_path, encoding="utf-8") as f:
        data = json.load(f)
    transcripts = data.get("transcripts")
    if not isinstance(transcripts, list):
        raise ValueError(
            f"{dataset_path} missing 'transcripts' list — got {type(transcripts)!r}"
        )
    return transcripts


def _truncate(db_path: str) -> None:
    repo = ClaimsRepository(db_path=db_path)
    repo.truncate_all()


def _post_precompute(
    host: str, transcripts: list[dict[str, Any]]
) -> dict[str, Any]:
    items = [
        {
            "transcript_id": t["id"],
            "raw_text": t["rawText"],
            "patient_id": t["patientId"],
            "context": t.get("context", {}),
        }
        for t in transcripts
    ]
    with httpx.Client(base_url=host, timeout=PRECOMPUTE_TIMEOUT_S) as client:
        response = client.post("/precompute", json=items)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--db-path",
        default=os.environ.get("CLAIMS_DB_PATH", DEFAULT_DB_PATH),
        help="SQLite DB path (default: $CLAIMS_DB_PATH or .data/claims.db)",
    )
    args = parser.parse_args(argv)

    print(f"[precompute-fresh] truncating {args.db_path} ...")
    _truncate(args.db_path)
    print("[precompute-fresh] tables truncated")

    transcripts = _load_transcripts(args.dataset)
    print(
        f"[precompute-fresh] POST {args.host}/precompute "
        f"({len(transcripts)} transcripts) ..."
    )
    payload = _post_precompute(args.host, transcripts)
    print(
        f"[precompute-fresh] cached={payload.get('cached')} "
        f"refreshed={payload.get('refreshed')} total={payload.get('total')}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
