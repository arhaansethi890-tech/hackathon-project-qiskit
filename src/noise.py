"""Validated Kit-literal synthetic noise model plus an explicit RZ sensitivity variant."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error

DEFAULT_PROCESSOR_CONFIG = Path(__file__).resolve().parents[1] / "processors" / "processor_A.json"
ONE_QUBIT_BASIS = ("rz", "sx", "x")


def load_noise_settings(config_path=None, *, rz_noiseless: bool | None = None) -> dict:
    """Load and validate saved probabilities; optionally remove RZ only as sensitivity."""
    path = Path(config_path) if config_path is not None else DEFAULT_PROCESSOR_CONFIG
    try:
        config = json.loads(path.read_text())
        settings = config["noise_model"]
        basis = tuple(config["basis_gates"])
        p1 = float(settings["single_qubit_depolarizing_p"])
        p_cx = float(settings["cx_depolarizing_p"])
        matrix = np.asarray(settings["readout_error_matrix"], dtype=float)
        configured_gates = tuple(settings["single_qubit_noisy_gates"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid noise configuration in {path}: {exc}") from exc
    if not np.isfinite(p1) or not 0.0 <= p1 <= 1.0:
        raise ValueError("single-qubit depolarizing probability must be finite and in [0,1]")
    if not np.isfinite(p_cx) or not 0.0 <= p_cx <= 1.0:
        raise ValueError("CX depolarizing probability must be finite and in [0,1]")
    if matrix.shape != (2, 2) or not np.isfinite(matrix).all() or (matrix < 0).any() or (matrix > 1).any():
        raise ValueError("readout error matrix must be a finite 2x2 probability matrix")
    if not np.allclose(matrix.sum(axis=1), 1.0, atol=1e-12, rtol=0):
        raise ValueError("readout error matrix rows must sum to one")
    if not np.allclose(matrix, [[matrix[0, 0], matrix[0, 1]], [matrix[0, 1], matrix[0, 0]]], atol=1e-12, rtol=0):
        raise ValueError("configured readout error must be symmetric")
    if not set(ONE_QUBIT_BASIS).issubset(basis) or "cx" not in basis:
        raise ValueError("processor basis must include rz, sx, x, and cx for the fixed model")
    if not set(configured_gates).issubset(set(ONE_QUBIT_BASIS)):
        raise ValueError("single-qubit noise may only target configured one-qubit basis gates")

    if rz_noiseless is None:
        noisy_gates = configured_gates
        rz_noiseless_resolved = bool(settings["rz_noiseless"])
    elif rz_noiseless:
        noisy_gates = tuple(gate for gate in configured_gates if gate != "rz")
        rz_noiseless_resolved = True
    else:
        noisy_gates = tuple(gate for gate in ONE_QUBIT_BASIS if gate in basis)
        rz_noiseless_resolved = False
    if not noisy_gates:
        raise ValueError("at least one single-qubit basis gate must receive noise")
    return {
        "single_qubit_depolarizing_p": p1,
        "single_qubit_noisy_gates": list(noisy_gates),
        "rz_noiseless": rz_noiseless_resolved,
        "cx_depolarizing_p": p_cx,
        "readout_error_matrix": matrix.tolist(),
        "readout_flip_probability": float(matrix[0, 1]),
        "basis_gates": list(basis),
        "variant": "project-rz-noiseless" if rz_noiseless_resolved else "kit-literal-all-one-qubit-gates",
        "source": settings["source"],
        "scope_quote": "Updated Challenge Kit p.4 §3.4: single-qubit depolarizing probability = 0.001 per 1-qubit gate",
    }


def fixed_noise_model(config_path=None, *, rz_noiseless: bool | None = None) -> NoiseModel:
    """Build Qiskit Aer noise model. The default applies p1 to RZ, SX, and X per Kit p.4."""
    settings = load_noise_settings(config_path, rz_noiseless=rz_noiseless)
    model = NoiseModel()
    model.add_all_qubit_quantum_error(
        depolarizing_error(settings["single_qubit_depolarizing_p"], 1),
        settings["single_qubit_noisy_gates"],
    )
    model.add_all_qubit_quantum_error(
        depolarizing_error(settings["cx_depolarizing_p"], 2), ["cx"]
    )
    model.add_all_qubit_readout_error(ReadoutError(settings["readout_error_matrix"]))
    return model
