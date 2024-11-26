# My module imports
import generate_data as gd
import preprocess_data as ppd
import mvp_model as mvp
import nba_email as em

# Standard module imports
from datetime import date, datetime, timedelta
import argparse, math, os, pytz, traceback
import pandas as pd

def main():
  # Get the development mode from an environment variable
  mode = os.getenv('MODE', 'dev') # default to dev mode

  est = pytz.timezone('US/Eastern')
  now = datetime.now(est)
  current_time = now.strftime('%Y-%m-%d %H:%M:%S %Z')

  if mode == 'prod':
    print(current_time + ": Running in production mode.\n")
    runs               = 100 
    pred_filename_stub = 'predictions_'
    is_prod_email      = True
  elif mode == 'dev':
    print(current_time + ": Running in development mode.\n")
    runs               = 3
    pred_filename_stub = 'dev_predictions_'
    is_prod_email      = False

  today = date.today()
  season_start = date(2024, 10, 22)
  season_end   = date(2025,  4, 13)
  target_year  = season_end.year
  delta = timedelta(weeks=1)

  train_start = 2000
  train_end   = target_year-1 #TODO Ensure training data actually goes up to this season

  # What week of the season is it? (this is useful for preseason notifications,
  # so we do this before checking if we're in season)
  season_days = (today - season_start).days
  season_week = math.ceil(season_days / 7) - 1
  is_last_week = today > season_end

  # Are we in season? (Wait 1 week following the start of the season, and
  # run a prediction in the week following the end of the season to ensure
  # we have the full season's data.
  before_season = today < (season_start + delta)
  after_season = today > (season_end + delta)

  if before_season:
    print("The season either hasn't started yet, or it's too early, so there's no analysis to do.")
    print("Today is:             " + str(today))
    print("The season starts on: " + str(season_start))
    print("The season ends on:   " + str(season_end) + "\n")

    # Figure out how many weeks until the first MVP prediction
    weeks_til_start = 1 - season_week
    if weeks_til_start == 1:
      print("The season is starting in about " + str(weeks_til_start) + " week!\n")
    else:
      print("The season is starting in about " + str(weeks_til_start) + " weeks!\n")

    # If we're in prod, find out when the 1st real prediction will happen & notify if we're close
    if mode == 'prod':
      # Figure out when we'll perform the first prediction
      predict_start_date = today + datetime.timedelta(weeks=weeks_til_start)
      print("The first prediction will be sent on this date: " + str(predict_start_date))

      # Notify the admin that we're getting close to the season
      if weeks_til_start <= 3:
        # send email
        em.send_preseason_email(target_year, season_start, season_end, weeks_til_start, predict_start_date)
    
    exit()
  elif after_season:
    print("The season either ended or is about to, so there's no analysis to do.")
    print("Today is:             " + str(today))
    print("The season starts on: " + str(season_start))
    print("The season ends on:   " + str(season_end) + '\n')
    exit()
  else:
    print("We're in season! Continuing...")

  # Create a string version of season_week and prepend a '0' if it's a single-digit week, to ensure
  # that file ordering in /data/mvp_predictions makes sense.
  week_str = str(season_week)
  if season_week < 10:
    week_str = '0' + week_str

  # Have we already generated predictions for this week?
  #   If so, exit - don't bother predicting again and definitely don't ping the basketball reference API unnecessarily
  #   Except, generate predictions if we're in dev mode (for testing)
  prediction_prefix = 'predictions_' + str(target_year) + '_wk' + week_str 
  prediction_path = '../data/mvp_predictions/' + str(target_year)
  if args.mode == 'prod':                     # confirm we're in 'prod' mode here
    for file in os.listdir(prediction_path):
      if file.startswith(prediction_prefix):
        print('Prediction for this week already exists! Exiting...')
        exit()

  # Delete the current year's data
  # TODO - Check to see if this works before the new year. IE target year is 2023, but season starts in 2022.
  def nba_delete_file(path):
    if(os.path.exists(path) and os.path.isfile(path)):
      os.remove(path)
      print("    file <" + path + "> deleted")
    else:
      print("    file <" + path + "> not found")

  stat_file      = '../data/stats/stats_' + str(target_year) + '.csv'
  pg_file        = '../data/per_game_stats/pg_stats_' + str(target_year) + '.csv'
  adv_file       = '../data/adv_stats/adv_stats_' + str(target_year) + '.csv'
  standings_file = '../data/standings/standings_' + str(target_year) + '.csv'

  print("Removing stale data from current season...")
  nba_delete_file(stat_file)
  nba_delete_file(pg_file)
  nba_delete_file(adv_file)
  nba_delete_file(standings_file)

  # Regenerate the current year's data
  print("Generating fresh data from current season...")
  try:
    gd.generate_data(target_year)
  except Exception as e:
    # Print a clear error message and exit gracefully
    print(f"ERROR: Data generation failed.")
    traceback_str = traceback.format_exc()
    print(traceback_str)
    em.send_error_email(target_year, season_week, traceback_str)
    exit()

  # Predict
  print("Making some predictions...")
  prediction = mvp.rforest_predict_mvp(train_start, train_end, target_year, runs)
  #prediction = mvp.neural_net_predict_mvp(train_start, train_end, target_year, 750, 'adam', 10, 10, 1)
  stats = ppd.preprocess_season_stats(target_year)

  print("Cleaning things up...")
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
  print("Saving the results...")
  timestamp = now.strftime("%Y%m%d_%H%M") 
  filepath = '../data/mvp_predictions/' + str(target_year)
  # Check if the sub-directory (for the current season) already exists, and if not, create it.
  if not os.path.exists(filepath):
    os.makedirs(filepath)
    print(f"Directory '{filepath}' created.")
  # Save the predictions.
  pred_file = filepath + '/' + pred_filename_stub + str(target_year) + '_wk' + week_str + '_' + str(timestamp) + '.csv'
  results.to_csv(pred_file, index=False)

  # Email the results
  print("Emailing the results...")
  em.send_nba_email(pred_file, target_year, season_week, is_prod_email, is_last_week)

# Set up command-line arguments & configure 'prod' and 'dev' modes (via an environment variable).
parser = argparse.ArgumentParser(description='Toggle between prod and dev modes.')
parser.add_argument('--mode', choices=['prod', 'dev'], default='dev', help='Set the application mode (prod or dev).')
args = parser.parse_args()
os.environ['MODE'] = args.mode

main()