from basketball_reference_web_scraper import client as br
import pandas as pd
import os

current_dir = os.getcwd()
parent_dir = os.path.dirname(current_dir)

# Get all player "slugs" according to Basketball Reference taxonomy
# For example, Jimmy Butler's slug is "butleji01"
# Save to ~/data/player_slugs.csv
#
# TODO 2024-10-24: This assumes the function is called interactively from the parent project directory... refactor this!
def pull_slugs(year):
  stats_dict = br.players_season_totals(season_end_year=year)
  stats_df = pd.DataFrame.from_dict(stats_dict)
  slugs = stats_df['slug']
  filename = os.path.join(parent_dir, 'data/player_slugs.csv')
  slugs.to_csv(filename, index=False, header=None)

def generate_data(year):
  # Check what files need to be created
  #TODO

  # Get the various datasets
  stats_dict = br.players_season_totals(season_end_year=year)
  adv_dict = br.players_advanced_season_totals(season_end_year=year)
  standings_dict = br.standings(season_end_year=year)

  # Convert them to dataframes
  stats_df = pd.DataFrame.from_dict(stats_dict) 
  adv_df = pd.DataFrame.from_dict(adv_dict)
  standings_df = pd.DataFrame.from_dict(standings_dict)
  
  # Merge rows for traded players
  stats_df = stats_df.groupby(['slug','name'], as_index=False).agg({'positions':'first', 'team':'last', 'age':'min',
           'games_played':'sum', 'games_started':'sum', 'minutes_played':'sum', 'made_field_goals':'sum',
           'attempted_field_goals':'sum', 'made_three_point_field_goals':'sum', 'attempted_three_point_field_goals':'sum',
           'made_free_throws':'sum', 'attempted_free_throws':'sum', 'offensive_rebounds':'sum', 'defensive_rebounds':'sum',
           'assists':'sum', 'steals':'sum', 'blocks':'sum', 'turnovers':'sum', 'personal_fouls':'sum', 'points':'sum'})
  
  adv_df.drop(['positions','age','team','minutes_played','player_efficiency_rating','three_point_attempt_rate',
              'free_throw_attempt_rate','offensive_rebound_percentage','defensive_rebound_percentage',
              'total_rebound_percentage','assist_percentage','steal_percentage','block_percentage','turnover_percentage',
              'usage_percentage','offensive_win_shares','defensive_win_shares','win_shares_per_48_minutes',
              'offensive_box_plus_minus','defensive_box_plus_minus','is_combined_totals'], inplace=True, axis=1)
   
  # To merge advanced stats, I'm going to need a weighted average of:
  # - true_shooting_percentage
  # - box_plus_minus
  # - value_over_replacement_player 
  # 
  # To do that, I need to multiple each duplicate row stat for those 3 stats by games played, on merge sum the multiplied numbers, and then divide by total games played
  adv_df['true_shooting_percentage'] = adv_df['true_shooting_percentage'] * adv_df['games_played']
  adv_df['box_plus_minus'] = adv_df['box_plus_minus'] * adv_df['games_played']
  adv_df['value_over_replacement_player'] = adv_df['value_over_replacement_player'] * adv_df['games_played']
  
  adv_df = adv_df.groupby(['slug','name'], as_index=False).agg({'games_played':'sum', 'true_shooting_percentage':'sum',
                  'box_plus_minus':'sum', 'value_over_replacement_player':'sum', 'win_shares':'sum'})
  
  adv_df['true_shooting_percentage'] = adv_df['true_shooting_percentage'] / adv_df['games_played']
  adv_df['box_plus_minus'] = adv_df['box_plus_minus'] / adv_df['games_played']
  adv_df['value_over_replacement_player'] = adv_df['value_over_replacement_player'] / adv_df['games_played']
  
  # Display all rows 
  #pd.set_option("display.max_rows", None, "display.max_columns", None)
  #pd.set_option('display.max_columns', 500)
  #pd.set_option('display.width', 1000)
  
  # Generate missing standard stats
  stats_df['FG%'] = stats_df['made_field_goals'].astype(int) / stats_df['attempted_field_goals'].astype(int)
  stats_df['3P%'] = stats_df['made_three_point_field_goals'].astype(int) / stats_df['attempted_three_point_field_goals'].astype(int) 
  stats_df['2P'] = stats_df['made_field_goals'].astype(int) - stats_df['made_three_point_field_goals'].astype(int) 
  stats_df['2PA'] = stats_df['attempted_field_goals'].astype(int) - stats_df['attempted_three_point_field_goals'].astype(int) 
  stats_df['2P%'] = stats_df['2P'].astype(int) / stats_df['2PA'].astype(int)
  stats_df['FT%'] = stats_df['made_free_throws'].astype(int) / stats_df['attempted_free_throws'].astype(int) 
  stats_df['rebounds'] = stats_df['offensive_rebounds'].astype(int) + stats_df['defensive_rebounds'].astype(int) 

  # Generate per game stats
  name = stats_df[['slug','name']]
  pts_avg = pd.Series(stats_df['points'].astype(int) / stats_df['games_played'].astype(int), name='points')
  reb_avg = pd.Series(stats_df['rebounds'].astype(int) / stats_df['games_played'].astype(int), name='rebounds')
  ast_avg = pd.Series(stats_df['assists'].astype(int) / stats_df['games_played'].astype(int), name='assists')
  pg_stats_df = pd.concat([name, pts_avg, reb_avg, ast_avg], axis=1) 

  # Generate standings win percentage
  standings_df['Win Pct'] = standings_df['wins'].astype(int) / (standings_df['wins'].astype(int) + standings_df['losses'].astype(int))

  # Drop some columns before saving
  stats_df.drop(['slug'], inplace=True, axis=1)
  adv_df.drop(['slug','games_played'], inplace=True, axis=1)
  pg_stats_df.drop(['slug'], inplace=True, axis=1)

  # Save the data as CSVs
  stats_path     = os.path.join(parent_dir, 'data/stats/stats_' + str(year) + '.csv')
  adv_path       = os.path.join(parent_dir, 'data/adv_stats/adv_stats_' + str(year) + '.csv')
  pg_stats_path  = os.path.join(parent_dir, 'data/per_game_stats/pg_stats_' + str(year) + '.csv')
  standings_path = os.path.join(parent_dir, 'data/standings/standings_' + str(year) + '.csv')

  stats_df.to_csv(stats_path, index=False)
  adv_df.to_csv(adv_path, index=False)
  pg_stats_df.to_csv(pg_stats_path, index=False)
  standings_df.to_csv(standings_path, index=False)
