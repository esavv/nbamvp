import os
import re
import traceback
from datetime import date, datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

SEASON_DATES_CSV = '../data/season_dates.csv'
USER_AGENT = 'nbamvp-bot/1.0 (+https://github.com/esavv/nbamvp)'
DURATION_SKIP_KEYWORDS = ('nba cup', 'play-in', 'playoffs', 'finals')
DATE_RANGE_PATTERN = re.compile(
  r'\b[A-Za-z]+\s+\d{1,2},\s+\d{4}\b\s*[\u2013-]\s*\b[A-Za-z]+\s+\d{1,2},\s+\d{4}\b'
)

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


def _extract_duration_lines(data_cell) -> list[str]:
  if data_cell.find('li'):
    return [li.get_text(' ', strip=True) for li in data_cell.find_all('li')]

  text = data_cell.get_text('\n', strip=True)
  return [line.strip() for line in re.split(r'\n+', text) if line.strip()]


def _select_season_range(lines: list[str]) -> str | None:
  for line in lines:
    lower = line.lower()
    if any(keyword in lower for keyword in DURATION_SKIP_KEYWORDS):
      continue
    if DATE_RANGE_PATTERN.search(line):
      return line
  return None


def _parse_date_range(range_text: str) -> tuple[date, date]:
  parts = re.split(r'[\u2013-]', range_text)
  if len(parts) < 2:
    raise ValueError(f"Unrecognized date range format: {range_text}")

  start_str = parts[0].strip()
  end_str = parts[1].strip()
  start_date = date_parser.parse(start_str, fuzzy=True).date()
  end_date = date_parser.parse(end_str, fuzzy=True).date()
  return start_date, end_date


def _upsert_season_dates(
  season_year: int,
  start_iso: str,
  end_iso: str,
  csv_path=SEASON_DATES_CSV,
  allow_update: bool = False,
) -> str:
  csv_path = os.path.abspath(csv_path)

  if not os.path.exists(csv_path):
    df = pd.DataFrame(columns=['year', 'start_date', 'end_date'])
  else:
    try:
      df = pd.read_csv(csv_path, dtype={'year': int, 'start_date': str, 'end_date': str})
    except Exception as exc:
      raise ValueError(f"Unable to read season dates file: {exc}") from exc

  mask = (df['year'] == int(season_year)) if not df.empty else pd.Series(dtype=bool)

  if not df.empty and mask.any():
    if not allow_update:
      return 'exists'
    df.loc[mask, ['start_date', 'end_date']] = [start_iso, end_iso]
    action = 'updated'
  else:
    new_row = pd.DataFrame([
      {
        'year': int(season_year),
        'start_date': start_iso,
        'end_date': end_iso,
      }
    ])
    df = pd.concat([df, new_row], ignore_index=True)
    action = 'inserted'

  df.to_csv(csv_path, index=False)
  return action


def fetch_next_season_dates(
  current_season_year: int,
  mode: str = 'postseason',
  existing_dates: tuple[date, date] | None = None,
  timeout: float = 10.0,
  csv_path=SEASON_DATES_CSV,
) -> dict:
  """Fetch and persist the next season's start/end dates from Wikipedia.

  Parameters
  ----------
  current_season_year: int
      The season year (end year). Postseason will fetch year+1, preseason re-validates year.
  mode: {'postseason','preseason'}
      Controls whether we append (postseason) or verify/update (preseason) the CSV.
  existing_dates: tuple(date, date) | tuple(str, str)
      Required for preseason mode. Represents current CSV values for comparison.

  Returns
  -------
  dict
      Keys: status, message, wiki_url, csv_note, start_date, end_date, season_year, and
      append_traceback if CSV writes failed.
  """
  if mode not in {'postseason', 'preseason'}:
    raise ValueError("mode must be 'postseason' or 'preseason'")

  if mode == 'preseason' and existing_dates is None:
    raise ValueError("existing_dates must be provided for preseason mode")

  if mode == 'postseason':
    scrape_year = current_season_year + 1
  else:
    scrape_year = current_season_year

  next_season_suffix = str(scrape_year)[-2:]
  url = f"https://en.wikipedia.org/wiki/{scrape_year-1}-{next_season_suffix}_NBA_season"
  headers = {'User-Agent': USER_AGENT}

  base_result = {
    'status': None,
    'message': None,
    'wiki_url': url,
    'csv_note': 'No CSV update performed.',
    'start_date': '',
    'end_date': '',
    'season_year': scrape_year,
  }

  try:
    response = requests.get(url, headers=headers, timeout=timeout)
  except requests.RequestException as exc:
    base_result.update({
      'status': 'network_error',
      'message': f'Unable to reach Wikipedia: {exc}',
    })
    return base_result

  if response.status_code == 404:
    base_result.update({
      'status': 'page_missing',
      'message': 'Next season Wikipedia page has not been published yet.',
    })
    return base_result

  if response.status_code != 200:
    base_result.update({
      'status': 'http_error',
      'message': f'Wikipedia responded with status code {response.status_code}.',
    })
    return base_result

  soup = BeautifulSoup(response.text, 'html.parser')
  infobox = soup.find('table', class_='infobox')
  if not infobox:
    base_result.update({
      'status': 'structure_missing',
      'message': 'Unable to locate the season infobox on Wikipedia (structure may have changed).',
    })
    return base_result

  duration_row = None
  for row in infobox.find_all('tr'):
    label_cell = row.find(class_='infobox-label')
    if label_cell and label_cell.get_text(strip=True).lower() == 'duration':
      duration_row = row
      break

  if not duration_row:
    base_result.update({
      'status': 'duration_missing',
      'message': 'Could not find the "Duration" row in the infobox.',
    })
    return base_result

  data_cell = duration_row.find(class_='infobox-data')
  if not data_cell:
    base_result.update({
      'status': 'duration_missing',
      'message': 'Duration row found, but missing data.',
    })
    return base_result

  lines = _extract_duration_lines(data_cell)
  range_text = _select_season_range(lines)
  if not range_text:
    base_result.update({
      'status': 'dates_missing',
      'message': 'Duration information found, but the season dates were not listed yet.',
    })
    return base_result

  try:
    start_date_value, end_date_value = _parse_date_range(range_text)
  except Exception as exc:
    base_result.update({
      'status': 'parse_error',
      'message': f'Unable to parse season dates: {exc}',
    })
    return base_result

  start_iso = start_date_value.isoformat()
  end_iso = end_date_value.isoformat()

  base_result.update({
    'status': 'success',
    'message': f'Found season dates: {start_iso} to {end_iso}.',
    'start_date': start_iso,
    'end_date': end_iso,
  })

  try:
    if mode == 'postseason':
      action = _upsert_season_dates(scrape_year, start_iso, end_iso, csv_path=csv_path, allow_update=False)
      if action == 'inserted':
        base_result['csv_note'] = f'Saved season {scrape_year} dates to season_dates.csv.'
      else:
        base_result['csv_note'] = f'Season {scrape_year} already present in season_dates.csv.'
    else:
      stored_start, stored_end = existing_dates
      stored_start_iso = stored_start.isoformat() if isinstance(stored_start, date) else str(stored_start)
      stored_end_iso = stored_end.isoformat() if isinstance(stored_end, date) else str(stored_end)

      if stored_start_iso == start_iso and stored_end_iso == end_iso:
        base_result['csv_note'] = 'No changes to upcoming season dates.'
      else:
        _ = _upsert_season_dates(scrape_year, start_iso, end_iso, csv_path=csv_path, allow_update=True)
        base_result['csv_note'] = 'Season dates have changed! Updated stored dates.'
  except Exception as exc:
    base_result['csv_note'] = f'ERROR: Failed to update season_dates.csv with season dates: {exc}'
    base_result['append_error'] = str(exc)
    base_result['append_traceback'] = traceback.format_exc()

  return base_result
