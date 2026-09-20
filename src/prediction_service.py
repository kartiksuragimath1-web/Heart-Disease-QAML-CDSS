from database import get_db_connection
from src.prediction import predict_heart_disease
from src.quantum_model import qaml_predict


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
    Retrieve an extraction record from the database.
    """

    print(
        f"[PREDICTION] Fetching extraction_id={extraction_id}",
        flush=True
    )

    connection = get_db_connection()

    if connection is None:
        print(
            "[PREDICTION] ERROR: Database connection failed "
            "while fetching extraction.",
            flush=True
        )
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

        extraction = cursor.fetchone()

        if extraction is None:
            print(
                f"[PREDICTION] No extraction found for "
                f"extraction_id={extraction_id}",
                flush=True
            )
        else:
            print(
                f"[PREDICTION] Extraction found. "
                f"validation_status={extraction['validation_status']}",
                flush=True
            )

        return extraction

    except Exception as e:
        print(
            "[PREDICTION] ERROR while fetching extraction:",
            repr(e),
            flush=True
        )
        raise

    finally:
        cursor.close()
        connection.close()


def save_prediction(
    patient_id,
    extraction_id,
    prediction,
    probability,
    qaml_prediction,
    quantum_score
):
    """
    Save ML + QAML prediction into the predictions table.
    """

    print(
        "\n[PREDICTION] ===== SAVE PREDICTION START =====",
        flush=True
    )

    print(
        f"[PREDICTION] patient_id={patient_id}",
        flush=True
    )

    print(
        f"[PREDICTION] extraction_id={extraction_id}",
        flush=True
    )

    print(
        f"[PREDICTION] prediction={prediction}",
        flush=True
    )

    print(
        f"[PREDICTION] probability={probability}",
        flush=True
    )

    print(
        f"[PREDICTION] qaml_prediction={qaml_prediction}",
        flush=True
    )

    print(
        f"[PREDICTION] quantum_score={quantum_score}",
        flush=True
    )

    # --------------------------------------------------------
    # Determine risk level
    # --------------------------------------------------------

    probability = float(probability)

    if probability < 0.40:
        risk_level = "LOW"

    elif probability < 0.70:
        risk_level = "MODERATE"

    else:
        risk_level = "HIGH"

    print(
        f"[PREDICTION] Calculated risk level={risk_level}",
        flush=True
    )

    # --------------------------------------------------------
    # Database connection
    # --------------------------------------------------------

    print(
        "[PREDICTION] Connecting to database...",
        flush=True
    )

    connection = get_db_connection()

    if connection is None:

        print(
            "[PREDICTION] ERROR: Could not connect to database "
            "while saving prediction.",
            flush=True
        )

        return False

    print(
        "[PREDICTION] Database connection successful.",
        flush=True
    )

    cursor = connection.cursor()

    try:

        # ----------------------------------------------------
        # Prevent duplicate predictions
        # ----------------------------------------------------

        check_query = """
        SELECT prediction_id
        FROM predictions
        WHERE extraction_id = %s
        LIMIT 1
        """

        print(
            "[PREDICTION] Checking for existing prediction...",
            flush=True
        )

        cursor.execute(
            check_query,
            (extraction_id,)
        )

        existing_prediction = cursor.fetchone()

        if existing_prediction:

            print(
                f"[PREDICTION] Prediction already exists for "
                f"extraction_id={extraction_id}. "
                f"prediction_id={existing_prediction[0]}",
                flush=True
            )

            return True

        # ----------------------------------------------------
        # Insert prediction
        # ----------------------------------------------------

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
            prediction_status,
            qaml_prediction,
            qaml_quantum_score
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
        """

        values = (
            int(patient_id),
            int(extraction_id),
            "Hybrid KNN + Random Forest",
            "1.0",
            int(prediction),
            round(probability, 5),
            risk_level,
            "COMPLETED",
            int(qaml_prediction),
            round(float(quantum_score), 8)
        )

        print(
            "[PREDICTION] Executing prediction INSERT...",
            flush=True
        )

        print(
            f"[PREDICTION] INSERT values={values}",
            flush=True
        )

        cursor.execute(
            query,
            values
        )

        print(
            "[PREDICTION] INSERT executed successfully.",
            flush=True
        )

        # ----------------------------------------------------
        # Commit transaction
        # ----------------------------------------------------

        connection.commit()

        print(
            "[PREDICTION] Database transaction committed.",
            flush=True
        )

        prediction_id = cursor.lastrowid

        print(
            f"[PREDICTION] Prediction saved successfully. "
            f"Prediction ID={prediction_id}",
            flush=True
        )

        print(
            "[PREDICTION] ===== SAVE PREDICTION END =====\n",
            flush=True
        )

        return True

    except Exception as e:

        print(
            "[PREDICTION] DATABASE ERROR:",
            repr(e),
            flush=True
        )

        try:
            connection.rollback()

            print(
                "[PREDICTION] Database transaction rolled back.",
                flush=True
            )

        except Exception as rollback_error:

            print(
                "[PREDICTION] Rollback error:",
                repr(rollback_error),
                flush=True
            )

        return False

    finally:

        cursor.close()
        connection.close()

        print(
            "[PREDICTION] Database resources closed.",
            flush=True
        )


def predict_from_extraction(
    patient_id,
    extraction_id
):
    """
    Run the trained classical ML model and QAML model
    using a validated extracted_features database record.

    Prediction is performed only when validation_status == VALID.
    """

    print(
        "\n" + "=" * 70,
        flush=True
    )

    print(
        "[PREDICTION] PREDICTION SERVICE STARTED",
        flush=True
    )

    print(
        f"[PREDICTION] patient_id={patient_id}",
        flush=True
    )

    print(
        f"[PREDICTION] extraction_id={extraction_id}",
        flush=True
    )

    print(
        "=" * 70,
        flush=True
    )

    # --------------------------------------------------------
    # Get extraction
    # --------------------------------------------------------

    extraction = get_extraction(extraction_id)

    if extraction is None:

        print(
            "[PREDICTION] ERROR: Extraction record not found.",
            flush=True
        )

        return False

    print(
        "[PREDICTION] Extraction record loaded successfully.",
        flush=True
    )

    # --------------------------------------------------------
    # Validation check
    # --------------------------------------------------------

    validation_status = extraction["validation_status"]

    print(
        f"[PREDICTION] Validation status: {validation_status}",
        flush=True
    )

    if validation_status != "VALID":

        print(
            "[PREDICTION] Prediction BLOCKED because extraction "
            "is not VALID.",
            flush=True
        )

        return False

    # --------------------------------------------------------
    # Build model input
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

    print(
        "\n[PREDICTION] ===== MODEL INPUT =====",
        flush=True
    )

    print(
        f"[PREDICTION] Feature columns: {FEATURE_COLUMNS}",
        flush=True
    )

    print(
        f"[PREDICTION] Patient data: {patient_data}",
        flush=True
    )

    # --------------------------------------------------------
    # Check missing ML features
    # --------------------------------------------------------

    missing_features = []

    for column, value in zip(
        FEATURE_COLUMNS,
        patient_data
    ):

        if value is None:
            missing_features.append(column)

    if missing_features:

        print(
            "[PREDICTION] Prediction BLOCKED.",
            flush=True
        )

        print(
            f"[PREDICTION] Missing features: {missing_features}",
            flush=True
        )

        return False

    print(
        "[PREDICTION] All 11 ML features are available.",
        flush=True
    )

    # --------------------------------------------------------
    # Classical ML model
    # --------------------------------------------------------

    try:

        print(
            "\n[PREDICTION] ===== CLASSICAL MODEL START =====",
            flush=True
        )

        print(
            "[PREDICTION] Calling predict_heart_disease()...",
            flush=True
        )

        prediction, probability = predict_heart_disease(
            patient_data
        )

        print(
            "[PREDICTION] Classical model completed.",
            flush=True
        )

        print(
            f"[PREDICTION] Classical prediction={prediction}",
            flush=True
        )

        print(
            f"[PREDICTION] Classical probability={probability}",
            flush=True
        )

    except Exception as e:

        print(
            "\n[PREDICTION] ===== CLASSICAL MODEL ERROR =====",
            flush=True
        )

        print(
            "[PREDICTION] Error:",
            repr(e),
            flush=True
        )

        raise

    # --------------------------------------------------------
    # QAML model
    # --------------------------------------------------------

    try:

        print(
            "\n[PREDICTION] ===== QAML MODEL START =====",
            flush=True
        )

        qaml_features = [
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

        print(
            f"[PREDICTION] QAML features: {qaml_features}",
            flush=True
        )

        print(
            "[PREDICTION] Calling qaml_predict()...",
            flush=True
        )

        qaml_prediction, quantum_score = qaml_predict(
            qaml_features
        )

        print(
            "[PREDICTION] QAML model completed.",
            flush=True
        )

        print(
            f"[PREDICTION] QAML prediction={qaml_prediction}",
            flush=True
        )

        print(
            f"[PREDICTION] Quantum score={quantum_score}",
            flush=True
        )

    except Exception as e:

        print(
            "\n[PREDICTION] ===== QAML MODEL ERROR =====",
            flush=True
        )

        print(
            "[PREDICTION] Error:",
            repr(e),
            flush=True
        )

        raise

    # --------------------------------------------------------
    # Final prediction information
    # --------------------------------------------------------

    print(
        "\n[PREDICTION] ===== AI PREDICTION =====",
        flush=True
    )

    print(
        f"[PREDICTION] Prediction: {int(prediction)}",
        flush=True
    )

    print(
        f"[PREDICTION] Probability: "
        f"{round(float(probability) * 100, 2)}%",
        flush=True
    )

    print(
        f"[PREDICTION] QAML Prediction: "
        f"{int(qaml_prediction)}",
        flush=True
    )

    print(
        f"[PREDICTION] Quantum Score: "
        f"{round(float(quantum_score), 8)}",
        flush=True
    )

    # --------------------------------------------------------
    # Save prediction
    # --------------------------------------------------------

    print(
        "\n[PREDICTION] ABOUT TO SAVE PREDICTION",
        flush=True
    )

    success = save_prediction(
        patient_id,
        extraction_id,
        prediction,
        probability,
        qaml_prediction,
        quantum_score
    )

    print(
        f"[PREDICTION] SAVE PREDICTION RESULT: {success}",
        flush=True
    )

    print(
        "[PREDICTION] PREDICTION SERVICE FINISHED",
        flush=True
    )

    return success