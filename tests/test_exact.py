import numpy as np
import pytest
from src.problem import dense_hamiltonian, sparse_hamiltonian, exact_ground_state, sparse_ground_energy, sparse_ground_state, sparse_low_energy_eigensystem, observables

ROUNDED={0.5:-3.427034,1.0:-4.758770,1.5:-6.503892}

def test_dimensions_hermiticity_and_terms():
    H=dense_hamiltonian(1.0)
    assert H.shape==(16,16) and np.allclose(H,H.T)
    assert sparse_hamiltonian(1.0).nnz>0

def test_independent_dense_sparse_and_rounded_checks():
    for g, rounded in ROUNDED.items():
        e, v=exact_ground_state(g)
        assert abs(e-sparse_ground_energy(g))<1e-10
        assert abs(e-rounded)<5e-7
        assert np.isclose(np.linalg.norm(v),1)
        es,vs=sparse_ground_state(g)
        assert np.isclose(es,e,atol=1e-10)
        assert abs(np.vdot(v,vs))**2>1-1e-10  # phase-insensitive state overlap

def test_sparse_degenerate_ground_subspace_matches_dense():
    H=dense_hamiltonian(0.0)
    values,vectors=np.linalg.eigh(H)
    basis=vectors[:,np.isclose(values,values[0],atol=1e-12)]
    sparse_values,sparse_vectors=sparse_low_energy_eigensystem(0.0,k=2)
    assert np.allclose(sparse_values,-3.0,atol=1e-12)
    for vector in sparse_vectors.T:
        projection=np.linalg.norm(basis.conj().T@vector)**2
        assert np.isclose(projection,1.0,atol=1e-10)

def test_sparse_eigensolver_handles_completely_degenerate_zero_hamiltonian():
    values,vectors=sparse_low_energy_eigensystem(0.0,k=2,n=4,coupling=0.0)
    assert np.allclose(values,0.0)
    assert vectors.shape==(16,2)
    assert np.allclose(vectors.conj().T@vectors,np.eye(2))

def test_hand_check_one_spin():
    X=np.array([[0.,1.],[1.,0.]])
    for g in (-0.5,0.5):
        H=dense_hamiltonian(g,n=1)
        assert np.allclose(H,-g*X)
        assert np.isclose(np.linalg.eigvalsh(H)[0],-abs(g))
        assert np.isclose(sparse_ground_energy(g,n=1),-abs(g))

def test_open_chain_zero_field_and_dense_sparse_matrices():
    # At g=0 an open four-site ferromagnetic chain has three bonds and two ground states.
    H=dense_hamiltonian(0.0)
    assert np.allclose(H,np.diag(np.diag(H)))
    eig=np.linalg.eigvalsh(H)
    assert np.isclose(eig[0],-3.0) and np.count_nonzero(np.isclose(eig,-3.0))==2
    assert np.isclose(sparse_ground_energy(0.0),-3.0)
    for g in (0.0,0.5,1.0,1.5):
        assert np.allclose(dense_hamiltonian(g),sparse_hamiltonian(g).toarray(),atol=1e-13)

def test_qiskit_pauli_strings_and_coefficients_are_explicit():
    from src.qiskit_problem import tfim_operator
    terms=dict(tfim_operator(0.5).to_list())
    assert set(terms)=={'ZZII','IZZI','IIZZ','XIII','IXII','IIXI','IIIX'}
    for label in ('ZZII','IZZI','IIZZ'):
        assert terms[label]==-1.0
    for label in ('XIII','IXII','IIXI','IIIX'):
        assert terms[label]==-0.5

def test_invalid_chain_parameters_fail_clearly():
    for n in (0,-1,1.5,True):
        with pytest.raises(ValueError): dense_hamiltonian(1.0,n=n)
    for g in (float('nan'),float('inf'),-float('inf')):
        with pytest.raises(ValueError): sparse_hamiltonian(g)

def test_qiskit_count_bit_order_and_magnetization_error_estimate():
    import pytest
    from src.measurements import expand_counts,spin_sum_estimate
    counts={'00':2,'01':1}
    samples=expand_counts(counts,2)
    assert samples.tolist()==[[0,0],[0,0],[1,0]]  # columns are c0 then c1
    mean,se=spin_sum_estimate(counts,2)
    assert mean==pytest.approx(4/3)
    assert se>0
    with pytest.raises(ValueError): expand_counts({'0x':2},2)
    with pytest.raises(ValueError): expand_counts({'00':0},2)

def test_z_magnetization_symmetry_and_observables():
    from functools import reduce
    X=np.array([[0.,1.],[1.,0.]])
    P=reduce(np.kron,[X]*4)
    Z=np.diag([1.,-1.]);I=np.eye(2)
    Mz=sum(np.kron(np.kron(np.kron(I if i!=3 else Z,I if i!=2 else Z),I if i!=1 else Z),I if i!=0 else Z) for i in range(4))
    for g in (0.5,1.,1.5):
        H=dense_hamiltonian(g)
        assert np.allclose(P@H@P,H,atol=1e-12)
        assert np.allclose(P@Mz@P,-Mz,atol=1e-12)
        o=observables(g)
        assert abs(o['magnetization_z_sum'])<1e-10
        assert len(o['zz_bonds'])==3
        assert len(o['z_sites'])==4 and len(o['x_sites'])==4
        assert np.isclose(sum(o['z_sites']),o['magnetization_z_sum'])
        assert np.isclose(sum(o['x_sites']),o['magnetization_x_sum'])
