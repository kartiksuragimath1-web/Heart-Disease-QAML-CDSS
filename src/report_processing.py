import pdfplumber
import pytesseract
from pdf2image import convert_from_path

try:
    from .feature_extractor import extract_features
except ImportError:
    from feature_extractor import extract_features


def extract_text_from_pdf(pdf_path):
    """
    Extract text from a PDF medical report.

    First attempts normal PDF text extraction.
    If insufficient text is found, falls back to OCR.

    Returns:
        str: Extracted text
        None: If extraction fails
    """

    extracted_text = ""
    extraction_method = "PDF_TEXT"

    # --------------------------------------------------------
    # STEP 1: Normal PDF text extraction
    # --------------------------------------------------------

    try:
        with pdfplumber.open(pdf_path) as pdf:

            for page in pdf.pages:

                text = page.extract_text()

                if text:
                    extracted_text += text + "\n"

    except Exception as e:

        print("PDF Extraction Error:", e)

    extracted_text = extracted_text.strip()

    # --------------------------------------------------------
    # STEP 2: OCR fallback for scanned/image PDFs
    # --------------------------------------------------------

    if len(extracted_text) < 100:
        extraction_method = "OCR"

        print("Insufficient PDF text. Starting OCR...")

        try:

            pages = convert_from_path(
                pdf_path,
                dpi=200
            )

            ocr_text = []

            for page_number, page in enumerate(
                pages,
                start=1
            ):

                text = pytesseract.image_to_string(
                    page
                )

                if text.strip():

                    ocr_text.append(
                        f"\n--- OCR PAGE {page_number} ---\n"
                    )

                    ocr_text.append(text)

            extracted_text = "\n".join(
                ocr_text
            ).strip()

            print(
                f"OCR completed. "
                f"Characters extracted: {len(extracted_text)}"
            )

        except Exception as e:

            print(
                "OCR Extraction Error:",
                e
            )

    # --------------------------------------------------------
    # STEP 3: Final check
    # --------------------------------------------------------

    if not extracted_text:
        return None, None

    return extracted_text, extraction_method

def process_pdf(pdf_path):
    """
    Read PDF and extract clinical features.
    """

    text, extraction_method = extract_text_from_pdf(pdf_path)

    if not text:
        return None, None, None

    features = extract_features(text)

    return text, features, extraction_method


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