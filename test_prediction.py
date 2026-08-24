from src.prediction import predict_heart_disease

# Sample patient from your dataset
patient = [
    40,   # age
    1,    # sex
    2,    # chest pain type
    140,  # resting bp s
    289,  # cholesterol
    0,    # fasting blood sugar
    0,    # resting ecg
    172,  # max heart rate
    0,    # exercise angina
    0.0,  # oldpeak
    1     # ST slope
]

prediction, probability = predict_heart_disease(patient)

print("=" * 50)
print("Heart Disease Prediction")
print("=" * 50)

if prediction == 1:
    print("Prediction : Heart Disease Detected")
else:
    print("Prediction : No Heart Disease")

print(f"Risk Probability : {probability:.2%}")