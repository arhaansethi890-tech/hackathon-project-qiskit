import numpy as np
import pytest

from src.free_fermion import (
    free_fermion_ground_energy,
    free_fermion_spectrum,
    free_fermion_x_sum,
)
from src.problem import dense_hamiltonian, exact_ground_state, observables

@pytest.mark.parametrize('g', [0.5, 1.0, 1.5])
def test_free_fermion_energy_spectrum_and_x_observable_independently_match_spin_matrix(g):
    spin_spectrum=np.linalg.eigvalsh(dense_hamiltonian(g))
    fermion_spectrum=free_fermion_spectrum(g)
    assert np.max(np.abs(spin_spectrum-fermion_spectrum)) < 1e-10
    assert abs(free_fermion_ground_energy(g)-exact_ground_state(g)[0]) < 1e-10
    assert abs(free_fermion_x_sum(g)-observables(g)['magnetization_x_sum']) < 1e-10


def test_free_fermion_limiting_cases():
    assert free_fermion_ground_energy(0.0, n=4, J=1.0) == pytest.approx(-3.0, abs=1e-12)
    assert free_fermion_ground_energy(0.0, n=4, J=0.0) == pytest.approx(0.0, abs=1e-12)
    assert free_fermion_ground_energy(1.25, n=4, J=0.0) == pytest.approx(-5.0, abs=1e-12)
    assert free_fermion_ground_energy(-1.25, n=4, J=0.0) == pytest.approx(-5.0, abs=1e-12)
    assert free_fermion_ground_energy(0.7, n=1, J=99.0) == pytest.approx(-0.7, abs=1e-12)


def test_free_fermion_x_sum_rejects_degenerate_derivative_point():
    with pytest.raises(ValueError, match='g > 0'):
        free_fermion_x_sum(0.0)
