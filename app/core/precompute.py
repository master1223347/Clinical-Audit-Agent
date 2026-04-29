"""Precompute pipeline — pilot.md C3/C4.

POST /precompute: batch-runs the full pipeline for each transcript, writes to
both SQLite tables. Idempotent — skips entries that already have a cache hit.
"""

from fastapi import APIRouter, HTTPException

import app.core.extraction as _extraction_mod
from app.api.analyze import _run_pipeline
from app.api.schemas import PrecomputeItem, PrecomputeResponse
from app.storage.deps import get_repo

router = APIRouter(tags=["precompute"])

_MAX_PRECOMPUTE_BATCH = 100


@router.post("/precompute", response_model=PrecomputeResponse)
def precompute(items: list[PrecomputeItem]) -> PrecomputeResponse:
    """Run full pipeline for each transcript; idempotent cache-hit skip.

    Returns counts of cached (already existed) and refreshed (newly computed).
    """
    if len(items) > _MAX_PRECOMPUTE_BATCH:
        raise HTTPException(
            status_code=422,
            detail=f"Batch size {len(items)} exceeds limit of {_MAX_PRECOMPUTE_BATCH}",
        )

    repo = get_repo()
    prompt_hash = _extraction_mod.PROMPT_VERSION_HASH
    model_id = _extraction_mod.MODEL_ID
    cached_count = 0
    refreshed_count = 0

    for item in items:
        existing = repo.get_analyze_response(item.transcript_id, prompt_hash, model_id)
        if existing is not None:
            cached_count += 1
            continue

        _run_pipeline(
            input_id=item.transcript_id,
            patient_id=item.patient_id,
            raw_text=item.raw_text,
            context=item.context,
            repo=repo,
        )
        refreshed_count += 1

    return PrecomputeResponse(
        cached=cached_count,
        refreshed=refreshed_count,
        total=len(items),
    )
