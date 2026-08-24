import pdfplumber

try:
    from .feature_extractor import extract_features
except ImportError:
    from feature_extractor import extract_features


def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF medical report.

    Returns:
        str: Extracted text
        None: If extraction fails
    """

    extracted_text = ""

    try:
        with pdfplumber.open(pdf_path) as pdf:

            for page in pdf.pages:

                text = page.extract_text()

                if text:
                    extracted_text += text + "\n"

        return extracted_text.strip()

    except Exception as e:

        print("PDF Extraction Error:", e)

        return None


def process_pdf(pdf_path):
    """
    Read PDF and extract clinical features.
    """

    text = extract_text_from_pdf(pdf_path)

    if not text:
        return None, None

    features = extract_features(text)

    return text, features


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    pdf_file = "uploads/ecg/sample_full_heart_features.pdf"

    text, features = process_pdf(pdf_file)

    if text:

        print("\n===== EXTRACTED TEXT =====\n")
        print(text)

        print("\n===== EXTRACTED FEATURES =====\n")

        for key, value in features.items():
            print(f"{key} : {value}")

    else:

        print("No text extracted.")