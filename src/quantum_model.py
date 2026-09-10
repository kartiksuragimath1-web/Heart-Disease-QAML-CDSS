import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


def quantum_feature_encoding(features):
    """
    Encode 11 normalized clinical features into a 4-qubit
    quantum circuit.

    The 11 classical features are compressed into 4 groups
    and encoded using rotation gates.
    """

    features = np.asarray(features, dtype=float)

    if len(features) != 11:
        raise ValueError("Exactly 11 clinical features are required.")

    # Group the 11 clinical features into 4 quantum inputs.
    quantum_inputs = np.array([
        np.mean(features[0:3]),
        np.mean(features[3:6]),
        np.mean(features[6:9]),
        np.mean(features[9:11])
    ])

    # Convert normalized values into rotation angles.
    angles = np.tanh(quantum_inputs) * np.pi

    qc = QuantumCircuit(4)

    for qubit, angle in enumerate(angles):
        qc.ry(float(angle), qubit)

    # Add entanglement between qubits.
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.cx(2, 3)

    return qc


def quantum_statevector(features):
    """
    Generate the quantum statevector.
    """

    circuit = quantum_feature_encoding(features)

    return Statevector.from_instruction(circuit)


def quantum_probability(features):
    """
    Generate a quantum-derived probability feature.

    This is NOT a clinical disease probability.
    It is a quantum feature used by the hybrid model.
    """

    state = quantum_statevector(features)

    probabilities = state.probabilities()

    # Probability of the |0000> quantum state.
    probability = float(probabilities[0])

    return probability


if __name__ == "__main__":

    demo_features = [
        -0.94,
        0.52,
        -1.33,
        -0.27,
        0.15,
        -0.54,
        0.51,
        -2.26,
        -0.83,
        0.32,
        0.61
    ]

    circuit = quantum_feature_encoding(demo_features)

    print("Quantum Circuit:")
    print(circuit)

    probability = quantum_probability(demo_features)

    print("Quantum Feature:", probability)

def qaml_score(features, classical_probability):
    """
    Combine the classical ML probability with the
    quantum-derived feature.

    This is an experimental QAML score and is not
    a clinical diagnosis.
    """

    quantum_feature = quantum_probability(features)

    # Weighted hybrid score
    qaml_score = (
        0.80 * float(classical_probability)
        + 0.20 * quantum_feature
    )

    return float(qaml_score)
def qaml_predict(features):
    """
    Run inference using the trained QAML model.

    Returns:
        prediction: 0 or 1
        quantum_score: probability of the |0000> state

    Note:
        quantum_score is a quantum model output and must not
        be presented as a clinical disease probability.
    """

    import joblib
    from config import MODEL_DIR

    model_path = f"{MODEL_DIR}/qaml_vqc.pkl"

    config = joblib.load(model_path)

    features = np.asarray(features, dtype=float)

    if len(features) != 11:
        raise ValueError("Exactly 11 clinical features are required.")

    # The QAML model was trained using the first 4 scaled features.
    qaml_features = features[:4]

    feature_map = config["feature_map"]
    ansatz = config["ansatz"]
    weights = np.asarray(config["weights"])

    # Encode the four features.
    feature_circuit = feature_map.assign_parameters(qaml_features)

    # Insert the trained parameters.
    ansatz_circuit = ansatz.assign_parameters(weights)

    # Combine feature map and trained ansatz.
    circuit = feature_circuit.compose(ansatz_circuit)

    # Simulate the trained quantum circuit.
    state = Statevector.from_instruction(circuit)

    probabilities = state.probabilities()

    quantum_score = float(probabilities[0])

    # VQC binary interpretation:
    # compare the probability mass of the two classes.
    class_0_probability = float(
        np.sum(probabilities[0::2])
    )

    class_1_probability = float(
        np.sum(probabilities[1::2])
    )

    prediction = 1 if class_1_probability > class_0_probability else 0

    return prediction, quantum_score