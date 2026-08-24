from database import get_db_connection
from src.prediction import predict_heart_disease


FEATURE_COLUMNS = [
    "age",
    "sex",
    "chest_pain_type",
    "resting_bp",
    "cholesterol",
    "fasting_blood_sugar",
    "resting_ecg",
    "max_heart_rate",
    "exercise_angina",
    "oldpeak",
    "st_slope"
]


def get_extraction(extraction_id):
    """
    Retrieve a validated extraction record from MySQL.
    """

    connection = get_db_connection()

    if connection is None:
        return None

    cursor = connection.cursor(dictionary=True)

    try:
        query = """
        SELECT
            extraction_id,
            report_id,
            age,
            sex,
            chest_pain_type,
            resting_bp,
            cholesterol,
            fasting_blood_sugar,
            resting_ecg,
            max_heart_rate,
            exercise_angina,
            oldpeak,
            st_slope,
            validation_status
        FROM extracted_features
        WHERE extraction_id = %s
        """

        cursor.execute(query, (extraction_id,))

        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()


def save_prediction(
    patient_id,
    extraction_id,
    prediction,
    probability
):
    """
    Save ML prediction into predictions table.
    """

    if probability < 0.40:
        risk_level = "LOW"
    elif probability < 0.70:
        risk_level = "MODERATE"
    else:
        risk_level = "HIGH"

    connection = get_db_connection()

    if connection is None:
        return False

    cursor = connection.cursor()

    try:

        query = """
        INSERT INTO predictions
        (
            patient_id,
            extraction_id,
            model_name,
            model_version,
            prediction_result,
            risk_probability,
            risk_level,
            prediction_status
        )
        VALUES
        (
            %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        """

        values = (
            patient_id,
            extraction_id,
            "Hybrid KNN + Random Forest",
            "1.0",
            int(prediction),
            round(float(probability), 5),
            risk_level,
            "COMPLETED"
        )

        cursor.execute(query, values)

        connection.commit()

        prediction_id = cursor.lastrowid

        print(
            f"Prediction saved successfully. "
            f"Prediction ID: {prediction_id}"
        )

        return True

    except Exception as e:

        connection.rollback()

        print("Prediction database error:", e)

        return False

    finally:

        cursor.close()
        connection.close()


def predict_from_extraction(
    patient_id,
    extraction_id
):
    """
    Run the trained ML model using a validated
    extracted_features database record.
    """

    extraction = get_extraction(extraction_id)

    if extraction is None:
        print("Extraction record not found.")
        return False

    # --------------------------------------------------------
    # Validation check
    # --------------------------------------------------------

    if extraction["validation_status"] != "VALID":

        print(
            "Prediction blocked: extraction is not VALID."
        )

        return False

    # --------------------------------------------------------
    # Build model input in EXACT training order
    # --------------------------------------------------------

    patient_data = [
        extraction["age"],
        extraction["sex"],
        extraction["chest_pain_type"],
        extraction["resting_bp"],
        extraction["cholesterol"],
        extraction["fasting_blood_sugar"],
        extraction["resting_ecg"],
        extraction["max_heart_rate"],
        extraction["exercise_angina"],
        extraction["oldpeak"],
        extraction["st_slope"]
    ]

    # --------------------------------------------------------
    # Make prediction using existing trained model
    # --------------------------------------------------------

    prediction, probability = predict_heart_disease(
        patient_data
    )

    print("\n===== AI PREDICTION =====")

    print("Prediction:", int(prediction))
    print(
        "Probability:",
        round(float(probability) * 100, 2),
        "%"
    )

    # --------------------------------------------------------
    # Save prediction
    # --------------------------------------------------------

    success = save_prediction(
        patient_id,
        extraction_id,
        prediction,
        probability
    )

    return success