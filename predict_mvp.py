# My module imports
import generate_data as gd
import preprocess_data as ppd
import mvp_model as mvp
import nba_email as em

# Standard module imports
from datetime import date
import argparse, datetime, math, os
import pandas as pd

# Set up command-line arguments & configure 'prod' and 'dev' modes.
parser = argparse.ArgumentParser(description='Toggle between prod and dev modes.')
parser.add_argument('--mode', choices=['prod', 'dev'], default='dev', help='Set the application mode (prod or dev).')
args = parser.parse_args()

if args.mode == 'prod':
  print("Running in production mode.")
  runs               = 100 
  pred_filename_stub = 'predictions_'
  is_prod_email      = True
elif args.mode == 'dev':
  print("Running in development mode.")
  runs               = 3
  pred_filename_stub = 'dev_predictions_'
  is_prod_email      = False

today = date.today()
target_year  = 2024
season_start = date(2023, 10, 24)
season_end   = date(2024,  4, 14)
delta = datetime.timedelta(weeks=1)

train_start = 2000
train_end   = 2023 #TODO Update this every season

# Are we in season? (Wait 1 week following the start of the season, and
# run a prediction in the week following the end of the season to ensure
# we have the full season's data.
if today >= (season_start + delta) and today <= (season_end + delta):
  print("We're in season! Continuing...")
else:
  print("We're not in season, or it's too early into the season, so there's no analysis to do yet.")
  print("Today is:             " + str(today))
  print("The season starts on: " + str(season_start))
  print("The season ends on:   " + str(season_end))
  exit()

# What week of the season is it?
season_days = (today - season_start).days
season_week = math.ceil(season_days / 7) - 1

# Create a string version of season_week and prepend a '0' if it's a single-digit week, to ensure
# that file ordering in /data/mvp_predictions makes sense.
week_str = str(season_week)
if season_week < 10:
  week_str = '0' + week_str

# Have we already generated predictions for this week?
#   If so, exit - don't bother predicting again and definitely don't ping the basketball reference API unnecessarily
#   Except, generate predictions if we're in dev mode (for testing)
filestring = 'predictions_' + str(target_year) + '_wk' + week_str 
for file in os.listdir('/Users/eriksavage/Documents/nbamvp/data/mvp_predictions/' + str(target_year)):
  if (file.startswith(filestring) and args.mode == 'prod'):        # confirm we're in 'prod' mode here
    print('Prediction for this week already exists! Exiting...')
    exit()

# Delete the current year's data
# TODO - Check to see if this works before the new year. IE target year is 2023, but season starts in 2022.
def nba_delete_file(path):
  if(os.path.exists(path) and os.path.isfile(path)):
    os.remove(path)
    print("file <" + path + "> deleted")
  else:
    print("file <" + path + "> not found")

stat_file      = 'data/stats/stats_' + str(target_year) + '.csv'
pg_file        = 'data/per_game_stats/pg_stats_' + str(target_year) + '.csv'
adv_file       = 'data/adv_stats/adv_stats_' + str(target_year) + '.csv'
standings_file = 'data/standings/standings_' + str(target_year) + '.csv'

print("Removing stale data from current season...")
nba_delete_file(stat_file)
nba_delete_file(pg_file)
nba_delete_file(adv_file)
nba_delete_file(standings_file)

# Regenerate the current year's data
print("Generating fresh data from current season...")
gd.generate_data(target_year)

# Predict
prediction = mvp.rforest_predict_mvp(train_start, train_end, target_year, runs)
#prediction = mvp.neural_net_predict_mvp(train_start, train_end, target_year, 750, 'adam', 10, 10, 1)
stats = ppd.preprocess_season_stats(target_year)

# Display all rows 
pd.set_option("display.max_rows", None, "display.max_columns", None)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

# Vlookup the actual stats into the predicted results
results = pd.merge(prediction, stats[['name','games_played_actual','points_y','rebounds_y','assists_y',
                                      'true_shooting_percentage','Win Pct','team']], on = 'name', how = 'left')
# Lots of formatting
results = results.fillna(0)
results = results.rename(columns={'name': 'Player', 'games_played_actual': 'GP', 'points_y': 'PTS', 'rebounds_y':'REB', 'assists_y':'AST', 'true_shooting_percentage':'TS %', 'Win Pct':'Win %', 'team':'Team'})
results = results.round({'Predicted Votes': 0, 'PTS': 1, 'REB': 1, 'AST': 1, 'TS %': 3, 'Win %': 3})
results = results.sort_values(by = ['Predicted Votes','PTS'], ascending = (False,False))
results['Rank'] = results['Predicted Votes'].rank(method = 'min', ascending = False) 
results = results[['Rank','Player','Team','Predicted Votes','GP','PTS','REB','AST','TS %','Win %']]
# Format the team names from "Team.DALLAS_MAVERICKS" to "Dallas Mavericks"
results['Team'] = results['Team'].str.replace('Team.', '', regex=False)
results['Team'] = results['Team'].str.replace('_',' ')
results['Team'] = results['Team'].str.lower()
results['Team'] = results['Team'].str.title()
results['Team'] = results['Team'].str.replace('76Ers','76ers')

# Save the predictions in a /data/mvp_predictions sub-directory
# Some pre-work.
now = datetime.datetime.now()
timestamp = now.strftime("%Y%m%d_%H%M") 
filepath = 'data/mvp_predictions/'
directory = str(target_year)
# Check if the sub-directory (for the current season) already exists, and if not, create it.
if not os.path.exists(filepath + directory):
  os.makedirs(filepath + directory)
  print(f"Directory '{filepath + directory}' created.")
# Save the predictions.
pred_file = filepath + directory + '/' + pred_filename_stub + str(target_year) + '_wk' + week_str + '_' + str(timestamp) + '.csv'
results.to_csv(pred_file, index=False)

# Email the results
em.send_nba_email(pred_file, target_year, season_week, is_prod_email)
