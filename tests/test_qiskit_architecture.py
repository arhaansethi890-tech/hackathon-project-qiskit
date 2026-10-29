import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from qiskit import transpile
from qiskit.quantum_info import Statevector

from src.ansatz import make_ansatz
from src.fidelity import reduce_to_logical
from src.measurements import expand_counts
from src.problem import dense_hamiltonian, exact_ground_state, state_observables
from src.processors import load_processor
from src.qiskit_problem import tfim_operator
from src.vqe import parameter_shift_gradient, run_vqe

ROOT=Path(__file__).resolve().parents[1]
A={(0,1),(1,2),(1,3),(3,4)}
B={(0,1),(1,2),(1,6),(2,3),(2,6),(2,5),(3,4),(4,5),(5,6),(6,7),(6,8),(0,8)}


def test_seven_pauli_terms_and_qiskit_label_order_match_independent_dense_matrix():
    for g in (.5,1.,1.5):
        op=tfim_operator(g)
        assert len(op)==7
        assert np.allclose(op.to_matrix(),dense_hamiltonian(g),atol=1e-12)
        assert np.allclose(np.linalg.eigvalsh(op.to_matrix()),np.linalg.eigvalsh(dense_hamiltonian(g)),atol=1e-12)
    terms={label:float(coeff.real) for label,coeff in tfim_operator(1.).to_list()}
    assert terms=={'IIZZ':-1.,'IZZI':-1.,'ZZII':-1.,'IIIX':-1.,'IIXI':-1.,'IXII':-1.,'XIII':-1.}
    terms_g={label:float(coeff.real) for label,coeff in tfim_operator(.5).to_list()}
    assert all(terms_g[k]==-.5 for k in ('IIIX','IIXI','IXII','XIII'))


def test_pre_registered_A_B_graphs_and_common_model():
    for proc, n, expected in [('processor_A',5,A),('processor_B',9,B)]:
        config,coupling=load_processor(ROOT/'processors'/f'{proc}.json')
        assert config['qubit_count']==n and coupling.size()==n
        assert {tuple(sorted(edge)) for edge in config['edges']}==expected
        assert config['basis_gates']==['rz','sx','x','cx']
        assert config['noise_model']['single_qubit_depolarizing_p']==.001
        assert config['noise_model']['cx_depolarizing_p']==.005
        assert config['noise_model']['readout_error_matrix']==[[.99,.01],[.01,.99]]
    assert ROOT.joinpath('processors/processor_A.json').exists()
    assert ROOT.joinpath('processors/processor_B.json').exists()


def test_processor_loader_rejects_invalid_topologies(tmp_path):
    for i,config in enumerate([
        {'name':'duplicate','qubit_count':2,'edges':[[0,1],[1,0]]},
        {'name':'range','qubit_count':2,'edges':[[0,2]]},
        {'name':'disconnected','qubit_count':3,'edges':[[0,1]]},
        {'name':'empty','qubit_count':2,'edges':[]},
    ]):
        path=tmp_path/f'{i}.json';path.write_text(json.dumps(config))
        with pytest.raises(ValueError): load_processor(path)


def test_compiled_A_B_circuits_preserve_logical_state_and_basis():
    params=np.linspace(-.23,.31,16)
    logical=make_ansatz(params,reps=3)
    reference=Statevector.from_instruction(logical).data
    for name in ('processor_A','processor_B'):
        cfg,cm=load_processor(ROOT/'processors'/f'{name}.json')
        compiled=transpile(logical,coupling_map=cm,basis_gates=cfg['basis_gates'],optimization_level=1,
                           layout_method='sabre',routing_method='sabre',seed_transpiler=42)
        assert set(compiled.count_ops()).issubset(set(cfg['basis_gates'])|{'barrier'})
        assert all(cm.graph.has_edge(*(compiled.find_bit(q).index for q in inst.qubits))
                   for inst in compiled.data if inst.operation.name=='cx')
        physical=Statevector.from_instruction(compiled).data
        mapping=compiled.layout.final_index_layout()[:logical.num_qubits]
        reduced=reduce_to_logical(np.outer(physical,physical.conj()),mapping,compiled.num_qubits,logical.num_qubits)
        assert np.allclose(reduced,np.outer(reference,reference.conj()),atol=1e-9)


def test_transpiled_measurements_keep_classical_bit_order():
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    qc=QuantumCircuit(4);qc.x(0);qc.measure_all()
    for name in ('processor_A','processor_B'):
        cfg,cm=load_processor(ROOT/'processors'/f'{name}.json')
        compiled=transpile(qc,coupling_map=cm,basis_gates=cfg['basis_gates'],optimization_level=1,
                           layout_method='sabre',routing_method='sabre',seed_transpiler=42)
        counts=AerSimulator().run(compiled,shots=64,seed_simulator=42).result().get_counts()
        bits=expand_counts(counts,4)
        assert bits.shape==(64,4) and np.all(bits[:,0]==1) and np.all(bits[:,1:]==0)


def test_vqe_is_deterministic_and_reports_all_requested_state_observables():
    a=run_vqe(.5,seed=42);b=run_vqe(.5,seed=42)
    assert a['energy']==b['energy'] and a['initial_parameters']==b['initial_parameters']
    assert a['optimizer']=='L-BFGS-B' and a['reps']==3 and len(a['parameters'])==16
    ref,exact=exact_ground_state(.5)
    assert abs(a['energy']-ref)<1e-6
    got=state_observables(a['state'].data); expected=state_observables(exact)
    assert set(got)=={'Mz_per_site','Mx_per_site','Mz2_normalized','zz_correlators','z_sites','x_sites'}
    assert np.allclose([got[k] for k in ('Mz_per_site','Mx_per_site','Mz2_normalized')],
                       [expected[k] for k in ('Mz_per_site','Mx_per_site','Mz2_normalized')],atol=1e-5)
    assert len(got['zz_correlators'])==3


def test_parameter_shift_gradient_matches_finite_difference():
    H=tfim_operator(.7);x=np.linspace(-.19,.22,16)
    def objective(p):return float(Statevector.from_instruction(make_ansatz(p,reps=3)).expectation_value(H).real)
    exact=parameter_shift_gradient(objective,x);h=1e-6;finite=np.empty_like(x)
    for i in range(x.size):
        p=x.copy();m=x.copy();p[i]+=h;m[i]-=h;finite[i]=(objective(p)-objective(m))/(2*h)
    assert np.allclose(exact,finite,atol=2e-8,rtol=2e-7)


def test_fresh_noisy_table_is_controlled_and_keeps_error_components_distinct():
    d=pd.read_csv(ROOT/'results/tables/noisy_results.csv')
    assert len(d)==18 and set(d.architecture)=={'Processor A_branch','Processor B_ref12'}
    assert set(d.g)=={.5,1.,1.5} and set(d.seed)=={42,7,21}
    assert (d.shots==4096).all()
    assert d[['initialization_seed','transpiler_seed','Z_simulator_seed','X_simulator_seed']].notna().all().all()
    assert d.Z_simulator_seed.nunique()==18 and d.X_simulator_seed.nunique()==18
    assert not set(d.Z_simulator_seed)&set(d.X_simulator_seed)
    assert (d.standard_error>0).all()
    assert np.allclose(d.noisy_shift_from_ideal,d.objective_or_accuracy-d.ideal_variational_energy)
    assert np.allclose(d.total_noisy_error_signed,d.objective_or_accuracy-d.classical_reference)
    assert {'Mz_per_site','Mx_per_site','Mz2_normalized','ZZ_0_1','ZZ_1_2','ZZ_2_3'}<=set(d.columns)


def test_fresh_ideal_results_keep_original_failure_and_architecture_evidence():
    d=pd.read_csv(ROOT/'results/tables/ideal_architecture_results.csv')
    assert len(d)==27 and set(d.architecture)=={'ideal logical','Processor A_branch','Processor B_ref12'}
    assert (d.variational_parameters==16).all()
    physical=d[d.architecture!='ideal logical']
    assert (physical.optimization_level==1).all() and (physical.seed_transpiler==42).all()
    assert physical.instrumented_pipeline_matches_transpile_output.astype(str).str.lower().eq('true').all()
    failed=d[(d.architecture=='ideal logical')&(d.g==1.5)&(d.seed==42)].iloc[0]
    assert str(failed.vqe_success).lower()=='false' and failed.approximation_or_error>1e-6
    assert failed.optimizer_outcome_classification=='optimizer_failure_or_iteration_limit'

def test_noninduced_motif_placements_collapse_automorphisms_and_graph_descriptors():
    from src.graph_analysis import graph_summary,motif_placements
    ca=json.loads((ROOT/'processors/processor_A.json').read_text())
    cb=json.loads((ROOT/'processors/processor_B.json').read_text())
    assert motif_placements(ca['qubit_count'],ca['edges'])=={'P4':2,'C4':0,'K1,3':1}
    assert motif_placements(cb['qubit_count'],cb['edges'])=={'P4':47,'C4':3,'K1,3':16}
    a=graph_summary(ca['qubit_count'],ca['edges']);b=graph_summary(cb['qubit_count'],cb['edges'])
    assert a['is_tree'] and a['diameter']==3 and a['edges']==4
    assert not b['is_tree'] and b['diameter']==4 and b['edges']==12
