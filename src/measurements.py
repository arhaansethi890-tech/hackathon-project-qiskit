"""Validated helpers for decoding Qiskit counts and estimating spin observables."""
from collections.abc import Mapping
import numpy as np


def expand_counts(counts: Mapping[str, int], n_qubits: int) -> np.ndarray:
    """Expand Qiskit count keys into rows ordered by logical classical bit (bit 0 first).

    Qiskit prints the highest-index classical bit on the left. Removing register
    separators and reversing each key therefore yields c0, c1, ... in columns.
    This is appropriate for circuits that explicitly measure logical qubit i into
    classical bit i (as `measure_all()` does before transpilation).
    """
    if isinstance(n_qubits, bool) or not isinstance(n_qubits, int) or n_qubits < 1:
        raise ValueError("n_qubits must be a positive integer")
    if not isinstance(counts, Mapping) or not counts:
        raise ValueError("counts must be a non-empty mapping")
    rows=[]
    for key, count in counts.items():
        bits=str(key).replace(" ", "")
        if len(bits)!=n_qubits or any(bit not in "01" for bit in bits):
            raise ValueError(f"count key {key!r} must contain exactly {n_qubits} binary digits")
        if isinstance(count, bool) or not isinstance(count, (int, np.integer)) or count < 0:
            raise ValueError(f"count for {key!r} must be a non-negative integer")
        if count:
            rows.extend([[int(bit) for bit in bits[::-1]]]*int(count))
    if not rows:
        raise ValueError("counts contain no measured shots")
    return np.asarray(rows,dtype=np.int8)


def tfim_energy_from_counts(z_counts: Mapping[str, int], x_counts: Mapping[str, int], g: float, n_qubits: int = 4, J: float = 1.0) -> dict:
    """Estimate open-chain TFIM energy and independent-group standard errors.

    `z_counts` are Z-basis outcomes; `x_counts` follow Hadamard basis changes.
    Independent simulator streams are required because the combined SE uses
    quadrature and assumes the Z and X group estimates are independent.
    """
    field=float(g); coupling=float(J)
    if not np.isfinite(field) or not np.isfinite(coupling):
        raise ValueError("g and J must be finite")
    z_bits=expand_counts(z_counts,n_qubits)
    x_bits=expand_counts(x_counts,n_qubits)
    z_spins=1-2*z_bits.astype(np.int16)
    x_spins=1-2*x_bits.astype(np.int16)
    z_per_shot=-coupling*np.sum(z_spins[:,:-1]*z_spins[:,1:],axis=1,dtype=np.int64)
    x_per_shot=-field*np.sum(x_spins,axis=1,dtype=np.int64)
    if z_per_shot.size<2 or x_per_shot.size<2:
        raise ValueError("each basis group requires at least two shots for a standard error")
    z_mean=float(z_per_shot.mean()); x_mean=float(x_per_shot.mean())
    z_se=float(z_per_shot.std(ddof=1)/np.sqrt(z_per_shot.size))
    x_se=float(x_per_shot.std(ddof=1)/np.sqrt(x_per_shot.size))
    return {
        "energy":z_mean+x_mean,
        "energy_z":z_mean,
        "energy_x":x_mean,
        "standard_error_z":z_se,
        "standard_error_x":x_se,
        "standard_error":float(np.hypot(z_se,x_se)),
        "shots_z":int(z_per_shot.size),
        "shots_x":int(x_per_shot.size),
        "independence_assumption":"independent simulator seeds by basis; combined standard error is quadrature",
    }


def observable_estimates_from_counts(counts: Mapping[str, int], n_qubits: int, basis: str) -> dict:
    """Per-shot estimates and standard errors for commuting Z or X observables."""
    basis=basis.upper()
    if basis not in {"Z","X"}:raise ValueError("basis must be 'Z' or 'X'")
    bits=expand_counts(counts,n_qubits);spins=1-2*bits.astype(np.int16);nshots=len(spins)
    mean=lambda a:float(np.mean(a))
    sem=lambda a:float(np.std(a,ddof=1)/np.sqrt(nshots)) if nshots>1 else float("nan")
    symbol="Mz" if basis=="Z" else "Mx"
    result={f"{symbol}_per_site":mean(spins.mean(axis=1)),f"{symbol}_per_site_se":sem(spins.mean(axis=1)),"shots":nshots}
    if basis=="Z":
        per_shot_m2=(spins.sum(axis=1)/n_qubits)**2
        result["Mz2_normalized"]=mean(per_shot_m2);result["Mz2_normalized_se"]=sem(per_shot_m2)
        for i in range(n_qubits-1):
            pair=spins[:,i]*spins[:,i+1]
            result[f"ZZ_{i}_{i+1}"]=mean(pair);result[f"ZZ_{i}_{i+1}_se"]=sem(pair)
    return result

def spin_sum_estimate(counts: Mapping[str, int], n_qubits: int) -> tuple[float, float]:
    """Return (sum_i <Z_i>, standard error) for the measured basis.

    For an X-basis circuit, first apply Hadamard gates, then these decoded bits
    represent X outcomes. The returned sum is in that rotated measurement basis.
    """
    bits=expand_counts(counts,n_qubits)
    per_shot=np.sum(1-2*bits,axis=1,dtype=np.int64)
    se=float(per_shot.std(ddof=1)/np.sqrt(per_shot.size)) if per_shot.size>1 else float("nan")
    return float(per_shot.mean()),se
