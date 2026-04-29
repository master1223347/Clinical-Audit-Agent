from fastapi import FastAPI

from app.api import analyze, review
from app.core.precompute import router as precompute_router

app = FastAPI(title="Clinical Proof Mode")

app.include_router(analyze.router, prefix="/analyze")
app.include_router(review.router)
app.include_router(precompute_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
