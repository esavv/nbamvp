import pandas as pd, os
import datetime

# This function bootstraps the week-to-week progression files assuming that these files haven't been
# created yet. It should be used sparingly, mostly as a one-off for the 2024 season (as of Nov 28, 2023)
# and retroactively for the 2022 & 2023 seasons. It will also inform how to create a more iterative
# function that will be called by predict_mvp.py.
#
# Usage:
#   > import rank_progress as rp
#   > rp.rank_progress_from_scratch(2024)
#
def rank_progress_from_scratch(year):

    # Set things up
    pred_filepath = '../data/mvp_predictions/' + str(year)
    raw_files = os.listdir(pred_filepath)
    prefix = 'predictions_' + str(year) + '_wk'

    # Get the list of prediction files 
    files = [file for file in raw_files if file.startswith(prefix)]
    files = sorted(files)

    # Initialize the progression:
    #  - Get the first file
    #  - Extract the relevant data (player, rank)
    #  - Get the week #
    #  - Update the rank column with the week #
    file = files[0]
    progression = pd.read_csv(os.path.join(pred_filepath, file))
    progression = progression[['Player','Rank']]
   
    week_no = file[len(prefix):file.find("_",len(prefix))]
    progression.rename(columns={'Rank': 'Week ' + str(int(week_no))}, inplace=True)

    # Save the first file
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M")
    prog_file = 'progression_' + str(year) + '_wk' + week_no + '_' + str(timestamp) + '.csv'
    prog_filepath = os.path.join('../data/rank_progress/' + str(year), prog_file)
    progression.to_csv(prog_filepath, index=False)

    # Loop through the remaining files to build the progression
    for file in files[1:]:
        # Extract the progression update from this week's file
        prog_update = pd.read_csv(os.path.join(pred_filepath, file))
        prog_update = prog_update[['Player','Rank']]
        week_no = file[len(prefix):file.find("_",len(prefix))]
        prog_update.rename(columns={'Rank': 'Week ' + str(int(week_no))}, inplace=True)

        # Append the progression update to the progression so far
        progression = pd.merge(progression, prog_update, on = 'Player', how = 'right')

        # Save a new file
        prog_file = 'progression_' + str(year) + '_wk' + week_no + '_' + str(timestamp) + '.csv'
        prog_filepath = os.path.join('../data/rank_progress/' + str(year), prog_file)
        progression.to_csv(prog_filepath, index=False)


# --- The following commented-out code block clears the NaN values from the
# --- progression tables. It will be re-used during visualization.

# import numpy as np

#        # Clean up the NaN values
#        # For each column
#        for col in progression.columns:
#            # Except for the first column, which has strings
#            if np.issubdtype(progression[col].dtype, np.number):
#                # Get the worst ranking
#                max_value = progression[col].max(skipna=True)
#                # Replace any NaNs with the worst ranking from that week + 1
#                progression[col].fillna(max_value + 1, inplace=True)
#                progression[col] = progression[col].astype(np.float64)