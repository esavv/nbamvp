import os
from datetime import datetime
import pandas as pd

SEASON_DATES_CSV = '../data/season_dates.csv'

def load_current_season_dates(csv_path=SEASON_DATES_CSV):
  """Return the season year, start date, and end date for the most recent entry."""
  csv_path = os.path.abspath(csv_path)
  if not os.path.exists(csv_path):
    raise FileNotFoundError(f"Season dates file not found at: {csv_path}")

  try:
    df = pd.read_csv(csv_path, dtype={'year': int, 'start_date': str, 'end_date': str})
  except Exception as exc:
    raise ValueError(f"Unable to read season dates file: {exc}") from exc

  if df.empty:
    raise ValueError("Season dates file is empty.")

  current_row = df.iloc[-1]

  try:
    season_start = datetime.strptime(current_row['start_date'], '%Y-%m-%d').date()
    season_end = datetime.strptime(current_row['end_date'], '%Y-%m-%d').date()
  except Exception as exc:
    raise ValueError(f"Invalid date format in season dates file: {exc}") from exc

  season_year = int(current_row['year'])
  if season_year != season_end.year:
    raise ValueError(
      f"Season year ({season_year}) does not match end date year ({season_end.year}). Update season_dates.csv."
    )

  return season_year, season_start, season_end
