from sklearn import linear_model
from sklearn.metrics import mean_squared_error, r2_score
import pandas as pd

# Extract the training data into inputs (X) and output (y)
# This is the 2019-2020 stats & MVP votes
train_stats = pd.read_csv('data/stats_2020.csv')
train_results = pd.read_csv('data/results_2020.csv')
train_results = train_results[['Player','Pts Won']]
train = pd.merge(train_stats, train_results, on = 'Player', how = 'left')
train = train.fillna(0)

X = train.drop(['Rk','Pos','Tm','Player','Pts Won'], inplace=False, axis=1)
y = train['Pts Won']

# Extract the test data into input (X_test) and output (y_test)
# This is the 2020-2021 stats & MVP votes
test_stats = pd.read_csv('data/stats_2021.csv')
test_results = pd.read_csv('data/results_2021.csv')
test_results = test_results[['Player','Pts Won']]
test = pd.merge(test_stats, test_results, on = 'Player', how = 'left')
test = test.fillna(0)

X_test = test.drop(['Rk','Pos','Tm','Player','Pts Won'], inplace=False, axis=1)
y_test = test['Pts Won']

# Build the model
regr = linear_model.LinearRegression()
regr.fit(X, y)

# Examine the coefficients
rounded = [round(num, 2) for num in regr.coef_]
#print(rounded)

# Predict
y_pred = regr.predict(X_test)
y_pred = pd.DataFrame(y_pred, columns = ['Predicted Votes'])
y_names = (test['Player'].to_frame())

# See the results
result = pd.concat([y_names,y_pred], axis=1)

# Show all results
#pd.set_option("display.max_rows", None, "display.max_columns", None)

# Vlookup the actual results into the predicted results
comparison = pd.merge(result, test[['Player','Pts Won']], on = 'Player', how = 'left')
comparison = comparison.fillna(0)

print(comparison.sort_values(by=['Pts Won'],ascending=False))

# The mean squared error
print("Mean squared error: %.2f" % mean_squared_error(y_test, y_pred))
# The coefficient of determination: 1 is perfect prediction
print("Coefficient of determination: %.2f" % r2_score(y_test, y_pred))

