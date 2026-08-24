from src.preprocessing import preprocess_data

(
    X_train,
    X_test,
    X_train_scaled,
    X_test_scaled,
    y_train,
    y_test,
    scaler
) = preprocess_data()

print("Preprocessing Successful")

print(X_train.shape)
print(X_test.shape)