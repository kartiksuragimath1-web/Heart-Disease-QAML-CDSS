import re


def extract_features(text):
    """
    Extract the 11 clinical features required by
    the HeartQAML heart disease model.

    Missing values are kept as None.
    No medical value is invented.
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
        "st_slope": None
    }

    # -------------------------
    # AGE
    # -------------------------
    match = re.search(r"Age\s*[:\-]?\s*(\d+)", text, re.IGNORECASE)
    if match:
        features["age"] = int(match.group(1))

    # -------------------------
    # SEX
    # -------------------------
    match = re.search(r"Sex\s*[:\-]?\s*([A-Za-z]+)", text, re.IGNORECASE)

    if match:
        value = match.group(1).lower()

        if value == "male":
            features["sex"] = 1
        elif value == "female":
            features["sex"] = 0

    # -------------------------
    # CHEST PAIN TYPE
    # -------------------------
    match = re.search(
        r"Chest\s*Pain\s*Type\s*[:\-]?\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if match:
        features["chest_pain_type"] = int(match.group(1))

    # -------------------------
    # RESTING BLOOD PRESSURE
    # -------------------------
    match = re.search(
        r"Resting\s*Blood\s*Pressure\s*[:\-]?\s*(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if match:
        features["resting_bp"] = float(match.group(1))

    # -------------------------
    # CHOLESTEROL
    # -------------------------
    match = re.search(
        r"Cholesterol\s*[:\-]?\s*(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if match:
        features["cholesterol"] = float(match.group(1))

    # -------------------------
    # FASTING BLOOD SUGAR
    # -------------------------
    match = re.search(
        r"Fasting\s*Blood\s*Sugar\s*[:\-]?\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if match:
        features["fasting_blood_sugar"] = int(match.group(1))

    # -------------------------
    # RESTING ECG
    # -------------------------
    match = re.search(
        r"Resting\s*ECG\s*[:\-]?\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if match:
        features["resting_ecg"] = int(match.group(1))

    # -------------------------
    # MAXIMUM HEART RATE
    # -------------------------
    match = re.search(
        r"Maximum\s*Heart\s*Rate\s*[:\-]?\s*(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if match:
        features["max_heart_rate"] = float(match.group(1))

    # -------------------------
    # EXERCISE ANGINA
    # -------------------------
    match = re.search(
        r"Exercise\s*Angina\s*[:\-]?\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if match:
        features["exercise_angina"] = int(match.group(1))

    # -------------------------
    # OLDPEAK
    # -------------------------
    match = re.search(
        r"Oldpeak\s*[:\-]?\s*(-?\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if match:
        features["oldpeak"] = float(match.group(1))

    # -------------------------
    # ST SLOPE
    # -------------------------
    match = re.search(
        r"ST\s*Slope\s*[:\-]?\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if match:
        features["st_slope"] = int(match.group(1))

    return features