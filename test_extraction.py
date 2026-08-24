from src.extraction_service import save_extracted_features


report_id = 2

pdf_path = (
    "uploads/ecg/"
    "sample_full_heart_features.pdf"
)

success = save_extracted_features(
    report_id,
    pdf_path
)

if success:
    print(
        "Extraction database test SUCCESSFUL"
    )
else:
    print(
        "Extraction database test FAILED"
    )