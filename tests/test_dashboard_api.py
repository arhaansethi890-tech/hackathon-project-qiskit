"""Contract tests for the local exploratory API and simulation response."""
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_and_options_are_available():
    health = client.get("/api/health")
    options = client.get("/api/options")

    assert health.status_code == 200
    assert health.json()["engine"] == "qiskit-aer"
    assert options.status_code == 200
    assert {item["id"] for item in options.json()["algorithms"]} == {"hva-vqe", "random-ry"}


def test_random_circuit_returns_counts_statevector_and_exports():
    response = client.post(
        "/api/simulate",
        json={
            "algorithm": "random-ry",
            "qubits": 2,
            "depth": 1,
            "shots": 256,
            "noise_enabled": False,
            "seed": 7,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_kind"] == "exploratory-local-aer"
    assert sum(payload["counts"].values()) == 256
    assert len(payload["probabilities"]) == 4
    assert len(payload["ideal_statevector"]) == 4
    assert payload["circuit_text"]
    assert payload["openqasm3"]
    assert payload["optimizer"] is None


def test_hva_returns_energy_and_fidelity_metrics():
    response = client.post(
        "/api/simulate",
        json={
            "algorithm": "hva-vqe",
            "qubits": 2,
            "depth": 1,
            "shots": 256,
            "noise_enabled": False,
            "seed": 13,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["optimizer"] == "L-BFGS-B"
    assert payload["optimizer_calls"] > 0
    assert payload["ideal_energy"] <= payload["exact_ground_energy"] + 1e-8
    assert 0.0 <= payload["ideal_ground_fidelity"] <= 1.0
    assert payload["noisy_ground_fidelity"] is None


def test_custom_noise_returns_density_matrix_metrics():
    response = client.post(
        "/api/simulate",
        json={
            "algorithm": "random-ry",
            "qubits": 2,
            "depth": 1,
            "shots": 256,
            "noise_enabled": True,
            "noise": {"p1": 0.002, "p2": 0.01, "p_readout": 0.02},
            "seed": 19,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["noise"] == {"p1": 0.002, "p2": 0.01, "p_readout": 0.02}
    assert payload["noisy_ground_fidelity"] is not None
    assert set(payload["noisy_observables"]) >= {"mx", "czz_nn", "mz2"}


def test_api_rejects_unbounded_simulation_requests():
    too_many_qubits = client.post(
        "/api/simulate",
        json={"algorithm": "random-ry", "qubits": 9, "noise_enabled": False},
    )
    invalid_noise = client.post(
        "/api/simulate",
        json={
            "algorithm": "random-ry",
            "qubits": 2,
            "noise": {"p1": 0.2, "p2": 0.005, "p_readout": 0.01},
        },
    )

    assert too_many_qubits.status_code == 422
    assert invalid_noise.status_code == 422
