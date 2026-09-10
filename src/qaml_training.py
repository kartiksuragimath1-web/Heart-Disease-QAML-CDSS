import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from qiskit_machine_learning.algorithms import VQC
from qiskit_machine_learning.circuit.library import QNNCircuit
from qiskit_machine_learning.optimizers import COBYLA

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config import DATASET_PATH, MODEL_DIR


QAML_MODEL_PATH = f"{MODEL_DIR}/qaml_vqc.pkl"
QAML_SCALER_PATH = f"{MODEL_DIR}/qaml_scaler.pkl"


FEATURE_COLUMNS = [
    "age",
    "sex",
    "chest pain type",
    "resting bp s",
    "cholesterol",
    "fasting blood sugar",
    "resting ecg",
    "max heart rate",
    "exercise angina",
    "oldpeak",
    "ST slope"
]


def load_qaml_data():

    df = pd.read_csv(DATASET_PATH)

    df = df.drop_duplicates()

    X = df[FEATURE_COLUMNS]
    y = df["target"]

    return X, y


def prepare_qaml_data():

    X, y = load_qaml_data()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    return (
        X_train_scaled,
        X_test_scaled,
        y_train.to_numpy(),
        y_test.to_numpy(),
        scaler
    )


def train_qaml_model():

    print("Loading heart disease dataset...")

    (
        X_train,
        X_test,
        y_train,
        y_test,
        scaler
    ) = prepare_qaml_data()

    print("Training samples:", len(X_train))
    print("Testing samples:", len(X_test))
    print("Features:", X_train.shape[1])

    print("\nCreating 4-qubit QAML circuit...")

    qnn_circuit = QNNCircuit(num_qubits=4)

    print(qnn_circuit)

    print("\nCreating VQC...")

    vqc = VQC(
        feature_map=qnn_circuit.feature_map,
        ansatz=qnn_circuit.ansatz,
        optimizer=COBYLA(maxiter=20)
    )

    print("\nTraining QAML model...")

    vqc.fit(X_train[:, :4], y_train)

    print("\nQAML training completed.")

    print("\n===== QAML EVALUATION =====")

    qaml_predictions = vqc.predict(X_test[:, :4]).ravel()

    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
        confusion_matrix
    )

    accuracy = accuracy_score(y_test, qaml_predictions)
    precision = precision_score(y_test, qaml_predictions, zero_division=0)
    recall = recall_score(y_test, qaml_predictions, zero_division=0)
    f1 = f1_score(y_test, qaml_predictions, zero_division=0)
    cm = confusion_matrix(y_test, qaml_predictions)

    print("Accuracy :", round(accuracy * 100, 2), "%")
    print("Precision:", round(precision * 100, 2), "%")
    print("Recall   :", round(recall * 100, 2), "%")
    print("F1 Score :", round(f1 * 100, 2), "%")
    print("Confusion Matrix:")
    print(cm)
    print("\n===== MODEL COMPARISON =====")
    print("Hybrid KNN + Random Forest Accuracy: calculated separately")
    print("QAML Accuracy:", round(accuracy * 100, 2), "%")
    print("Saving QAML model configuration...")

    qaml_config = {
        "feature_map": qnn_circuit.feature_map,
        "ansatz": qnn_circuit.ansatz,
        "optimizer": "COBYLA",
        "maxiter": 20,
        "weights": vqc.weights
    }

    joblib.dump(qaml_config, QAML_MODEL_PATH)
    joblib.dump(scaler, QAML_SCALER_PATH)

    print("\nQAML model configuration saved:")
    print(QAML_MODEL_PATH)

    print("\nQAML scaler saved:")
    print(QAML_SCALER_PATH)

    print("\nModel saved:")
    print(QAML_MODEL_PATH)

    print("\nScaler saved:")
    print(QAML_SCALER_PATH)


if __name__ == "__main__":
    train_qaml_model()