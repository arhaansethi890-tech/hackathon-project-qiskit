"""Layout-aware density-matrix fidelity tools using Qiskit little-endian subsystem indices."""
import numpy as np
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from .ansatz import make_ansatz
from .noise import fixed_noise_model, load_noise_settings
from .routing import compile_with_evidence
from .processors import load_processor
from .problem import exact_ground_state

def reduce_to_logical(rho_physical, logical_to_physical, n_physical, n_logical=4):
    """Trace spectators and return rho with logical q0 as its least-significant bit.

    `logical_to_physical[i]` is the final physical-wire index holding logical qi.
    Matrix indices follow Qiskit's convention: qubit 0 is least significant.
    """
    rho=np.asarray(rho_physical,dtype=complex)
    if rho.shape!=(2**n_physical,2**n_physical):
        raise ValueError(f'physical density matrix shape {rho.shape} != {(2**n_physical,)*2}')
    mapping=[int(x) for x in logical_to_physical]
    if len(mapping)!=n_logical or len(set(mapping))!=n_logical:
        raise ValueError('logical-to-physical mapping must contain one unique physical wire per logical qubit')
    if any(x<0 or x>=n_physical for x in mapping): raise ValueError('layout contains an out-of-range physical wire')
    spectators=[q for q in range(n_physical) if q not in mapping]
    out=np.zeros((2**n_logical,2**n_logical),dtype=complex)
    for i in range(2**n_logical):
        for j in range(2**n_logical):
            total=0j
            for env in range(2**len(spectators)):
                row=col=0
                for logical_q,physical_q in enumerate(mapping):
                    row |= ((i>>logical_q)&1)<<physical_q
                    col |= ((j>>logical_q)&1)<<physical_q
                for env_q,physical_q in enumerate(spectators):
                    bit=(env>>env_q)&1
                    row |= bit<<physical_q; col |= bit<<physical_q
                total+=rho[row,col]
            out[i,j]=total
    return out

def pure_state_fidelity(exact_state, trial_state):
    a=np.asarray(exact_state,dtype=complex).reshape(-1); b=np.asarray(trial_state,dtype=complex).reshape(-1)
    if a.shape!=b.shape: raise ValueError(f'state dimensions differ: {a.shape} vs {b.shape}')
    na=np.linalg.norm(a); nb=np.linalg.norm(b)
    if not np.isclose(na,1,atol=1e-8) or not np.isclose(nb,1,atol=1e-8): raise ValueError('input statevectors must be normalized')
    return float(abs(np.vdot(a,b))**2)

def density_fidelity(exact_state, rho_logical):
    psi=np.asarray(exact_state,dtype=complex).reshape(-1); rho=np.asarray(rho_logical,dtype=complex)
    if rho.shape!=(psi.size,psi.size): raise ValueError('exact state and logical density dimensions do not match')
    if not np.isclose(np.trace(rho),1,atol=1e-7): raise ValueError('reduced density matrix must have unit trace')
    if not np.allclose(rho,rho.conj().T,atol=1e-8): raise ValueError('density matrix must be Hermitian')
    f=float(np.vdot(psi,rho@psi).real)
    if f < -1e-8 or f > 1+1e-7: raise ValueError(f'fidelity outside physical range: {f}')
    return float(np.clip(f,0,1))

def simulate_density_fidelity(g, parameters, reps, processor_path, noisy=True, seed_transpiler=42, rz_noiseless=None):
    """Simulate a mapped ansatz, trace spectators, and record noise/pass evidence.

    Density-matrix fidelity is pre-measurement; readout error is therefore not
    included in this state-fidelity quantity. It is included in sampled counts.
    """
    cfg,cm=load_processor(processor_path)
    logical=make_ansatz(parameters,reps=reps)
    transpiled,evidence=compile_with_evidence(
        logical,coupling_map=cm,basis_gates=cfg['basis_gates'],optimization_level=1,
        layout_method='sabre',routing_method='sabre',seed_transpiler=seed_transpiler)
    if not evidence['instrumented_pipeline_matches_transpile_output']:
        raise RuntimeError('Instrumented pass-manager output disagrees with qiskit.transpile')
    mapping=evidence['final_layout']
    _,psi_exact=exact_ground_state(g)
    ideal=Statevector.from_instruction(logical).data
    compiled_state=Statevector.from_instruction(transpiled).data
    compiled_rho=reduce_to_logical(np.outer(compiled_state,compiled_state.conj()),mapping,transpiled.num_qubits,logical.num_qubits)
    compiled_semantic_fidelity=density_fidelity(ideal,compiled_rho)
    if not np.isclose(compiled_semantic_fidelity,1.0,atol=1e-9):
        raise RuntimeError(f'Mapped logical state not preserved: fidelity={compiled_semantic_fidelity}')
    selected_noise=(load_noise_settings(rz_noiseless=rz_noiseless) if noisy else {'variant':'noiseless','single_qubit_noisy_gates':[],'rz_noiseless':None})
    simulator=AerSimulator(method='density_matrix',noise_model=fixed_noise_model(rz_noiseless=rz_noiseless) if noisy else None)
    circuit=transpiled.copy();circuit.save_density_matrix()
    result=simulator.run(circuit,seed_simulator=seed_transpiler).result()
    physical=np.asarray(result.data(0)['density_matrix'],dtype=complex)
    rho=reduce_to_logical(physical,mapping,circuit.num_qubits,logical.num_qubits)
    return {'fidelity':density_fidelity(psi_exact,rho),'rho_logical':rho,'rho_physical_shape':physical.shape,
            'logical_to_physical':list(mapping),'physical_qubits':circuit.num_qubits,
            'final_circuit_swap_gate_count':int(transpiled.count_ops().get('swap',0)),
            'transpiled_cx_count':int(transpiled.count_ops().get('cx',0)),
            'transpiled_depth':transpiled.depth(),'compiled_semantic_fidelity':compiled_semantic_fidelity,
            **evidence,'noise_variant':selected_noise['variant'],'noisy':bool(noisy),
            'single_qubit_noisy_gates':selected_noise['single_qubit_noisy_gates'],
            'rz_noiseless':selected_noise['rz_noiseless'],
            'readout_error_applied_to_density_fidelity':False,
            'fidelity_definition':'<psi_exact|rho_logical|psi_exact> after tracing spectator wires; pre-measurement, no readout channel',
            'ideal_vqe_fidelity':pure_state_fidelity(psi_exact,ideal)}
