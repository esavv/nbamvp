"""Render and deliver NBA MVP emails."""

import email_rendering
import ses_service


def send_nba_email(prediction_file, year, week, mode, is_last_week):
  if mode == 'prod':
    rendered = email_rendering.render_weekly_email(
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
        rendered.subject,
        rendered.html,
        rendered.text,
        subscription_managed=True,
        tags={'audience': 'subscriber', 'season': year, 'week': week},
      )
    print(f'  Sent weekly prediction email to {len(recipients)} confirmed subscribers.')
  else:
    rendered = email_rendering.render_weekly_email(prediction_file, year, week, is_last_week)
    ses_service.send_admin_email('[TEST] ' + rendered.subject, rendered.html)


def send_preseason_email(
  year,
  season_start,
  season_end,
  weeks_til_start,
  predict_start_date,
  mode,
  next_season_info,
  voting_results_info,
):
  rendered = email_rendering.render_preseason_email(
    year,
    season_start,
    season_end,
    weeks_til_start,
    predict_start_date,
    mode,
    next_season_info,
    voting_results_info,
  )
  ses_service.send_admin_email(rendered.subject, rendered.html)


def send_postseason_email(year, season_end, mode, next_season_info, voting_results_info):
  rendered = email_rendering.render_postseason_email(
    year,
    season_end,
    mode,
    next_season_info,
    voting_results_info,
  )
  ses_service.send_admin_email(rendered.subject, rendered.html)


def send_error_email(year, week, traceback_str):
  print('\nSending an error email notification!\n')
  rendered = email_rendering.render_error_email(year, week, traceback_str)
  ses_service.send_admin_email(rendered.subject, rendered.html)
