import numpy as np
from pathlib import Path
from src.fidelity import reduce_to_logical, density_fidelity, simulate_density_fidelity
from src.vqe import run_vqe
from src.noise import fixed_noise_model
ROOT=Path(__file__).resolve().parents[1]

def test_layout_reduction_little_endian_permuted_with_spectator():
    psi=np.array([1,2j,3,4j],dtype=complex);psi=psi/np.linalg.norm(psi)
    # logical q0 -> physical q2; logical q1 -> physical q0; spectator q1 in |+>
    full=np.zeros(8,dtype=complex)
    for i,a in enumerate(psi):
        for s in (0,1):
            idx=(((i>>0)&1)<<2)|(((i>>1)&1)<<0)|(s<<1)
            full[idx]+=a/np.sqrt(2)
    rho=full[:,None]@full.conj()[None,:]
    red=reduce_to_logical(rho,[2,0],3,2)
    assert np.allclose(red,psi[:,None]@psi.conj()[None,:],atol=1e-12)
    assert np.isclose(density_fidelity(psi,red),1,atol=1e-12)

def test_noiseless_density_pipeline_matches_ideal_pure_state():
    v=run_vqe(.5,seed=42,reps=3,maxiter=300)
    r=simulate_density_fidelity(.5,v['parameters'],v['reps'],ROOT/'processors/processor_A.json',noisy=False)
    assert abs(r['fidelity']-r['ideal_vqe_fidelity'])<1e-8
    assert r['rho_physical_shape']==(32,32)
    assert r['logical_to_physical'] and len(r['logical_to_physical'])==4

def test_fixed_noise_gate_coverage_and_readout_sampling_reproducibility():
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    noise=fixed_noise_model()
    assert set(noise.noise_instructions)=={'rz','sx','x','cx','measure'}
    assert 'rz' in noise.noise_instructions
    assert 'rz' not in fixed_noise_model(rz_noiseless=True).noise_instructions
    readout=[e for e in noise.to_dict()['errors'] if e['type']=='roerror']
    assert len(readout)==1
    assert np.allclose(readout[0]['probabilities'],[[0.99,0.01],[0.01,0.99]])
    qc=QuantumCircuit(1);qc.measure_all()
    sim=AerSimulator(noise_model=noise)
    a=sim.run(qc,shots=8192,seed_simulator=42).result().get_counts()
    b=sim.run(qc,shots=8192,seed_simulator=42).result().get_counts()
    assert a==b
    observed=a.get('1',0)/8192
    assert abs(observed-0.01)<0.005

def test_noisy_density_fidelity_is_physical_and_reduced():
    v=run_vqe(.5,seed=42,reps=3,maxiter=300)
    r=simulate_density_fidelity(.5,v['parameters'],v['reps'],ROOT/'processors/processor_A.json',noisy=True)
    rho=r['rho_logical']
    assert rho.shape==(16,16) and np.isclose(np.trace(rho),1,atol=1e-7)
    assert np.allclose(rho,rho.conj().T,atol=1e-8)
    assert np.linalg.eigvalsh(rho).min()>-1e-8
    assert 0<=r['fidelity']<=1
