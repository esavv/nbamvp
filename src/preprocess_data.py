import pandas as pd
import os

# With the BR web scraper API, we no longer need the team mapping to map stats to standings
#team_mapping = pd.read_csv('data/team_mapping.csv')

current_dir = os.getcwd()
parent_dir = os.path.dirname(current_dir)

def preprocess_season_stats(year):
  stats_path     = os.path.join(parent_dir, 'data/stats/stats_' + str(year) + '.csv')
  adv_path       = os.path.join(parent_dir, 'data/adv_stats/adv_stats_' + str(year) + '.csv')
  pg_stats_path  = os.path.join(parent_dir, 'data/per_game_stats/pg_stats_' + str(year) + '.csv')
  standings_path = os.path.join(parent_dir, 'data/standings/standings_' + str(year) + '.csv')

  # Read standard stats
  stats = pd.read_csv(stats_path)

  # Read advanced stats
  adv = pd.read_csv(adv_path)

  stats = pd.merge(stats, adv, on = 'name', how = 'left')

  # Read per game stats
  pg_stats = pd.read_csv(pg_stats_path)

  stats = pd.merge(stats, pg_stats, on = 'name', how = 'left')

  # Read team standings 
  standings = pd.read_csv(standings_path)
  standings = standings[['team','Win Pct']]

  stats = pd.merge(stats, standings, on = 'team', how = 'left')

  stats = stats.fillna(0)

  # ABANDONED - Convert raw inputs into ranked inputs
  #val = stats.drop(['name','positions','team'], inplace=False, axis=1)
  #val_norm = (val-val.min())/(val.max()-val.min())
  #rank_stats = stats[['name','positions','team']].join(val_norm)

  # Scale stats to adjust for midseason / shortened-season predictions
  max_possible_games = 82
  games_into_season = stats['games_played'].max()
  actual_games_played = stats['games_played']
  scale_stats = stats[['games_played','games_started','minutes_played','made_field_goals','attempted_field_goals',
        'made_three_point_field_goals','attempted_three_point_field_goals','made_free_throws','attempted_free_throws',
        'offensive_rebounds','defensive_rebounds','assists_x','steals','blocks','turnovers','personal_fouls','points_x',
        'rebounds_x','win_shares']]
  stats.drop(['games_played','games_started','minutes_played','made_field_goals','attempted_field_goals',
        'made_three_point_field_goals','attempted_three_point_field_goals','made_free_throws','attempted_free_throws',
        'offensive_rebounds','defensive_rebounds','assists_x','steals','blocks','turnovers','personal_fouls','points_x',
        'rebounds_x','win_shares'], inplace=True, axis=1)
  scale_stats = scale_stats * (max_possible_games / games_into_season)
  stats = stats.join(scale_stats)
  stats['games_played_actual'] = actual_games_played

  return stats

def preprocess_season_stats_and_results(year):
  stats = preprocess_season_stats(year)  

  # Read the MVP voting results
  result_path = os.path.join(parent_dir, 'data/mvp_results/results_' + str(year) + '.csv')
  results = pd.read_csv(result_path)
  
  # Split "Player" field into "name" and "stub"
  # This if/else statement here was added on 10/28/2022 to accommodate
  #   a change in the results csv format that began in the 2022-23 season.
  # As of 10/31/2023, it appears this format change is persisting into
  #   the 2023-24 season, so I updated the conditional to split the
  #   Player column for all seasons before 2022.
  if year <= 2021:
    results[['name','stub']] = results.Player.str.split('\\',expand=True)
  else:
    results['name'] = results.Player


  results = results.rename(columns={'Pts Won': 'Actual Votes'})
  results = results[['name','Actual Votes']]

  season = pd.merge(stats, results, on = 'name', how = 'left')
  season = season.fillna(0)
  return season
