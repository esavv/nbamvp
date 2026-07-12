from html import escape
from pathlib import Path
from urllib.parse import urlencode
import os

import pandas as pd
import ses_service


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_HTML_DIR = PROJECT_ROOT / 'static' / 'html'

webapp_url = os.getenv('WEBAPP_URL', 'https://nba-mvp.com')

main_template_path = STATIC_HTML_DIR / 'email_template.html'
main_body_path = STATIC_HTML_DIR / 'email_body.html'
preseason_template_path = STATIC_HTML_DIR / 'email_template_preseason.html'
postseason_template_path = STATIC_HTML_DIR / 'email_template_postseason.html'
error_template_path = STATIC_HTML_DIR / 'email_template_error.html'


def _format_number(value, decimals=1):
  if pd.isna(value):
    return '—'
  return f'{float(value):.{decimals}f}'


def _build_prediction_table(df):
  columns = [
    ('Rank', 'Rank', 'center'),
    ('Player', 'Player', 'left'),
    ('Team', 'Team', 'left'),
    ('Predicted Votes', 'Predicted Votes', 'right'),
    ('GP', 'GP', 'right'),
    ('PTS', 'PTS', 'right'),
    ('REB', 'REB', 'right'),
    ('AST', 'AST', 'right'),
    ('TS %', 'TS%', 'right'),
    ('Win %', 'Win%', 'right'),
  ]

  header_cells = ''.join(
    f'<th style="padding:10px 9px;border-bottom:1px solid #e2e8f0;'
    f'background:#f8fafc;color:#64748b;font-family:Arial,sans-serif;'
    f'font-size:10px;font-weight:700;letter-spacing:.5px;text-align:{alignment};'
    f'text-transform:uppercase;white-space:nowrap;">{label}</th>'
    for _, label, alignment in columns
  )

  body_rows = []
  for _, row in df.iterrows():
    rank = int(row['Rank'])
    rank_html = str(rank)
    if rank <= 3:
      rank_html = (
        '<span style="display:inline-block;min-width:20px;padding:3px 2px;'
        'border-radius:6px;background:#ffedd5;color:#9a3412;font-weight:700;'
        f'text-align:center;">{rank}</span>'
      )

    values = {
      'Rank': rank_html,
      'Player': escape(str(row['Player'])),
      'Team': escape(str(row['Team'])),
      'Predicted Votes': f"{int(row['Predicted Votes']):,}",
      'GP': str(int(row['GP'])),
      'PTS': _format_number(row['PTS']),
      'REB': _format_number(row['REB']),
      'AST': _format_number(row['AST']),
      'TS %': _format_number(float(row.get('TS %', row.get('TS%', 0))) * 100),
      'Win %': _format_number(float(row['Win %']) * 100),
    }

    cells = []
    for key, _, alignment in columns:
      weight = '700' if key in {'Player', 'Predicted Votes'} else '400'
      color = '#0f172a' if key in {'Player', 'Predicted Votes'} else '#475569'
      cells.append(
        f'<td style="padding:11px 9px;border-bottom:1px solid #f1f5f9;'
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


def render_nba_email(prediction_file, year, week, is_last_week, unsubscribe_url='#'):
  """Render a weekly prediction email and save a browser-previewable copy."""
  subject = f'{year} NBA MVP Predictions - Week {week}'
  if is_last_week:
    subject = f'{year} NBA MVP Predictions - Final Week (Week {week})'

  df = pd.read_csv(prediction_file)
  df = df.sort_values(by=['Predicted Votes', 'PTS'], ascending=[False, False]).head(n=15).copy()
  df['Rank'] = df['Rank'].astype(int)
  df['Predicted Votes'] = df['Predicted Votes'].astype(int)
  table_html = _build_prediction_table(df)

  season_label = f'{year - 1}–{str(year)[-2:]}'
  prediction_url = escape(f'{webapp_url}/?{urlencode({"season": year, "week": week})}', quote=True)

  with open(main_template_path, 'r', encoding='utf-8') as template_file:
    html_template = template_file.read()
  html = html_template.format(
    table_html=table_html,
    season_label=season_label,
    prediction_url=prediction_url,
    unsubscribe_url=unsubscribe_url,
  )

  with open(main_body_path, 'w', encoding='utf-8') as html_file:
    html_file.write(html)

  return subject, html


def send_nba_email(prediction_file, year, week, mode, is_last_week):
  if mode == 'prod':
    subject, html = render_nba_email(
      prediction_file,
      year,
      week,
      is_last_week,
      unsubscribe_url='{{amazonSESUnsubscribeUrl}}',
    )
    recipients = ses_service.opted_in_contacts()
    for contact in recipients:
      ses_service.send_email(
        contact['EmailAddress'],
        subject,
        html,
        'The latest NBA MVP predictions are available at https://nba-mvp.com.',
        subscription_managed=True,
        tags={'audience': 'subscriber', 'season': year, 'week': week},
      )
    print(f'  Sent weekly prediction email to {len(recipients)} confirmed subscribers.')
  else:
    subject, html = render_nba_email(prediction_file, year, week, is_last_week)
    ses_service.send_admin_email('[TEST] ' + subject, html)


def send_test_nba_email(subject, html):
  """Send an already-rendered weekly email only to the administrator."""
  ses_service.send_admin_email('[TEST] ' + subject, html)


def send_preseason_email(year, season_start, season_end, weeks_til_start, predict_start_date, mode, next_season_info):
  if weeks_til_start == 1:
    subject = str(year) + ' NBA MVP Preseason: First Prediction in ' + str(weeks_til_start) + ' Week!'
  else:
    subject = str(year) + ' NBA MVP Preseason: First Prediction in ' + str(weeks_til_start) + ' Weeks!'

  if mode == 'dev':
    subject = '[TEST] ' + subject

  with open(preseason_template_path, 'r', encoding='utf-8') as template_file:
    html_template = template_file.read()
  html = html_template.format(
    season_start=season_start,
    season_end=season_end,
    predict_start_date=predict_start_date,
    status=next_season_info.get('status', 'unknown'),
    message=next_season_info.get('message', 'No update available.'),
    wiki_url=next_season_info.get('wiki_url', ''),
    csv_note=next_season_info.get('csv_note', ''),
  )

  ses_service.send_admin_email(subject, html)


def send_postseason_email(year, season_end, mode, next_season_info):
  subject = str(year) + ' NBA MVP Postseason Notification'
  if mode == 'dev':
    subject = '[TEST] ' + subject

  with open(postseason_template_path, 'r', encoding='utf-8') as template_file:
    html_template = template_file.read()
  html = html_template.format(
    season_end=season_end,
    status=next_season_info.get('status', 'unknown'),
    message=next_season_info.get('message', 'No update available.'),
    wiki_url=next_season_info.get('wiki_url', ''),
    csv_note=next_season_info.get('csv_note', ''),
    start_date=next_season_info.get('start_date', ''),
    end_date=next_season_info.get('end_date', ''),
  )

  ses_service.send_admin_email(subject, html)


def send_error_email(year, week, traceback_str):
  print('\nSending an error email notification!\n')
  subject = 'ERROR: ' + str(year) + ' NBA MVP Predictions - Week ' + str(week)

  with open(error_template_path, 'r', encoding='utf-8') as template_file:
    html_template = template_file.read()
  html = html_template.replace('{traceback_str}', traceback_str)

  ses_service.send_admin_email(subject, html)
