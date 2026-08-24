import pandas as pd
import joblib

from config import SCALER_PATH, FINAL_MODEL_PATH

# Load scaler and model
scaler = joblib.load(SCALER_PATH)
model = joblib.load(FINAL_MODEL_PATH)


def predict_heart_disease(patient_data):
    """
    Predict heart disease for one patient.

    Parameters
    ----------
    patient_data : list
        [
            age,
            sex,
            chest pain type,
            resting bp s,
            cholesterol,
            fasting blood sugar,
            resting ecg,
            max heart rate,
            exercise angina,
            oldpeak,
            ST slope
        ]

    Returns
    -------
    prediction : int
    probability : float
    """

    columns = [
        "age",
        "sex",
        "chest pain type",
        "resting bp s",
        "cholesterol",
        "fasting blood sugar",
        "resting ecg",
        "max heart rate",
        "exercise angina",
        "oldpeak",
        "ST slope"
    ]

    # Convert list into DataFrame
    patient = pd.DataFrame([patient_data], columns=columns)

    # Scale features
    patient_scaled = scaler.transform(patient)

    # Prediction
    prediction = model.predict(patient_scaled)[0]

    # Probability
    probability = model.predict_proba(patient_scaled)[0][1]

    return prediction, probability