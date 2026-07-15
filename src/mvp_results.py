import os
import tempfile
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup, Comment


MVP_RESULTS_DIR = '../data/mvp_results'
USER_AGENT = 'nbamvp-bot/1.0 (+https://github.com/esavv/nbamvp)'


def _contains_mojibake(value):
  text = str(value)
  if not ('Ä' in text or 'Ã' in text or any('\u0080' <= character <= '\u009f' for character in text)):
    return False
  try:
    repaired = text.encode('latin-1').decode('utf-8')
  except (UnicodeEncodeError, UnicodeDecodeError):
    return False
  return repaired != text


def _existing_results_need_repair(results_path):
  try:
    players = pd.read_csv(results_path, usecols=['Player'], encoding='utf-8-sig')['Player']
  except Exception:
    return False
  return players.astype(str).map(_contains_mojibake).any()


def _find_mvp_table(html):
  soup = BeautifulSoup(html, 'html.parser')
  table = soup.find('table', id='mvp')
  if table:
    return table

  # Basketball Reference sometimes wraps tables in HTML comments.
  for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
    if 'id="mvp"' not in comment and "id='mvp'" not in comment:
      continue
    commented_soup = BeautifulSoup(comment, 'html.parser')
    table = commented_soup.find('table', id='mvp')
    if table:
      return table

  return None


def _normalize_columns(dataframe):
  if isinstance(dataframe.columns, pd.MultiIndex):
    dataframe.columns = [
      next(
        (str(value) for value in reversed(column) if value and not str(value).startswith('Unnamed:')),
        str(column[-1]),
      )
      for column in dataframe.columns
    ]
  else:
    dataframe.columns = [str(column) for column in dataframe.columns]
  return dataframe


def fetch_mvp_results(season_year, timeout=10.0, results_dir=MVP_RESULTS_DIR):
  """Fetch and persist Basketball Reference MVP voting results when missing."""
  season_year = int(season_year)
  url = f'https://www.basketball-reference.com/awards/awards_{season_year}.html#mvp'
  results_dir = os.path.abspath(results_dir)
  results_path = os.path.join(results_dir, f'results_{season_year}.csv')

  result = {
    'status': None,
    'message': None,
    'results_url': url,
    'csv_note': 'No CSV update performed.',
    'season_year': season_year,
    'results_path': results_path,
  }

  repair_existing = os.path.exists(results_path) and _existing_results_need_repair(results_path)
  if os.path.exists(results_path) and not repair_existing:
    result.update({
      'status': 'already_exists',
      'message': f'MVP voting results for {season_year} are already available locally.',
      'csv_note': f'Existing results_{season_year}.csv was left unchanged.',
    })
    return result

  headers = {'User-Agent': USER_AGENT}
  try:
    response = requests.get(url, headers=headers, timeout=timeout)
  except requests.RequestException as exc:
    result.update({
      'status': 'network_error',
      'message': f'Unable to reach Basketball Reference: {exc}',
    })
    return result

  if response.status_code == 404:
    result.update({
      'status': 'results_unavailable',
      'message': f'MVP voting results for {season_year} have not been published yet.',
    })
    return result

  if response.status_code != 200:
    result.update({
      'status': 'http_error',
      'message': f'Basketball Reference responded with status code {response.status_code}.',
    })
    return result

  # Pass the response bytes to BeautifulSoup so it honors the page's UTF-8
  # declaration. requests otherwise defaults this response to ISO-8859-1.
  table = _find_mvp_table(response.content)
  if table is None:
    result.update({
      'status': 'results_unavailable',
      'message': f'The {season_year} awards page is available, but its MVP voting table is not.',
    })
    return result

  try:
    dataframe = pd.read_html(StringIO(str(table)))[0]
    dataframe = _normalize_columns(dataframe)
  except Exception as exc:
    result.update({
      'status': 'parse_error',
      'message': f'Unable to parse the MVP voting table: {exc}',
    })
    return result

  required_columns = {'Player', 'Pts Won'}
  if dataframe.empty or not required_columns.issubset(dataframe.columns):
    result.update({
      'status': 'parse_error',
      'message': 'The MVP voting table was empty or missing the Player and Pts Won columns.',
    })
    return result

  points_won = pd.to_numeric(dataframe['Pts Won'], errors='coerce')
  if dataframe['Player'].isna().any() or points_won.isna().any():
    result.update({
      'status': 'parse_error',
      'message': 'The MVP voting table contained invalid player or points data.',
    })
    return result

  try:
    os.makedirs(results_dir, exist_ok=True)
    temp_path = None
    with tempfile.NamedTemporaryFile(
      mode='w',
      encoding='utf-8',
      newline='',
      dir=results_dir,
      prefix=f'.results_{season_year}_',
      suffix='.csv',
      delete=False,
    ) as temp_file:
      temp_path = temp_file.name
      dataframe.to_csv(temp_file, index=False)
    os.replace(temp_path, results_path)
  except Exception as exc:
    if temp_path and os.path.exists(temp_path):
      os.remove(temp_path)
    result.update({
      'status': 'write_error',
      'message': f'Unable to save MVP voting results: {exc}',
    })
    return result

  if repair_existing:
    result.update({
      'status': 'repaired',
      'message': f'Re-fetched MVP voting results for {season_year} to repair player name encoding.',
      'csv_note': f'Replaced results_{season_year}.csv with {len(dataframe)} correctly encoded candidates.',
    })
  else:
    result.update({
      'status': 'saved',
      'message': f'Fetched MVP voting results for {season_year}.',
      'csv_note': f'Saved results_{season_year}.csv with {len(dataframe)} candidates.',
    })
  return result
