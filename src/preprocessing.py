import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from config import DATASET_PATH


def load_dataset():
    """
    Load dataset
    """
    df = pd.read_csv(DATASET_PATH)
    return df


def preprocess_data():
    """
    Load and preprocess dataset
    """

    df = load_dataset()

    # Remove duplicate records
    df = df.drop_duplicates()

    # Features & Target
    X = df.drop("target", axis=1)
    y = df["target"]

    # Train Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    # Scaling
    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    return (
        X_train,
        X_test,
        X_train_scaled,
        X_test_scaled,
        y_train,
        y_test,
        scaler
    )