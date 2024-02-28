from sklearn import linear_model
from sklearn.metrics import mean_squared_error, r2_score
import pandas as pd

# Extract the data into inputs (X) and output (y)
# This is the 2019-2020 stats & MVP votes
train = pd.read_csv('input_2020.csv')
X = train.drop(['Rk','Pos','Tm','Player','PTS','TRB','AST','G','ORB','DRB','GS','MP','FG','PF','mvp_pts_won'], inplace=False, axis=1)
#print(X)
X = X.fillna(0)
y = train['mvp_pts_won']

# Create test inputs
# This is the 2020-2021 stats
test = pd.read_csv('stats_2021.csv')
X_test = test.drop(['Rk','Pos','Tm','Player','PTS','TRB','AST','G','ORB','DRB','GS','MP','FG','PF'], inplace=False, axis=1)
X_test = X_test.fillna(0)

# Create test outputs
# This should be the 2020-2021 MVP votes
actual = pd.read_csv('results_2021.csv')
actual = actual[['Player','Pts Won']]
#print(actual[['Player','Pts Won']])
#y_test = y_test['Player','Pts Won']

# Build the model
regr = linear_model.LinearRegression()
regr.fit(X, y)

# Predict
y_pred = regr.predict(X_test)
y_pred = pd.DataFrame(y_pred, columns = ['Predicted Votes'])
y_names = (test['Player'].to_frame())

# See the results
result = pd.concat([y_names,y_pred], axis=1)

# Show all results
#pd.set_option("display.max_rows", None, "display.max_columns", None)

# Vlookup the actual results into the predictd results
left_join = pd.merge(result, actual, on = 'Player', how = 'left')
left_join = left_join.fillna(0)

#print(left_join.sort_values(by=['Predicted Votes'],ascending=False))
#print(left_join['Predicted Votes'])
#print(left_join['Pts Won'])

# The mean squared error
print("Mean squared error: %.2f" % mean_squared_error(left_join['Pts Won'], left_join['Predicted Votes']))
# The coefficient of determination: 1 is perfect prediction
print("Coefficient of determination: %.2f" % r2_score(left_join['Pts Won'], left_join['Predicted Votes']))
