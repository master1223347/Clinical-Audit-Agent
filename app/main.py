from fastapi import FastAPI

from app.api import analyze, metrics, report, review

app = FastAPI(title="Clinical Proof Mode")

app.include_router(analyze.router)
app.include_router(review.router)
app.include_router(report.router)
app.include_router(metrics.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
