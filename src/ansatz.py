"""RY hardware-efficient ansatz and explicit topology-pattern variants."""
import numpy as np
from qiskit import QuantumCircuit

PATTERN_EDGES = {
    "path": ((0, 1), (1, 2), (2, 3)),
    "ring": ((0, 1), (1, 2), (2, 3), (3, 0)),
    "star": ((0, 1), (0, 2), (0, 3)),
}

def parameter_count(n=4, reps=2):
    return (reps + 1) * n

def make_pattern_ansatz(params, pattern="path", n=4, reps=3):
    """Build a four-layer RY ansatz with three repeated entangler sweeps by default."""
    if n != 4:
        raise ValueError("the defined S1 patterns are four-qubit circuits")
    if pattern not in PATTERN_EDGES:
        raise ValueError(f"unknown pattern {pattern!r}; choose {tuple(PATTERN_EDGES)}")
    x = np.asarray(params, dtype=float).reshape(-1)
    expected = parameter_count(n, reps)
    if x.size != expected or not np.isfinite(x).all():
        raise ValueError(f"params must contain exactly {expected} finite values")
    qc = QuantumCircuit(n)
    p = x.reshape(reps + 1, n)
    for layer in range(reps + 1):
        for q in range(n):
            qc.ry(float(p[layer, q]), q)
        if layer < reps:
            for control, target in PATTERN_EDGES[pattern]:
                qc.cx(control, target)
    return qc

def make_ansatz(params, n=4, reps=2):
    """Historical default remains reps=2; core S1 explicitly selects reps=3."""
    return make_pattern_ansatz(params, "path", n=n, reps=reps)
