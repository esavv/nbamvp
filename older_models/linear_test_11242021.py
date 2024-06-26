from sklearn import datasets, linear_model
from sklearn.metrics import mean_squared_error, r2_score

# Load the data 
#diabetes_X, diabetes_y = datasets.load_diabetes(return_X_y=True)

# Split the data into training/testing sets
#diabetes_X_train = diabetes_X[:-20]
#diabetes_X_test = diabetes_X[-20:]

# Split the targets into training/testing sets
#diabetes_y_train = diabetes_y[:-20]
#diabetes_y_test = diabetes_y[-20:]

# Create linear regression object
#regr = linear_model.LinearRegression()

# Train the model using the training sets
#regr.fit(diabetes_X_train, diabetes_y_train)

# Make predictions using the testing set
#diabetes_y_pred = regr.predict(diabetes_X_test)

# The coefficients
#print("Coefficients: \n", regr.coef_)
# The mean squared error
#print("Mean squared error: %.2f" % mean_squared_error(diabetes_y_test, diabetes_y_pred))
# The coefficient of determination: 1 is perfect prediction
#print("Coefficient of determination: %.2f" % r2_score(diabetes_y_test, diabetes_y_pred))

X = [[ 1,  2,  3],  # 2 samples, 3 features
     [11, 12, 13]]

X_test = [[ 0,  1,  2.5],
          [10, 14, 13.5]]

y = [0, 1]

regr = linear_model.LinearRegression()

regr.fit(X, y)

y_pred = regr.predict(X_test)

y_pred

