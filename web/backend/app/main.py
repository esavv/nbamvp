from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .analytics import router as analytics_router, shutdown_analytics
from .data import available_seasons, home_state, prediction_week
from .subscriptions import router as subscriptions_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    shutdown_analytics()


app = FastAPI(
    title="NBA MVP Predictor",
    description="CSV-backed API for weekly NBA MVP predictions.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(analytics_router)
app.include_router(subscriptions_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/home")
def get_home() -> dict:
    eastern_today = datetime.now(ZoneInfo("America/New_York")).date()
    return home_state(eastern_today)


@app.get("/api/seasons")
def get_seasons() -> list[dict]:
    return available_seasons()


@app.get("/api/seasons/{year}/weeks/{week}")
def get_prediction_week(year: int, week: int, limit: Annotated[int, Query(ge=1, le=600)] = 30) -> dict:
    prediction = prediction_week(year, week, limit)
    if prediction is None:
        raise HTTPException(status_code=404, detail="Prediction week not found")
    return prediction


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.get("/confirm", include_in_schema=False)
def confirmation_page() -> FileResponse:
    index = frontend_dist / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Frontend build not found")
    return FileResponse(index)


if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
