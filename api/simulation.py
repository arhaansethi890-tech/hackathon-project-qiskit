"""Reusable exploratory Qiskit circuit and simulation engine.

This module deliberately keeps user-controlled experiments separate from the
locked Phase 2 benchmark runner. Its small system-size limits make local
statevector and density-matrix outputs practical and predictable.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import DensityMatrix, Statevector, state_fidelity
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error
from qiskit.qasm3 import dumps as qasm3_dumps
from scipy.optimize import minimize

import qff_sim as qff

BASE_BASIS_GATES = ("rz", "sx", "x", "cx")
EXPLORATORY_MAX_ITERATIONS = 180


def _random_ry_circuit(qubits: int, depth: int, seed: int) -> QuantumCircuit:
    """Build a seeded hardware-efficient RY/CX circuit on a nearest-neighbor line."""
    rng = np.random.default_rng(seed)
    circuit = QuantumCircuit(qubits, name="random_ry")
    for layer in range(depth):
        for wire in range(qubits):
            circuit.ry(float(rng.uniform(-np.pi, np.pi)), wire)
        # Alternating disjoint CX layers limit avoidable serial entanglers.
        start = layer % 2
        for control in range(start, qubits - 1, 2):
            circuit.cx(control, control + 1)
    return circuit


def _noise_model(settings: dict[str, float], include_rzz: bool) -> NoiseModel:
    """Create a configurable exploratory depolarizing and readout noise model."""
    model = NoiseModel()
    p1 = float(settings["p1"])
    p2 = float(settings["p2"])
    p_readout = float(settings["p_readout"])
    if p1:
        model.add_all_qubit_quantum_error(depolarizing_error(p1, 1), ["rz", "sx", "x"])
    if p2:
        two_qubit_gates = ["cx", "rzz"] if include_rzz else ["cx"]
        model.add_all_qubit_quantum_error(depolarizing_error(p2, 2), two_qubit_gates)
    if p_readout:
        model.add_all_qubit_readout_error(
            ReadoutError([[1.0 - p_readout, p_readout], [p_readout, 1.0 - p_readout]])
        )
    return model


def _bind(circuit: QuantumCircuit, parameters: list, values: np.ndarray) -> QuantumCircuit:
    """Return a copy of a parameterized circuit with its parameters assigned."""
    return circuit.assign_parameters(
        {parameter: float(value) for parameter, value in zip(parameters, values)},
        inplace=False,
    )


def _hva_state(
    qubits: int,
    depth: int,
    g: float,
    seed: int,
    zz_mode: str,
) -> tuple[QuantumCircuit, dict[str, Any]]:
    """Optimize the open-chain TFIM HVA and return its bound circuit and diagnostics."""
    circuit, parameters = qff.hva_ansatz(qubits, depth, zz_mode=zz_mode)
    hamiltonian = qff.tfim_hamiltonian(qubits, J=1.0, g=g, periodic=False)
    rng = np.random.default_rng(seed)
    initial = rng.uniform(-np.pi, np.pi, size=len(parameters))
    evaluations = 0
    history: list[float] = []
    last_parameters: np.ndarray | None = None
    last_energy: float | None = None

    def objective(values: np.ndarray) -> float:
        nonlocal evaluations, last_parameters, last_energy
        evaluations += 1
        state = Statevector.from_instruction(_bind(circuit, parameters, values))
        last_parameters = np.asarray(values, dtype=float).copy()
        last_energy = float(np.real(state.expectation_value(hamiltonian)))
        return last_energy

    history.append(objective(initial))

    def callback(values: np.ndarray) -> None:
        if last_parameters is not None and np.array_equal(values, last_parameters):
            history.append(float(last_energy))
        else:
            history.append(objective(values))

    result = minimize(
        objective,
        initial,
        method="L-BFGS-B",
        callback=callback,
        options={"maxiter": EXPLORATORY_MAX_ITERATIONS, "ftol": 1e-9, "gtol": 1e-6, "maxls": 24},
    )
    bound = _bind(circuit, parameters, result.x)
    if not history or not np.isclose(history[-1], float(result.fun), atol=1e-12, rtol=0):
        history.append(float(result.fun))
    return bound, {
        "optimizer": "L-BFGS-B",
        "optimizer_success": bool(result.success),
        "optimizer_message": str(result.message),
        "optimizer_iterations": int(result.nit),
        "optimizer_calls": int(evaluations),
        "parameter_count": len(parameters),
        "optimizer_settings": {
            "maxiter": EXPLORATORY_MAX_ITERATIONS,
            "ftol": 1e-9,
            "gtol": 1e-6,
            "maxls": 24,
        },
        "energy_history": history,
    }


def _serialize_statevector(state: Statevector) -> list[list[float]]:
    """Encode complex amplitudes as JSON-safe ``[real, imaginary]`` pairs."""
    return [[float(value.real), float(value.imag)] for value in state.data]


def run_simulation(config: dict[str, Any]) -> dict[str, Any]:
    """Run one exploratory circuit and return measurements and analysis as JSON data.

    The logical circuit is evaluated ideally for statevector and energy metrics,
    then transpiled to a simulator basis. If noise is enabled, Aer also runs a
    pre-measurement density-matrix simulation for noisy ground-state fidelity.
    Counts always come from a separate shot-based run, with readout noise applied
    when requested.
    """
    qubits = int(config["qubits"])
    depth = int(config["depth"])
    g = float(config["g"])
    shots = int(config["shots"])
    seed = int(config["seed"])
    algorithm = str(config["algorithm"])
    zz_mode = str(config["zz_mode"])
    effective_zz_mode = zz_mode if algorithm == "hva-vqe" else "cx"

    diagnostics: dict[str, Any]
    if algorithm == "hva-vqe":
        logical, diagnostics = _hva_state(qubits, depth, g, seed, effective_zz_mode)
    elif algorithm == "random-ry":
        logical = _random_ry_circuit(qubits, depth, seed)
        diagnostics = {
            "optimizer": None,
            "optimizer_success": None,
            "optimizer_message": "No optimizer used for the random circuit.",
            "optimizer_iterations": 0,
            "optimizer_calls": 0,
            "parameter_count": 0,
            "optimizer_settings": None,
            "energy_history": [],
        }
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    hamiltonian = qff.tfim_hamiltonian(qubits, J=1.0, g=g, periodic=False)
    ideal_state = Statevector.from_instruction(logical)
    ideal_energy = float(np.real(ideal_state.expectation_value(hamiltonian)))
    eigenvalues, exact_states = qff.exact_spectrum(hamiltonian, k=1)
    exact_ground = exact_states[0]
    ideal_fidelity = float(state_fidelity(exact_ground, ideal_state))
    observable_ops = qff.observable_ops(qubits)
    ideal_observables = qff.expectations(ideal_state, observable_ops)
    if not diagnostics["energy_history"]:
        diagnostics["energy_history"] = [ideal_energy]

    basis_gates = list(BASE_BASIS_GATES)
    if algorithm == "hva-vqe" and effective_zz_mode == "rzz":
        basis_gates.append("rzz")
    compiled = transpile(
        logical,
        basis_gates=basis_gates,
        optimization_level=2,
        seed_transpiler=seed,
    )
    compiled_state = Statevector.from_instruction(compiled)
    compiled_semantic_fidelity = float(state_fidelity(ideal_state, compiled_state))
    if not np.isclose(compiled_semantic_fidelity, 1.0, atol=1e-10, rtol=0):
        raise RuntimeError(
            f"Transpilation changed the ideal logical state (fidelity={compiled_semantic_fidelity})."
        )
    measurement_circuit = compiled.copy()
    measurement_circuit.measure_all()
    measured = transpile(
        measurement_circuit,
        basis_gates=basis_gates,
        optimization_level=2,
        seed_transpiler=seed,
    )

    noise_enabled = bool(config["noise_enabled"])
    noise_settings = dict(config["noise"])
    uses_rzz = algorithm == "hva-vqe" and effective_zz_mode == "rzz"
    noise_model = _noise_model(noise_settings, include_rzz=uses_rzz) if noise_enabled else None
    simulator_options: dict[str, Any] = {"basis_gates": basis_gates, "seed_simulator": seed}
    if noise_enabled:
        simulator_options["noise_model"] = noise_model
    else:
        simulator_options["method"] = "statevector"
    counts_result = AerSimulator(**simulator_options).run(
        measured, shots=shots, seed_simulator=seed
    ).result()
    raw_counts = counts_result.get_counts(0)
    counts = {str(key).replace(" ", ""): int(value) for key, value in raw_counts.items()}
    probabilities = {
        format(index, f"0{qubits}b"): counts.get(format(index, f"0{qubits}b"), 0) / shots
        for index in range(2**qubits)
    }

    noisy_fidelity: float | None = None
    noisy_observables: dict[str, float] | None = None
    if noise_enabled:
        density_circuit = compiled.copy()
        density_circuit.save_density_matrix(label="rho")
        density_result = AerSimulator(
            method="density_matrix",
            noise_model=noise_model,
            basis_gates=basis_gates,
            seed_simulator=seed,
        ).run(density_circuit, seed_simulator=seed).result()
        density = DensityMatrix(density_result.data(0)["rho"])
        noisy_fidelity = float(state_fidelity(exact_ground, density))
        noisy_observables = qff.expectations(density, observable_ops)

    try:
        qasm = qasm3_dumps(logical)
        qasm_error = None
    except Exception as exc:  # A text circuit is still available if an exporter lacks a gate.
        qasm = None
        qasm_error = f"OpenQASM 3 export unavailable: {type(exc).__name__}: {exc}"

    return {
        "run_kind": "exploratory-local-aer",
        "algorithm": algorithm,
        "qubits": qubits,
        "depth_requested": depth,
        "depth_compiled": int(compiled.depth()),
        "two_qubit_gates": int(sum(compiled.count_ops().get(gate, 0) for gate in ("cx", "cz", "rzz"))),
        "compiled_semantic_fidelity": compiled_semantic_fidelity,
        "g": g,
        "shots": shots,
        "seed": seed,
        "zz_mode": effective_zz_mode,
        "basis_gates": basis_gates,
        "noise_enabled": noise_enabled,
        "noise": noise_settings if noise_enabled else None,
        "counts": counts,
        "probabilities": probabilities,
        "ideal_statevector": _serialize_statevector(ideal_state),
        "ideal_energy": ideal_energy,
        "exact_ground_energy": float(eigenvalues[0]),
        "absolute_energy_error": abs(ideal_energy - float(eigenvalues[0])),
        "ideal_ground_fidelity": ideal_fidelity,
        "noisy_ground_fidelity": noisy_fidelity,
        "ideal_observables": ideal_observables,
        "noisy_observables": noisy_observables,
        "circuit_text": str(compiled.draw(output="text", fold=-1)),
        "openqasm3": qasm,
        "openqasm3_error": qasm_error,
        "noise_scope": "Local Aer synthetic noise; no hardware or processor topology is used.",
        **diagnostics,
    }
