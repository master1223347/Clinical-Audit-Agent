"""§10.6 / §15 — Quality dashboard endpoint."""

from fastapi import APIRouter

from app.api.schemas import MetricsResponse, PatternsResponse

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=MetricsResponse)
def get_metrics(patient_id: str | None = None) -> MetricsResponse:
    """Aggregate quality metrics. If `patient_id` is omitted, return clinic-wide."""
    raise NotImplementedError


@router.get("/patterns", response_model=PatternsResponse)
def get_patterns(patient_id: str) -> PatternsResponse:
    """§19 Phase 5 — longitudinal patterns for one patient."""
    raise NotImplementedError
