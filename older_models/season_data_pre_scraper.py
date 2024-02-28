import pandas as pd

team_mapping = pd.read_csv('data/team_mapping.csv')

def prep_season_data(year):
  # Read standard stats
  stats = pd.read_csv('data/stats_' + str(year) + '.csv')

  # Read advanced stats
  adv = pd.read_csv('data/adv_stats_' + str(year) + '.csv')
  adv.drop(['Rk','Pos','Age','Tm','G','MP','PER','3PAr','FTr','ORB%','DRB%','TRB%','AST%','STL%','BLK%',
            'TOV%','USG%','OWS','DWS','WS/48','OBPM','DBPM','Unnamed: 19','Unnamed: 24'], inplace=True, axis=1)

  stats = pd.merge(stats, adv, on = 'Player', how = 'left')

  # Read per game stats
  pg_stats = pd.read_csv('data/pg_stats_' + str(year) + '.csv')
  pg_stats = pg_stats[['Player','PTS','TRB','AST']]

  stats = pd.merge(stats, pg_stats, on = 'Player', how = 'left')

  # Read team standings and calculate win percentage
  standings = pd.read_csv('data/standings_' + str(year) + '.csv')
  standings[['Wins','Losses']] = standings.Overall.str.split("-",expand=True)
  standings['Win Pct'] = standings['Wins'].astype(int) / (standings['Wins'].astype(int) + standings['Losses'].astype(int))
  standings = standings[['Team','Win Pct']]

  stats = pd.merge(stats, team_mapping, on = 'Tm', how = 'left')
  stats = pd.merge(stats, standings, on = 'Team', how = 'left')

  results = pd.read_csv('data/results_' + str(year) + '.csv')
  results = results[['Player','Pts Won']]

  season = pd.merge(stats, results, on = 'Player', how = 'left')
  season = season.fillna(0)
  return season
