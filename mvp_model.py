from sklearn import preprocessing
from sklearn.ensemble import RandomForestRegressor 
from sklearn.neural_network import MLPRegressor
import pandas as pd
import preprocess_data as ppd

def prep_the_data(train_start, train_end, target_year, to_scale):
  #### Extract the training data into inputs (X) and output (y)
  ## Extract the 2000-2020 stats & MVP votes
  train = pd.DataFrame()
  for year in range(train_end - train_start + 1):
    train_year = ppd.preprocess_season_stats_and_results(train_start + year)
    train = train.append(train_year)

  ## Prep the X & y inputs 
  X = train.drop(['positions','team','name','Actual Votes','games_played_actual'], inplace=False, axis=1)
  if (to_scale):
    scaler = preprocessing.StandardScaler().fit(X)
    X = scaler.transform(X)
  y = train['Actual Votes']

  ##### Extract the test data into input (X_test) and output (y_test)
  ## Extract the target year stats
  test = ppd.preprocess_season_stats(target_year)

  X_test = test.drop(['positions','team','name','games_played_actual'], inplace=False, axis=1)
  if (to_scale):
    scaler = preprocessing.StandardScaler().fit(X_test)
    X_test = scaler.transform(X_test)

  return train, X, y, test, X_test

# Predicts the NBA MVP
# Input: A range of training years, a target prediction year, and the # of times to run the model
# Output: A DataFrame containing predictions for all players in the target year 
def rforest_predict_mvp(train_start, train_end, target_year, runs):
  train, X, y, test, X_test = prep_the_data(train_start, train_end, target_year, False)

  # Build the model
  model = RandomForestRegressor(n_estimators=10, max_features=6)
  model.fit(X, y)

  # Predict once
  y_preds = model.predict(X_test)
  y_preds = pd.DataFrame(y_preds, columns = ['Predicted Votes'])

  # Predict <runs-1> more times
  for index in range(runs-1):
    model = RandomForestRegressor(n_estimators=10, max_features=6)
    model.fit(X, y)
  
    # Predict
    next_pred = model.predict(X_test)
    next_pred = pd.DataFrame(next_pred, columns = ['Predicted Votes'])
    y_preds = pd.concat([y_preds, next_pred], axis=1)

  # Get the average of the <runs> predictions
  y_pred = y_preds.mean(axis=1)
  y_pred = pd.DataFrame(y_pred, columns = ['Predicted Votes'])

  y_names = (test['name'].to_frame())

  # Prep the results
  result = pd.concat([y_names,y_pred], axis=1)

  return result


def neural_net_predict_mvp(train_start, train_end, target_year, iterations, algo, alf, hidone, hidtwo):
  train, X, y, test, X_test = prep_the_data(train_start, train_end, target_year, True)

  # Build the model
  model = MLPRegressor(solver=algo, alpha=alf, hidden_layer_sizes=(hidone, hidtwo), random_state=1, max_iter=iterations)
  model.fit(X, y)

  # Predict
  y_pred = model.predict(X_test)
  y_pred = pd.DataFrame(y_pred, columns = ['Predicted Votes'])
  y_names = (test['name'].to_frame())

  # Prep the results
  result = pd.concat([y_names,y_pred], axis=1)

  return result
