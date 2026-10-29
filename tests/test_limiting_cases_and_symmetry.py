import numpy as np
from src.problem import dense_hamiltonian, exact_ground_state, observables, sparse_ground_energy


def test_j_zero_and_g_zero_limits_for_direct_spin_matrices():
    n=4
    assert np.isclose(np.linalg.eigvalsh(dense_hamiltonian(0.0,n=n,coupling=1.0))[0],-3.0)
    for g in (-1.25,0.0,1.25):
        expected=-n*abs(g)
        assert np.isclose(np.linalg.eigvalsh(dense_hamiltonian(g,n=n,coupling=0.0))[0],expected)
        assert np.isclose(sparse_ground_energy(g,n=n,coupling=0.0),expected)


def test_positive_field_ground_state_is_unique_and_z_symmetric():
    x=np.array([[0.,1.],[1.,0.]])
    parity=np.kron(np.kron(np.kron(x,x),x),x)
    for g in (.5,1.0,1.5):
        h=dense_hamiltonian(g)
        values, vectors=np.linalg.eigh(h)
        assert values[1]-values[0]>0.0
        _,state=exact_ground_state(g)
        parity_eigenvalue=float(np.vdot(state,parity@state).real)
        assert np.isclose(abs(parity_eigenvalue),1.0,atol=1e-10)
        assert abs(observables(g)['magnetization_z_sum'])<1e-10
