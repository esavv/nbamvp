"""Fixed admin-email inputs captured from live source responses."""


# These values reflect one-time live fetches on 2026-09-16. Preview generation
# uses these dictionaries directly and does not contact either source.
SEASON_YEAR = 2027
SEASON_START = '2026-10-20'
SEASON_END = '2027-04-11'
VOTING_YEAR = 2026


def season_dates_result(state, phase):
  wiki_url = 'https://en.wikipedia.org/wiki/2026-27_NBA_season'
  if state == 'success':
    csv_note = (
      'No changes to upcoming season dates.'
      if phase == 'preseason'
      else 'Saved season 2027 dates to season_dates.csv.'
    )
    return {
      'status': 'success',
      'message': 'Found season dates: 2026-10-20 to 2027-04-11.',
      'wiki_url': wiki_url,
      'csv_note': csv_note,
      'start_date': SEASON_START,
      'end_date': SEASON_END,
      'season_year': SEASON_YEAR,
    }

  return {
    'status': 'page_missing',
    'message': 'Next season Wikipedia page has not been published yet.',
    'wiki_url': wiki_url,
    'csv_note': 'No CSV update performed.',
    'start_date': '',
    'end_date': '',
    'season_year': SEASON_YEAR,
  }


def voting_results_result(state):
  results_url = 'https://www.basketball-reference.com/awards/awards_2026.html#mvp'
  if state == 'success':
    return {
      'status': 'saved',
      'message': 'Fetched MVP voting results for 2026.',
      'results_url': results_url,
      'csv_note': 'Saved results_2026.csv with 8 candidates.',
      'season_year': VOTING_YEAR,
    }

  return {
    'status': 'results_unavailable',
    'message': 'MVP voting results for 2026 have not been published yet.',
    'results_url': results_url,
    'csv_note': 'No CSV update performed.',
    'season_year': VOTING_YEAR,
  }
