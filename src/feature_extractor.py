import re


MODEL_FEATURES = [
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


def extract_features(text):
    """
    Extract clinical features from a medical report.

    Only extracts values that are explicitly present in the
    report. Missing values remain None.

    No clinical values are invented.
    """

    features = {
        "age": None,
        "sex": None,
        "chest_pain_type": None,
        "resting_bp": None,
        "cholesterol": None,
        "fasting_blood_sugar": None,
        "resting_ecg": None,
        "max_heart_rate": None,
        "exercise_angina": None,
        "oldpeak": None,
        "st_slope": None,

        # ECG-specific information
        "ecg_quality": None,
        "ventricular_rate": None,
        "pr_interval": None,
        "qrs_duration": None,
        "qtc_interval": None,
        "cardiac_axis": None,
        "sinus_rhythm": None,
        "av_conduction": None
    }

    # ============================================================
    # STANDARD ML FEATURES
    # ============================================================

    # AGE
    match = re.search(
        r"\bAge\s*[:\-]?\s*(\d{2,3})\b",
        text,
        re.IGNORECASE
    )

    if match:
        age = int(match.group(1))

        if 1 <= age <= 120:
            features["age"] = age

    # SEX / GENDER
    match = re.search(
        r"\b(?:Sex|Gender)\s*[:\-]?\s*(Male|Female)\b",
        text,
        re.IGNORECASE
    )

    if match:
        value = match.group(1).lower()

        if value == "male":
            features["sex"] = 1
        elif value == "female":
            features["sex"] = 0

    # CHEST PAIN TYPE
    match = re.search(
        r"\bChest\s*Pain\s*Type\s*[:\-]?\s*(\d+)\b",
        text,
        re.IGNORECASE
    )

    if match:
        value = int(match.group(1))

        if 1 <= value <= 4:
            features["chest_pain_type"] = value

    # RESTING BLOOD PRESSURE
    #
    # Supports explicitly labelled formats such as:
    # Resting BP 128
    # Resting BP: 128
    # BP: 128/82
    # BP 128/82
    # Blood Pressure: 130
    # Blood Pressure 130/80
    #
    # If systolic/diastolic is present, only the explicitly
    # labelled systolic value is used for resting_bp.
    match = re.search(
        r"\b(?:Resting\s*)?(?:Blood\s*Pressure|BP)\s*[:\-]?\s*(\d{2,3})(?:\s*/\s*\d{2,3})?\b",
        text,
        re.IGNORECASE
    )

    if match:
        value = float(match.group(1))

        if 50 <= value <= 250:
            features["resting_bp"] = value

    # CHOLESTEROL
    match = re.search(
        r"\bCholesterol\s*[:\-]?\s*(\d+(?:\.\d+)?)\b",
        text,
        re.IGNORECASE
    )

    if match:
        value = float(match.group(1))

        if 50 <= value <= 700:
            features["cholesterol"] = value

    # FASTING BLOOD SUGAR
    match = re.search(
        r"\bFasting\s*Blood\s*Sugar\s*[:\-]?\s*(\d+)\b",
        text,
        re.IGNORECASE
    )

    if match:
        value = int(match.group(1))

        if value in (0, 1):
            features["fasting_blood_sugar"] = value

    # RESTING ECG
    match = re.search(
        r"\bResting\s*ECG\s*[:\-]?\s*(\d+)\b",
        text,
        re.IGNORECASE
    )

    if match:
        value = int(match.group(1))

        if 0 <= value <= 2:
            features["resting_ecg"] = value

    # MAXIMUM HEART RATE
    #
    # IMPORTANT:
    # This intentionally does NOT match ordinary:
    # Heart Rate 80 bpm
    #
    # Only explicitly labelled Maximum Heart Rate / Max Heart Rate
    # is accepted.
    match = re.search(
        r"\b(?:Maximum\s*Heart\s*Rate|Max\s*Heart\s*Rate)\s*[:\-]?\s*(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if match:
        value = float(match.group(1))

        if 40 <= value <= 250:
            features["max_heart_rate"] = value

    # EXERCISE ANGINA
    match = re.search(
        r"\bExercise\s*Angina\s*[:\-]?\s*(\d+)\b",
        text,
        re.IGNORECASE
    )

    if match:
        value = int(match.group(1))

        if value in (0, 1):
            features["exercise_angina"] = value

    # OLDPEAK
    match = re.search(
        r"\bOldpeak\s*[:\-]?\s*(-?\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if match:
        value = float(match.group(1))

        if -5 <= value <= 10:
            features["oldpeak"] = value

    # ST SLOPE
    match = re.search(
        r"\bST\s*Slope\s*[:\-]?\s*(\d+)\b",
        text,
        re.IGNORECASE
    )

    if match:
        value = int(match.group(1))

        if 1 <= value <= 3:
            features["st_slope"] = value

    # ============================================================
    # ECG-SPECIFIC FEATURES
    # ============================================================

    # ECG QUALITY
    match = re.search(
        r"\bECG\s*Quality\s*[:\-]?\s*(Good|Poor|Bad|Adequate)\b",
        text,
        re.IGNORECASE
    )

    if match:
        features["ecg_quality"] = match.group(1).strip()

    # VENTRICULAR RATE
    match = re.search(
        r"\bVentricular\s*(?:rate)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*bpm",
        text,
        re.IGNORECASE
    )

    if match:
        features["ventricular_rate"] = float(match.group(1))

    # PR INTERVAL / PR DURATION
    match = re.search(
        r"\bPR\s*(?:interval|duration)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*ms",
        text,
        re.IGNORECASE
    )

    if match:
        features["pr_interval"] = float(match.group(1))

    # QRS DURATION
    match = re.search(
        r"\bQRS\s*duration\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*ms",
        text,
        re.IGNORECASE
    )

    if match:
        features["qrs_duration"] = float(match.group(1))

    # QTc INTERVAL
    #
    # Supports:
    # QT/QTcF interval: 360/429 ms
    match = re.search(
        r"\bQT\s*/\s*QTcF\s*interval\s*[:\-]?\s*\d+(?:\.\d+)?\s*/\s*(\d+(?:\.\d+)?)\s*ms",
        text,
        re.IGNORECASE
    )

    if match:
        features["qtc_interval"] = float(match.group(1))

    # CARDIAC AXIS
    match = re.search(
        r"\bQRS\s*axis\s*[:\-]?\s*(-?\d+(?:\.\d+)?)\s*°?",
        text,
        re.IGNORECASE
    )

    if match:
        features["cardiac_axis"] = float(match.group(1))

    # SINUS RHYTHM
    match = re.search(
        r"\b(?:Is\s*)?Sinus\s*Rhythm\s*(?:Present)?\s*[:\-]?\s*(Yes|No)",
        text,
        re.IGNORECASE
    )

    if match:
        features["sinus_rhythm"] = (
            match.group(1).lower() == "yes"
        )

    # AV CONDUCTION
    match = re.search(
        r"\bAV\s*Conduction\s*[:\-]?\s*([^\n]+)",
        text,
        re.IGNORECASE
    )

    if match:
        features["av_conduction"] = (
            match.group(1)
            .strip()
            .split("\n")[0]
        )

    return features