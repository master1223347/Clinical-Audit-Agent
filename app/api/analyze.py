"""§11.1 — POST /analyze: turn patient input into clinical proof objects."""

from fastapi import APIRouter

from app.api.schemas import AnalyzeRequest, AnalyzeResponse

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("", response_model=AnalyzeResponse)
def analyze_input(req: AnalyzeRequest) -> AnalyzeResponse:
    """Build a PatientInput, run `core.pipeline.analyze`, return the response."""
    raise NotImplementedError
