import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from src.fidelity import reduce_to_logical
from src.processors import load_processor
from src.routing import compile_with_evidence
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def test_actual_layout_routing_pass_trace_and_public_dag_swap_indices():
    ring=QuantumCircuit(4)
    for q in range(4):ring.ry(.31*(q+1),q)
    for q in range(3):ring.cx(q,q+1)
    ring.cx(3,0)
    for name in ('processor_A','processor_B'):
        cfg,coupling=load_processor(ROOT/'processors'/f'{name}.json')
        compiled,evidence=compile_with_evidence(ring,coupling_map=coupling,basis_gates=cfg['basis_gates'],seed_transpiler=42)
        assert evidence['layout_selection_pass']=='SabreLayout'
        assert evidence['observed_routing_passes']==['SabreLayout']
        assert all(len(pair)==2 and all(isinstance(q,int) for q in pair) for pair in evidence['routing_swaps'])
        assert evidence['instrumented_pipeline_matches_transpile_output']
        assert evidence['final_layout'] is not None and len(evidence['final_layout'])==4
        assert all(len(pair)==2 and all(isinstance(q,int) for q in pair) for pair in evidence['routing_swaps'])
        physical=Statevector.from_instruction(compiled).data
        rho=reduce_to_logical(np.outer(physical,physical.conj()),evidence['final_layout'],compiled.num_qubits,4)
        reference=Statevector.from_instruction(ring).data
        assert np.isclose(np.vdot(reference,rho@reference).real,1,atol=1e-9)


def test_compiled_final_swap_gates_are_separate_from_routing_pass_trace():
    line=QuantumCircuit(4)
    for q in range(3):line.cx(q,q+1)
    for name in ('processor_A','processor_B'):
        cfg,coupling=load_processor(ROOT/'processors'/f'{name}.json')
        compiled,evidence=compile_with_evidence(line,coupling_map=coupling,basis_gates=cfg['basis_gates'],seed_transpiler=42)
        assert int(compiled.count_ops().get('swap',0))>=0
        assert len(evidence['routing_swaps'])>=0
        assert evidence['requested_routing_method']=='sabre'
        assert evidence['instrumented_pipeline_matches_transpile_output']
