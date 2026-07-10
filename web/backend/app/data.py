from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "data"
PREDICTIONS_DIR = DATA_DIR / "mvp_predictions"
RESULTS_DIR = DATA_DIR / "mvp_results"
SEASON_DATES_PATH = DATA_DIR / "season_dates.csv"

PREDICTION_PATTERN = re.compile(
    r"^predictions_(?P<year>\d{4})_wk(?P<week>\d+)_(?P<timestamp>\d{8}_\d{4})\.csv$"
)


@dataclass(frozen=True)
class PredictionFile:
    year: int
    week: int
    generated_at: datetime
    path: Path


@dataclass(frozen=True)
class SeasonDates:
    year: int
    start: date
    end: date


def season_label(year: int) -> str:
    return f"{year - 1}–{str(year)[-2:]}"


def _number(value: str | None, *, integer: bool = False) -> int | float:
    try:
        number = float(value or 0)
    except ValueError:
        number = 0
    return int(round(number)) if integer else number


def _clean_team(value: str | None) -> str:
    team = (value or "").removeprefix("Team.").replace("_", " ").title()
    return team.replace("76Ers", "76ers")


def _clean_player(value: str | None) -> str:
    return (value or "").split("\\", 1)[0].strip()


def prediction_index() -> dict[int, list[PredictionFile]]:
    index: dict[int, list[PredictionFile]] = {}
    if not PREDICTIONS_DIR.exists():
        return index

    for path in PREDICTIONS_DIR.glob("*/*.csv"):
        match = PREDICTION_PATTERN.match(path.name)
        if not match:
            continue
        item = PredictionFile(
            year=int(match.group("year")),
            week=int(match.group("week")),
            generated_at=datetime.strptime(match.group("timestamp"), "%Y%m%d_%H%M"),
            path=path,
        )
        index.setdefault(item.year, []).append(item)

    for files in index.values():
        files.sort(key=lambda item: (item.week, item.generated_at))
    return index


def season_dates() -> list[SeasonDates]:
    if not SEASON_DATES_PATH.exists():
        return []

    with SEASON_DATES_PATH.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        dates = [
            SeasonDates(
                year=int(row["year"]),
                start=date.fromisoformat(row["start_date"]),
                end=date.fromisoformat(row["end_date"]),
            )
            for row in rows
        ]
    return sorted(dates, key=lambda item: item.year)


def available_seasons() -> list[dict[str, Any]]:
    index = prediction_index()
    return [
        {
            "year": year,
            "label": season_label(year),
            "weeks": [item.week for item in files],
            "latestWeek": files[-1].week,
            "resultsAvailable": (RESULTS_DIR / f"results_{year}.csv").exists(),
        }
        for year, files in sorted(index.items(), reverse=True)
    ]


def _first_prediction_date(start: date) -> date:
    wednesday = 2
    days_until = (wednesday - start.weekday()) % 7
    candidate = start + timedelta(days=days_until)
    if candidate < start + timedelta(days=7):
        candidate += timedelta(days=7)
    return candidate


def home_state(today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    dates = season_dates()
    index = prediction_index()

    active = next((item for item in dates if item.start <= today <= item.end), None)
    upcoming = next((item for item in dates if item.start > today), None)

    if active:
        predictions = index.get(active.year, [])
        available = [item for item in predictions if item.generated_at.date() <= today]
        if available:
            latest = available[-1]
            return {
                "status": "in_season",
                "seasonYear": active.year,
                "seasonLabel": season_label(active.year),
                "week": latest.week,
                "seasonStart": active.start.isoformat(),
                "seasonEnd": active.end.isoformat(),
                "countdown": None,
            }

        first_prediction = _first_prediction_date(active.start)
        return {
            "status": "awaiting_first_prediction",
            "seasonYear": active.year,
            "seasonLabel": season_label(active.year),
            "week": None,
            "seasonStart": active.start.isoformat(),
            "seasonEnd": active.end.isoformat(),
            "countdown": {
                "kind": "first_prediction",
                "target": first_prediction.isoformat(),
            },
        }

    completed_years = [year for year, files in index.items() if files]
    if not completed_years:
        return {
            "status": "no_data",
            "seasonYear": None,
            "seasonLabel": None,
            "week": None,
            "countdown": None,
        }

    latest_year = max(completed_years)
    latest = index[latest_year][-1]
    results_available = (RESULTS_DIR / f"results_{latest_year}.csv").exists()
    countdown = None
    if upcoming:
        countdown = {
            "kind": "next_season",
            "target": upcoming.start.isoformat(),
            "seasonYear": upcoming.year,
            "seasonLabel": season_label(upcoming.year),
        }

    return {
        "status": "offseason_results" if results_available else "offseason_waiting_results",
        "seasonYear": latest_year,
        "seasonLabel": season_label(latest_year),
        "week": latest.week,
        "resultsAvailable": results_available,
        "countdown": countdown,
    }


def _prediction_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        normalized = [
            {
                "rank": _number(row.get("Rank"), integer=True),
                "player": _clean_player(row.get("Player")),
                "team": _clean_team(row.get("Team")),
                "predictedVotes": _number(row.get("Predicted Votes"), integer=True),
                "gamesPlayed": _number(row.get("GP"), integer=True),
                "points": _number(row.get("PTS")),
                "rebounds": _number(row.get("REB")),
                "assists": _number(row.get("AST")),
                "trueShooting": _number(row.get("TS %") or row.get("TS%")),
                "winPercentage": _number(row.get("Win %")),
            }
            for row in rows
        ]
    normalized.sort(key=lambda row: (-row["predictedVotes"], -row["points"]))
    return normalized[:30]


def _result_rows(year: int) -> dict[str, dict[str, int]]:
    path = RESULTS_DIR / f"results_{year}.csv"
    if not path.exists():
        return {}

    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        results: dict[str, dict[str, int]] = {}
        for row in rows:
            player = _clean_player(row.get("Player"))
            rank_match = re.match(r"\d+", row.get("Rank", ""))
            results[player] = {
                "actualRank": int(rank_match.group()) if rank_match else 0,
                "actualVotes": int(round(_number(row.get("Pts Won")))),
            }
    return results


def prediction_week(year: int, week: int) -> dict[str, Any] | None:
    files = prediction_index().get(year, [])
    matching = [item for item in files if item.week == week]
    if not matching:
        return None

    selected = matching[-1]
    weeks = sorted({item.week for item in files})
    position = weeks.index(week)
    is_final = week == weeks[-1]
    rows = _prediction_rows(selected.path)
    results_available = (RESULTS_DIR / f"results_{year}.csv").exists()

    if is_final and results_available:
        results = _result_rows(year)
        for row in rows:
            actual = results.get(row["player"])
            row["actualRank"] = actual["actualRank"] if actual else None
            row["actualVotes"] = actual["actualVotes"] if actual else 0

    return {
        "year": year,
        "seasonLabel": season_label(year),
        "week": week,
        "generatedAt": selected.generated_at.isoformat(),
        "isFinal": is_final,
        "resultsAvailable": results_available,
        "previousWeek": weeks[position - 1] if position > 0 else None,
        "nextWeek": weeks[position + 1] if position < len(weeks) - 1 else None,
        "rows": rows,
    }
