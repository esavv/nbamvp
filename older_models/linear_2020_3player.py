from sklearn import linear_model
import pandas as pd

# Extract the data into inputs (X) and output (y)
data = pd.read_csv('input_2020.csv')
X = data.drop(['Rk','Pos','Tm','Player','mvp_pts_won'], inplace=False, axis=1)
X = X.fillna(0)
y = data['mvp_pts_won']

# Create test inputs
X_test = [[34,70,70,2208,434,887,0.489,111,304,0.365,323,583,0.554,0.552,253,279,0.907,26,323,349,472,111,11,161,158,1232], #chrispaul
[27,53,29,1029,151,278,0.543,0,0,0,151,278,0.543,0.543,91,151,0.603,120,188,308,50,10,49,48,116,393], #bismack
[22,5,0,20,3,3,1,0,0,0,3,3,1,1,1,2,0.5,2,1,3,2,0,0,1,2,7]] #kostas

# Create test outputs
y_test = [26,0,0]

# Build the model
regr = linear_model.LinearRegression()
regr.fit(X, y)

# Predict
y_pred = regr.predict(X_test)

# See the results
print(y_pred)
