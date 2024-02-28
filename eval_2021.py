import pandas as pd
import preprocess_data as ppd
import mvp_model as mvp
import sklearn.metrics as skm

# Select the regressor to predict
result = mvp.rforest_predict_mvp(2000, 2020, 2021, 100)
#result = mvp.rforest_predict_mvp(2000, 2020, 2021, 3)         # for testing
#result = mvp.neural_net_predict_mvp(2000, 2020, 2021, 750, 'adam', 10, 10, 1)

y_pred = result['Predicted Votes']
test21 = ppd.preprocess_season_stats_and_results(2021)
y_test = test21['Actual Votes']
  
# Display all rows 
pd.set_option("display.max_rows", None, "display.max_columns", None)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

# Vlookup the actual results into the predicted results
comparison = pd.merge(result, test21[['name','Actual Votes','games_played_actual','points_y','rebounds_y','assists_y',
                                      'true_shooting_percentage','Win Pct']], on = 'name', how = 'left')
comparison = comparison.fillna(0)
comparison = comparison.rename(columns={'name': 'Player', 'games_played_actual': 'GP', 'points_y': 'PTS', 'rebounds_y':'REB', 'assists_y':'AST', 'true_shooting_percentage':'TS%', 'Win Pct':'Win %'})
comparison = comparison.round({'Predicted Votes': 0, 'Actual Votes': 0, 'PTS': 1, 'REB': 1, 'AST': 1, 'TS%': 3, 'Win %': 3})

#print(comparison.sort_values(by = ['Actual Votes','Predicted Votes','PTS'], ascending = (False,False,False)))

# The mean squared error
print("Mean squared error: %.2f" % skm.mean_squared_error(y_test, y_pred))
# The coefficient of determination: 1 is perfect prediction
print("Coefficient of determination: %.2f" % skm.r2_score(y_test, y_pred))
