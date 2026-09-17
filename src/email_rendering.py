"""Render production email content without delivery side effects."""

from dataclasses import dataclass
from html import escape
import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_HTML_DIR = PROJECT_ROOT / 'static' / 'html'
TEAM_STYLES_PATH = PROJECT_ROOT / 'data' / 'team_styles.json'
TEAM_STYLES = json.loads(TEAM_STYLES_PATH.read_text(encoding='utf-8'))

MAIN_TEMPLATE_PATH = STATIC_HTML_DIR / 'email_template.html'
PRESEASON_TEMPLATE_PATH = STATIC_HTML_DIR / 'email_template_preseason.html'
POSTSEASON_TEMPLATE_PATH = STATIC_HTML_DIR / 'email_template_postseason.html'
ERROR_TEMPLATE_PATH = STATIC_HTML_DIR / 'email_template_error.html'

PREDICTION_PATTERN = re.compile(
  r'^predictions_(?P<year>\d{4})_wk(?P<week>\d+)_(?P<timestamp>\d{8}_\d{4})\.csv$'
)

ADMIN_TEXT = 'NBA MVP Predictions administrative notification.'
WEEKLY_TEXT = 'The latest NBA MVP predictions are available at https://nba-mvp.com.'


@dataclass(frozen=True)
class RenderedEmail:
  subject: str
  html: str
  text: str


def _format_number(value, decimals=1):
  import pandas as pd

  if pd.isna(value):
    return '—'
  return f'{float(value):.{decimals}f}'


def _team_label(team):
  team_name = str(team).removeprefix('Team.').replace('_', ' ').title()
  team_name = team_name.replace('76Ers', '76ers').replace('Oronto Raptors', 'Toronto Raptors')
  style = TEAM_STYLES.get(team_name)
  if style is None:
    acronym = ''.join(word[0] for word in team_name.split())[:3].upper() or 'NBA'
    style = {'acronym': acronym, 'background': '#475569', 'color': '#FFFFFF'}
  return (
    f'<span title="{escape(team_name, quote=True)}" style="display:inline-block;'
    f'box-sizing:border-box;width:28px;margin-right:7px;padding:3px 0px;border-radius:4px;'
    f'background:{style["background"]};color:{style["color"]};'
    f'font-family:Arial,sans-serif;font-size:9px;font-weight:900;'
    f'letter-spacing:-.2px;line-height:1;text-align:center;vertical-align:1px;">'
    f'{escape(style["acronym"])}</span>'
  )


def _previous_prediction_file(prediction_file, year, week):
  candidates = []
  for path in Path(prediction_file).parent.glob('predictions_*.csv'):
    match = PREDICTION_PATTERN.match(path.name)
    if not match:
      continue
    candidate_year = int(match.group('year'))
    candidate_week = int(match.group('week'))
    if candidate_year == int(year) and candidate_week < int(week):
      candidates.append((candidate_week, match.group('timestamp'), path))
  return max(candidates, default=(None, None, None))[-1]


def _rank_changes(df, previous_prediction_file):
  import pandas as pd

  if previous_prediction_file is None:
    return [None] * len(df)

  previous_df = pd.read_csv(previous_prediction_file)
  previous_ranks = {
    str(row['Player']).split('\\', 1)[0].strip(): int(row['Rank'])
    for _, row in previous_df.iterrows()
  }
  return [
    previous_ranks.get(str(row['Player']).split('\\', 1)[0].strip()) - int(row['Rank'])
    if str(row['Player']).split('\\', 1)[0].strip() in previous_ranks
    else None
    for _, row in df.iterrows()
  ]


def _build_prediction_table(df):
  import pandas as pd

  columns = [
    ('Rank', 'Rank', 'center'),
    (
      'Rank Change',
      '<span style="color:#65a30d;">&#9650;</span>'
      '<span style="color:#e11d48;">&#9660;</span>',
      'center',
    ),
    ('Player', 'Player', 'left'),
    ('Predicted Votes', 'Predicted Votes', 'right'),
    ('PTS', 'PTS', 'right'),
    ('REB', 'REB', 'right'),
    ('AST', 'AST', 'right'),
    ('GP', 'GP', 'right'),
    ('TS %', 'TS%', 'right'),
    ('Win %', 'Win%', 'right'),
  ]

  header_cells = ''.join(
    f'<th style="padding:{"10px 4px" if key == "Rank Change" else "10px 9px"};'
    f'border-bottom:1px solid #e2e8f0;'
    f'background:#f8fafc;color:#64748b;font-family:Arial,sans-serif;'
    f'font-size:10px;font-weight:700;letter-spacing:.5px;text-align:{alignment};'
    f'text-transform:uppercase;white-space:nowrap;">{label}</th>'
    for key, label, alignment in columns
  )

  body_rows = []
  for _, row in df.iterrows():
    rank_change = row['Rank Change']
    if pd.isna(rank_change) or int(rank_change) == 0:
      rank_change_html = '<span style="color:#94a3b8;">-</span>'
    elif rank_change > 0:
      rank_change_html = (
        '<span style="color:#65a30d;font-weight:700;">'
        f'&#9650;&nbsp;{int(rank_change)}</span>'
      )
    else:
      rank_change_html = (
        '<span style="color:#e11d48;font-weight:700;">'
        f'&#9660;&nbsp;{abs(int(rank_change))}</span>'
      )

    values = {
      'Rank': str(int(row['Rank'])),
      'Rank Change': rank_change_html,
      'Player': _team_label(row['Team']) + escape(str(row['Player'])),
      'Predicted Votes': f"{int(row['Predicted Votes']):,}",
      'PTS': _format_number(row['PTS']),
      'REB': _format_number(row['REB']),
      'AST': _format_number(row['AST']),
      'GP': str(int(row['GP'])),
      'TS %': _format_number(float(row.get('TS %', row.get('TS%', 0))) * 100),
      'Win %': _format_number(float(row['Win %']) * 100),
    }

    cells = []
    for key, _, alignment in columns:
      weight = '700' if key in {'Player', 'Predicted Votes'} else '400'
      color = '#0f172a' if key in {'Player', 'Predicted Votes'} else '#475569'
      padding = '11px 4px' if key == 'Rank Change' else '11px 9px'
      cells.append(
        f'<td style="padding:{padding};border-bottom:1px solid #f1f5f9;'
        f'color:{color};font-family:Arial,sans-serif;font-size:12px;'
        f'font-weight:{weight};text-align:{alignment};white-space:nowrap;">'
        f'{values[key]}</td>'
      )
    body_rows.append('<tr>' + ''.join(cells) + '</tr>')

  return (
    '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
    'style="width:100%;border-collapse:collapse;background:#ffffff;">'
    f'<thead><tr>{header_cells}</tr></thead>'
    f'<tbody>{"".join(body_rows)}</tbody></table>'
  )


def render_weekly_email(prediction_file, year, week, is_last_week, unsubscribe_url='#'):
  import pandas as pd

  subject = f'{year} NBA MVP Predictions - Week {week}'
  if is_last_week:
    subject = f'{year} NBA MVP Predictions - Final Week (Week {week})'

  df = pd.read_csv(prediction_file)
  df = df.sort_values(by=['Predicted Votes', 'PTS'], ascending=[False, False]).copy()
  df['Rank'] = df['Rank'].astype(int)
  df['Predicted Votes'] = df['Predicted Votes'].astype(int)
  previous_prediction_file = _previous_prediction_file(prediction_file, year, week)
  df['Rank Change'] = _rank_changes(df, previous_prediction_file)
  table_html = _build_prediction_table(df.head(n=15))

  webapp_url = os.getenv('WEBAPP_URL', 'https://nba-mvp.com').rstrip('/')
  prediction_url = escape(f'{webapp_url}/?{urlencode({"season": year, "week": week})}', quote=True)

  html_template = MAIN_TEMPLATE_PATH.read_text(encoding='utf-8')
  html = html_template.format(
    table_html=table_html,
    prediction_url=prediction_url,
    unsubscribe_url=unsubscribe_url,
  )
  return RenderedEmail(subject, html, WEEKLY_TEXT)


def render_preseason_email(
  year,
  season_start,
  season_end,
  weeks_til_start,
  predict_start_date,
  mode,
  next_season_info,
  voting_results_info,
):
  unit = 'Week' if weeks_til_start == 1 else 'Weeks'
  subject = f'{year} NBA MVP Preseason: First Prediction in {weeks_til_start} {unit}!'
  if mode == 'dev':
    subject = '[TEST] ' + subject

  html_template = PRESEASON_TEMPLATE_PATH.read_text(encoding='utf-8')
  html = html_template.format(
    season_start=season_start,
    season_end=season_end,
    predict_start_date=predict_start_date,
    status=next_season_info.get('status', 'unknown'),
    message=next_season_info.get('message', 'No update available.'),
    wiki_url=next_season_info.get('wiki_url', ''),
    csv_note=next_season_info.get('csv_note', ''),
    voting_season_year=voting_results_info.get('season_year', ''),
    voting_status=voting_results_info.get('status', 'unknown'),
    voting_message=voting_results_info.get('message', 'No update available.'),
    voting_url=voting_results_info.get('results_url', ''),
    voting_csv_note=voting_results_info.get('csv_note', ''),
  )
  return RenderedEmail(subject, html, ADMIN_TEXT)


def render_postseason_email(year, season_end, mode, next_season_info, voting_results_info):
  subject = f'{year} NBA MVP Postseason Notification'
  if mode == 'dev':
    subject = '[TEST] ' + subject

  html_template = POSTSEASON_TEMPLATE_PATH.read_text(encoding='utf-8')
  html = html_template.format(
    season_end=season_end,
    status=next_season_info.get('status', 'unknown'),
    message=next_season_info.get('message', 'No update available.'),
    wiki_url=next_season_info.get('wiki_url', ''),
    csv_note=next_season_info.get('csv_note', ''),
    start_date=next_season_info.get('start_date', ''),
    end_date=next_season_info.get('end_date', ''),
    voting_season_year=voting_results_info.get('season_year', ''),
    voting_status=voting_results_info.get('status', 'unknown'),
    voting_message=voting_results_info.get('message', 'No update available.'),
    voting_url=voting_results_info.get('results_url', ''),
    voting_csv_note=voting_results_info.get('csv_note', ''),
  )
  return RenderedEmail(subject, html, ADMIN_TEXT)


def render_error_email(year, week, traceback_str):
  subject = f'ERROR: {year} NBA MVP Predictions - Week {week}'
  html_template = ERROR_TEMPLATE_PATH.read_text(encoding='utf-8')
  html = html_template.replace('{traceback_str}', traceback_str)
  return RenderedEmail(subject, html, ADMIN_TEXT)


def render_subscription_confirmation_email(confirmation_url):
  subject = 'Confirm your NBA MVP subscription'
  html = f"""<!doctype html>
<html lang="en">
  <body style="margin:0;padding:24px;background:#f1f5f9;font-family:Arial,sans-serif;color:#0f172a;">
    <div style="max-width:560px;margin:0 auto;padding:28px;background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;">
      <p style="margin:0 0 22px;color:#64748b;line-height:1.6;">
        Thanks for subscribing to nba-mvp.com! Please confirm that you want to receive weekly NBA MVP predictions during the season below.
      </p>
      <a href="{confirmation_url}" style="display:inline-block;padding:12px 18px;border-radius:9px;background:#ea580c;color:#ffffff;font-weight:700;text-decoration:none;">
        Confirm subscription
      </a>
      <p style="margin:22px 0 0;color:#94a3b8;font-size:12px;line-height:1.5;">
        If you did not request this email, you can ignore it. This link expires in 48 hours.
      </p>
    </div>
  </body>
</html>"""
  return RenderedEmail(subject, html, f'Confirm your subscription: {confirmation_url}')
