"""Render or safely send a weekly NBA MVP email from an existing prediction."""

import argparse
import re
from pathlib import Path

import nba_email


DATA_DIR = Path(__file__).resolve().parent.parent / 'data'
PREDICTION_PATTERN = re.compile(
  r'^predictions_(?P<year>\d{4})_wk(?P<week>\d+)_(?P<timestamp>\d{8}_\d{4})\.csv$'
)


def find_prediction(season, requested_week=None):
  prediction_dir = DATA_DIR / 'mvp_predictions' / str(season)
  if not prediction_dir.exists():
    raise FileNotFoundError(f'Prediction directory not found: {prediction_dir}')

  predictions = []
  for path in prediction_dir.glob('predictions_*.csv'):
    match = PREDICTION_PATTERN.match(path.name)
    if match and int(match.group('year')) == season:
      predictions.append((int(match.group('week')), match.group('timestamp'), path))

  if not predictions:
    raise FileNotFoundError(f'No production predictions found for the {season} season.')

  available_weeks = sorted({week for week, _, _ in predictions})
  week = requested_week if requested_week is not None else available_weeks[-1]
  matching = [item for item in predictions if item[0] == week]
  if not matching:
    choices = ', '.join(str(value) for value in available_weeks)
    raise ValueError(f'Week {week} was not found. Available weeks: {choices}')

  _, _, prediction_path = max(matching, key=lambda item: item[1])
  return prediction_path, week, week == available_weeks[-1]


def parse_args():
  parser = argparse.ArgumentParser(
    description='Preview a weekly prediction email without running the prediction pipeline.'
  )
  parser.add_argument('--season', type=int, required=True, help='Season end year, such as 2026.')
  parser.add_argument('--week', type=int, help='Prediction week. Defaults to the latest available week.')
  parser.add_argument(
    '--send',
    action='store_true',
    help='Send the rendered email only to the administrator configured in SSM.',
  )
  return parser.parse_args()


def main():
  args = parse_args()
  prediction_path, week, is_last_week = find_prediction(args.season, args.week)
  subject, html = nba_email.render_nba_email(
    prediction_path,
    args.season,
    week,
    is_last_week,
  )

  print(f'Rendered: {subject}')
  print(f'Prediction source: {prediction_path}')
  print(f'HTML preview: {nba_email.main_body_path}')

  if args.send:
    nba_email.send_test_nba_email(subject, html)
    print('Test email sent to the administrator configured in SSM Parameter Store.')
  else:
    print('No email sent. Pass --send to send only to the configured administrator.')


if __name__ == '__main__':
  main()
