"""§11.3 — POST /report: build the doctor report from accepted/edited claims."""

from fastapi import APIRouter

from app.api.schemas import GenerateReportRequest, GenerateReportResponse

router = APIRouter(prefix="/report", tags=["report"])


@router.post("", response_model=GenerateReportResponse)
def generate_report(req: GenerateReportRequest) -> GenerateReportResponse:
    raise NotImplementedError
