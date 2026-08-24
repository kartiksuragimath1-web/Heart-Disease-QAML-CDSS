from src.prediction_service import predict_from_extraction


patient_id = 2
extraction_id = 2


success = predict_from_extraction(
    patient_id,
    extraction_id
)


if success:
    print(
        "\nAI prediction test SUCCESSFUL"
    )
else:
    print(
        "\nAI prediction test FAILED"
    )