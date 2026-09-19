from database import get_db_connection
from src.report_processing import process_pdf


REQUIRED_FEATURES = [
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


def calculate_extraction_confidence(features):
    """
    Calculate extraction confidence based on the
    number of required ML features successfully extracted.
    """

    extracted_count = sum(
        features.get(feature) is not None
        for feature in REQUIRED_FEATURES
    )

    return extracted_count / len(REQUIRED_FEATURES)


def validate_features(features):
    """
    Basic structural/range validation.

    Missing features are not invented.
    """

    errors = []

    ranges = {
        "age": (1, 120),
        "sex": (0, 1),
        "chest_pain_type": (1, 4),
        "resting_bp": (50, 250),
        "cholesterol": (50, 700),
        "fasting_blood_sugar": (0, 1),
        "resting_ecg": (0, 2),
        "max_heart_rate": (40, 250),
        "exercise_angina": (0, 1),
        "oldpeak": (-5, 10),
        "st_slope": (1, 3)
    }

    for feature in REQUIRED_FEATURES:

        value = features.get(feature)

        if value is None:
            errors.append(f"Missing: {feature}")
            continue

        minimum, maximum = ranges[feature]

        if not minimum <= value <= maximum:
            errors.append(
                f"Invalid {feature}: {value}"
            )

    return errors


def save_extracted_features(report_id, pdf_path):
    """
    Process a medical report and save all extracted
    clinical features into extracted_features.
    """

    # --------------------------------------------------------
    # Extract text and features
    # --------------------------------------------------------

    text, features, extraction_method = process_pdf(pdf_path)

    if not text or not features:
        print("Feature extraction failed.")
        return False

    print("\n===== EXTRACTED FEATURES =====")

    for feature in REQUIRED_FEATURES:
        print(
            f"{feature}: "
            f"{features.get(feature)}"
        )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    confidence = calculate_extraction_confidence(
        features
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    validation_errors = validate_features(
        features
    )

    if validation_errors:
        validation_status = "NEEDS_REVIEW"
    else:
        validation_status = "VALID"

    print(
        f"\nExtraction confidence: "
        f"{confidence:.4f}"
    )

    print(
        f"Validation status: "
        f"{validation_status}"
    )

    if validation_errors:

        print("\nValidation issues:")

        for error in validation_errors:
            print("-", error)

    # --------------------------------------------------------
    # Database connection
    # --------------------------------------------------------

    connection = get_db_connection()

    if connection is None:
        print("Database connection failed.")
        return False

    cursor = connection.cursor()

    try:

        query = """
        INSERT INTO extracted_features
        (
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
            extraction_method,
            validation_status,
            extraction_confidence,
            doctor_verified,
            ecg_quality,
            ventricular_rate,
            pr_interval,
            qrs_duration,
            qtc_interval,
            cardiac_axis,
            sinus_rhythm,
            av_conduction
        )
        VALUES
        (
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s
        )
        """

        values = (
            report_id,

            features.get("age"),
            features.get("sex"),
            features.get("chest_pain_type"),
            features.get("resting_bp"),
            features.get("cholesterol"),
            features.get("fasting_blood_sugar"),
            features.get("resting_ecg"),
            features.get("max_heart_rate"),
            features.get("exercise_angina"),
            features.get("oldpeak"),
            features.get("st_slope"),

            extraction_method,
            validation_status,
            round(confidence, 4),
            0,

            features.get("ecg_quality"),
            features.get("ventricular_rate"),
            features.get("pr_interval"),
            features.get("qrs_duration"),
            features.get("qtc_interval"),
            features.get("cardiac_axis"),
            features.get("sinus_rhythm"),
            features.get("av_conduction")
        )

        cursor.execute(query, values)

        connection.commit()

        extraction_id = cursor.lastrowid

        print(
            f"\nExtraction saved successfully."
        )

        print(
            f"Extraction ID: {extraction_id}"
        )

        return extraction_id

    except Exception as e:

        connection.rollback()

        print(
            "Feature database error:",
            e
        )

        return False

    finally:

        cursor.close()
        connection.close()