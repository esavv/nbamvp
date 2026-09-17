"""Generate browser previews of user and administrator emails without sending."""

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime
from html import escape
from itertools import product
from pathlib import Path
import json
import re

import email_preview_fixtures as fixtures
from email_rendering import (
  ADMIN_TEXT,
  RenderedEmail,
  render_error_email,
  render_postseason_email,
  render_preseason_email,
  render_subscription_confirmation_email,
  render_weekly_email,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / 'data'
PREVIEW_DIR = PROJECT_ROOT / 'static' / 'html' / 'previews'
PREDICTION_PATTERN = re.compile(
  r'^predictions_(?P<year>\d{4})_wk(?P<week>\d+)_(?P<timestamp>\d{8}_\d{4})\.csv$'
)
FETCH_STATES = ('success', 'not-found')


@dataclass(frozen=True)
class Preview:
  audience: str
  filename: str
  label: str
  email: RenderedEmail


def find_prediction(requested_season=None, requested_week=None):
  predictions = []
  prediction_root = DATA_DIR / 'mvp_predictions'
  for path in prediction_root.glob('*/predictions_*.csv'):
    match = PREDICTION_PATTERN.match(path.name)
    if not match:
      continue
    season = int(match.group('year'))
    week = int(match.group('week'))
    if requested_season is not None and season != requested_season:
      continue
    predictions.append((season, week, match.group('timestamp'), path))

  if not predictions:
    requested = f' for season {requested_season}' if requested_season else ''
    requested += f', week {requested_week}' if requested_week else ''
    raise FileNotFoundError(f'No production prediction found{requested}.')

  season = requested_season if requested_season is not None else max(item[0] for item in predictions)
  season_predictions = [item for item in predictions if item[0] == season]
  week = requested_week if requested_week is not None else max(item[1] for item in season_predictions)
  matching = [item for item in season_predictions if item[1] == week]
  if not matching:
    available_weeks = ', '.join(str(value) for value in sorted({item[1] for item in season_predictions}))
    raise ValueError(f'Week {week} was not found. Available weeks: {available_weeks}')

  _, _, timestamp, path = max(matching, key=lambda item: item[2])
  season_weeks = [item[1] for item in season_predictions]
  is_latest_week = week == max(season_weeks)
  return path, season, week, is_latest_week and generated_after_season_end(season, timestamp)


def generated_after_season_end(season, timestamp):
  season_dates_path = DATA_DIR / 'season_dates.csv'
  if not season_dates_path.exists():
    return False

  with season_dates_path.open(newline='', encoding='utf-8-sig') as handle:
    row = next((item for item in csv.DictReader(handle) if int(item['year']) == season), None)
  if row is None:
    return False

  season_end = date.fromisoformat(row['end_date'])
  generated_date = datetime.strptime(timestamp, '%Y%m%d_%H%M').date()
  return generated_date > season_end


def weekly_previews(season, week, final_week):
  prediction_path, season, week, inferred_final = find_prediction(season, week)
  is_final = inferred_final if final_week is None else final_week
  user_email = render_weekly_email(prediction_path, season, week, is_final)
  admin_email = RenderedEmail('[TEST] ' + user_email.subject, user_email.html, ADMIN_TEXT)
  return [
    Preview('user', 'weekly-prediction.html', 'Weekly prediction', user_email),
    Preview('admin', 'weekly-prediction-test.html', 'Weekly prediction test', admin_email),
  ]


def preseason_preview(season_dates_state, voting_results_state):
  suffix = f'season-dates-{season_dates_state}-voting-results-{voting_results_state}'
  rendered = render_preseason_email(
    fixtures.SEASON_YEAR,
    fixtures.SEASON_START,
    fixtures.SEASON_END,
    1,
    '2026-10-28',
    'prod',
    fixtures.season_dates_result(season_dates_state, 'preseason'),
    fixtures.voting_results_result(voting_results_state),
  )
  label = f'Preseason: season dates {season_dates_state}, voting results {voting_results_state}'
  return Preview('admin', f'preseason-{suffix}.html', label, rendered)


def postseason_preview(season_dates_state, voting_results_state):
  suffix = f'season-dates-{season_dates_state}-voting-results-{voting_results_state}'
  rendered = render_postseason_email(
    fixtures.VOTING_YEAR,
    '2026-04-12',
    'prod',
    fixtures.season_dates_result(season_dates_state, 'postseason'),
    fixtures.voting_results_result(voting_results_state),
  )
  label = f'Postseason: season dates {season_dates_state}, voting results {voting_results_state}'
  return Preview('admin', f'postseason-{suffix}.html', label, rendered)


def error_preview():
  traceback_str = (
    'Traceback (most recent call last):\n'
    '  File "src/predict_mvp.py", line 214, in main\n'
    '    predictions = model.predict(features)\n'
    'RuntimeError: Preview example prediction failure'
  )
  return Preview(
    'admin',
    'error.html',
    'Prediction error',
    render_error_email(fixtures.VOTING_YEAR, 18, traceback_str),
  )


def subscription_preview():
  rendered = render_subscription_confirmation_email(
    'http://localhost:5173/confirm?subscription_token=preview-token'
  )
  return Preview('user', 'subscription-confirmation.html', 'Subscription confirmation', rendered)


def preview_label(path):
  labels = {
    'weekly-prediction': 'Weekly prediction',
    'weekly-prediction-test': 'Weekly prediction test',
    'subscription-confirmation': 'Subscription confirmation',
    'error': 'Prediction error',
  }
  if path.stem in labels:
    return labels[path.stem]

  match = re.match(
    r'^(preseason|postseason)-season-dates-(success|not-found)-voting-results-(success|not-found)$',
    path.stem,
  )
  if match:
    email_type, season_dates_state, voting_results_state = match.groups()
    return (
      f'{email_type.title()}: season dates {season_dates_state}, '
      f'voting results {voting_results_state}'
    )
  return path.stem.replace('-', ' ').title()


def written_previews():
  previews = []
  for audience in ('user', 'admin'):
    directory = PREVIEW_DIR / audience
    if not directory.exists():
      continue
    for html_path in sorted(directory.glob('*.html')):
      text_path = html_path.with_suffix('.txt')
      text_content = text_path.read_text(encoding='utf-8') if text_path.exists() else ''
      subject_line, _, text = text_content.partition('\n\n')
      subject = subject_line.removeprefix('Subject: ').strip() or preview_label(html_path)
      previews.append(
        Preview(
          audience,
          html_path.name,
          preview_label(html_path),
          RenderedEmail(subject, html_path.read_text(encoding='utf-8'), text.strip()),
        )
      )
  return previews


def all_previews(season, week, final_week):
  previews = weekly_previews(season, week, final_week)
  previews.append(subscription_preview())
  for season_dates_state, voting_results_state in product(FETCH_STATES, repeat=2):
    previews.append(preseason_preview(season_dates_state, voting_results_state))
    previews.append(postseason_preview(season_dates_state, voting_results_state))
  previews.append(error_preview())
  return previews


def write_index(previews):
  sections = []
  preview_content = {}
  for audience in ('user', 'admin'):
    options = []
    for preview in previews:
      if preview.audience != audience:
        continue
      key = f'{audience}/{preview.filename}'
      preview_content[key] = {
        'html': preview.email.html,
        'subject': preview.email.subject,
      }
      options.append(
        '<li>'
        f'<button type="button" data-preview="{escape(key, quote=True)}">{escape(preview.label)}</button>'
        f'<small>{escape(preview.email.subject)}</small>'
        '</li>'
      )
    if options:
      sections.append(f'<section><h2>{audience.title()} emails</h2><ul>{"".join(options)}</ul></section>')

  preview_json = json.dumps(preview_content).replace('</', '<\\/')

  html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBA MVP Email Previews</title>
    <style>
      body {{ margin: 0; color: #0f172a; background: #f8fafc; font-family: Arial, sans-serif; }}
      main {{ display: grid; min-height: 100vh; grid-template-columns: minmax(280px, 380px) 1fr; }}
      nav {{ padding: 24px; border-right: 1px solid #e2e8f0; background: #ffffff; }}
      section {{ margin-top: 32px; }}
      ul {{ display: grid; gap: 10px; padding: 0; list-style: none; }}
      li {{ padding: 14px; border: 1px solid #e2e8f0; border-radius: 10px; }}
      button {{ padding: 0; border: 0; color: #c2410c; background: transparent; font: inherit; font-weight: 700; text-align: left; cursor: pointer; }}
      button[aria-current="true"] {{ color: #0f172a; }}
      small {{ display: block; margin-top: 5px; color: #64748b; }}
      .viewer {{ min-width: 0; padding: 24px; }}
      .viewer h2 {{ margin: 0 0 12px; font-size: 1rem; }}
      iframe {{ width: 100%; height: calc(100vh - 85px); border: 1px solid #e2e8f0; background: #ffffff; }}
      @media (max-width: 760px) {{
        main {{ grid-template-columns: 1fr; }}
        nav {{ border-right: 0; border-bottom: 1px solid #e2e8f0; }}
        iframe {{ height: 760px; }}
      }}
    </style>
  </head>
  <body>
    <main>
      <nav>
        <h1>NBA MVP Email Previews</h1>
        {''.join(sections)}
      </nav>
      <div class="viewer">
        <h2 id="preview-subject">Select an email</h2>
        <iframe id="preview-frame" title="Email preview"></iframe>
      </div>
    </main>
    <script>
      const previews = {preview_json};
      const frame = document.getElementById('preview-frame');
      const subject = document.getElementById('preview-subject');
      const buttons = document.querySelectorAll('[data-preview]');
      for (const button of buttons) {{
        button.addEventListener('click', () => {{
          const preview = previews[button.dataset.preview];
          frame.srcdoc = preview.html;
          subject.textContent = preview.subject;
          for (const item of buttons) item.removeAttribute('aria-current');
          button.setAttribute('aria-current', 'true');
        }});
      }}
      buttons[0]?.click();
    </script>
  </body>
</html>"""
  (PREVIEW_DIR / 'index.html').write_text(html, encoding='utf-8')


def write_previews(previews):
  for preview in previews:
    directory = PREVIEW_DIR / preview.audience
    directory.mkdir(parents=True, exist_ok=True)
    html_path = directory / preview.filename
    text_path = html_path.with_suffix('.txt')
    html_path.write_text(preview.email.html, encoding='utf-8')
    text_path.write_text(
      f'Subject: {preview.email.subject}\n\n{preview.email.text}\n',
      encoding='utf-8',
    )
    print(f'Rendered {preview.label}: {html_path}')
  write_index(written_previews())
  print(f'Preview index: {PREVIEW_DIR / "index.html"}')
  print('No email sent.')


def parse_args():
  parser = argparse.ArgumentParser(
    description='Render production email bodies without network access or delivery.'
  )
  parser.add_argument(
    'email_type',
    nargs='?',
    default='all',
    choices=('all', 'weekly', 'preseason', 'postseason', 'error', 'subscription'),
  )
  parser.add_argument('--season', type=int, help='Weekly prediction season end year.')
  parser.add_argument('--week', type=int, help='Weekly prediction week.')
  parser.add_argument(
    '--final-week',
    action=argparse.BooleanOptionalAction,
    default=None,
    help='Show or hide the final-week weekly subject. By default, infer it from available files.',
  )
  parser.add_argument('--season-dates-state', choices=FETCH_STATES, default='success')
  parser.add_argument('--voting-results-state', choices=FETCH_STATES, default='success')
  return parser.parse_args()


def main():
  args = parse_args()
  if args.email_type == 'all':
    previews = all_previews(args.season, args.week, args.final_week)
  elif args.email_type == 'weekly':
    previews = weekly_previews(args.season, args.week, args.final_week)
  elif args.email_type == 'preseason':
    previews = [preseason_preview(args.season_dates_state, args.voting_results_state)]
  elif args.email_type == 'postseason':
    previews = [postseason_preview(args.season_dates_state, args.voting_results_state)]
  elif args.email_type == 'error':
    previews = [error_preview()]
  else:
    previews = [subscription_preview()]
  write_previews(previews)


if __name__ == '__main__':
  main()
