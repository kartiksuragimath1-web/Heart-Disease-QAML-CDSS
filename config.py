import os

# Base Project Directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Dataset Path
DATASET_PATH = os.path.join(
    BASE_DIR,
    "dataset",
    "heart_statlog_cleveland_hungary_final.csv"
)

# Model Directory
MODEL_DIR = os.path.join(BASE_DIR, "model")

# Saved Models
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.pkl")
FINAL_MODEL_PATH = os.path.join(MODEL_DIR, "final_model.pkl")