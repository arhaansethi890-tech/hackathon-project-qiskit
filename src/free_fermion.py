"""Independent open-chain TFIM cross-check via the Jordan-Wigner free-fermion form.

After a global Hadamard rotation, -J sum ZZ - g sum X becomes
-J sum XX - g sum Z. Jordan-Wigner Majorana reduction gives a real bidiagonal
single-particle matrix T with diagonal g and subdiagonal J. The many-body ground
energy is -sum(singular_values(T)). For a nondegenerate positive-field ground
state, Hellmann-Feynman gives <sum X_i> = d(-E0)/dg = sum_i u_i^T v_i,
where T = U diag(s) V^T. This does not construct or diagonalize the 2**N spin
Hamiltonian.
"""
import numpy as np


def _validate(g: float, n: int, coupling: float) -> tuple[float, int, float]:
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < 1:
        raise ValueError("n must be a positive integer")
    try:
        field, j = float(g), float(coupling)
    except (TypeError, ValueError) as exc:
        raise ValueError("g and J must be finite real numbers") from exc
    if not np.isfinite(field) or not np.isfinite(j):
        raise ValueError("g and J must be finite")
    return field, int(n), j


def single_particle_matrix(g: float, n: int = 4, J: float = 1.0) -> np.ndarray:
    """Return the N×N bidiagonal Majorana matrix for an open TFIM chain."""
    field, n, j = _validate(g, n, J)
    matrix = np.diag(np.full(n, field, dtype=float))
    if n > 1:
        matrix += np.diag(np.full(n - 1, j, dtype=float), k=-1)
    return matrix


def free_fermion_ground_energy(g: float, n: int = 4, J: float = 1.0) -> float:
    """Ground energy of -J Σ Z_i Z_(i+1) - g Σ X_i for an open chain."""
    singular_values = np.linalg.svd(single_particle_matrix(g, n, J), compute_uv=False)
    return float(-singular_values.sum())


def free_fermion_spectrum(g: float, n: int = 4, J: float = 1.0) -> np.ndarray:
    """Return all 2**N eigenvalues from independent fermionic mode occupations."""
    singular_values = np.linalg.svd(single_particle_matrix(g, n, J), compute_uv=False)
    energies = []
    for mask in range(1 << n):
        excitation = sum(singular_values[i] for i in range(n) if (mask >> i) & 1)
        energies.append(-float(singular_values.sum()) + 2.0 * float(excitation))
    return np.sort(np.asarray(energies, dtype=float))


def free_fermion_x_sum(g: float, n: int = 4, J: float = 1.0) -> float:
    """Return <ΣX_i> from the Hellmann-Feynman derivative for nondegenerate g>0."""
    field, _, _ = _validate(g, n, J)
    if field <= 0:
        raise ValueError("the derivative-based observable is restricted to g > 0")
    u, _, vh = np.linalg.svd(single_particle_matrix(field, n, J), full_matrices=False)
    v = vh.T
    return float(np.sum(u * v))
