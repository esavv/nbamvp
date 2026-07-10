from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from .data import available_seasons, home_state, prediction_week


app = FastAPI(
    title="NBA MVP Predictor",
    description="CSV-backed API for weekly NBA MVP predictions.",
    version="1.0.0",
)


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
def get_prediction_week(year: int, week: int) -> dict:
    prediction = prediction_week(year, week)
    if prediction is None:
        raise HTTPException(status_code=404, detail="Prediction week not found")
    return prediction


frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
