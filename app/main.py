import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import analyze, review
from app.core.extraction import ExtractionUnavailable
from app.core.precompute import router as precompute_router

_DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"

app = FastAPI(title="Clinical Proof Mode")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o.strip()
        for o in os.environ.get("CORS_ALLOW_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
        if o.strip()
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(analyze.router, prefix="/analyze")
app.include_router(review.router)
app.include_router(precompute_router)


@app.exception_handler(ExtractionUnavailable)
def extraction_unavailable_handler(
    _request: Request, exc: ExtractionUnavailable
) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
