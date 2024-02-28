from sklearn.ensemble import RandomForestRegressor 
#from sklearn import preprocessing
from sklearn.metrics import mean_squared_error, r2_score
import pandas as pd
import season_data as sd

#### Extract the training data into inputs (X) and output (y)

## Extract the 2019 and 2020 stats & MVP votes
train19 = sd.prep_season_data(2019)
train20 = sd.prep_season_data(2020)

## Combine the 2019 & 2020 seasons
train = train19.append(train20)

## Prep the X & y inputs 

X = train.drop(['Rk','Pos','Tm','Player','Pts Won','Team'], inplace=False, axis=1)
#scaler = preprocessing.StandardScaler().fit(X)
#X_scaled = scaler.transform(X)
y = train['Pts Won']


##### Extract the test data into input (X_test) and output (y_test)

## Extract the 2021 stats & MVP votes 
test21 = sd.prep_season_data(2021)

X_test = test21.drop(['Rk','Pos','Tm','Player','Pts Won','Team'], inplace=False, axis=1)
#scaler = preprocessing.StandardScaler().fit(X_test)
#X_test_scaled = scaler.transform(X_test)
y_test = test21['Pts Won']

# Build the model
model = RandomForestRegressor(n_estimators=10, max_features=6)
model.fit(X, y)
#model.fit(X_scaled, y)

# Predict
y_pred = model.predict(X_test)
#y_pred = model.predict(X_test_scaled)
y_pred = pd.DataFrame(y_pred, columns = ['Predicted Votes'])
y_names = (test21['Player'].to_frame())

# Prep the results
result = pd.concat([y_names,y_pred], axis=1)

# Display all rows 
#pd.set_option("display.max_rows", None, "display.max_columns", None)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

# Vlookup the actual results into the predicted results
comparison = pd.merge(result, test21[['Player','Pts Won','G','PTS_y','TRB_y','AST_y','TS%','Win Pct']], on = 'Player', how = 'left')
comparison = comparison.fillna(0)
comparison = comparison.rename(columns={"Pts Won": "Actual Votes"})

print(comparison.sort_values(by = ['Actual Votes','Predicted Votes'], ascending = (False,False)))

# The mean squared error
print("Mean squared error: %.2f" % mean_squared_error(y_test, y_pred))
# The coefficient of determination: 1 is perfect prediction
print("Coefficient of determination: %.2f" % r2_score(y_test, y_pred))
