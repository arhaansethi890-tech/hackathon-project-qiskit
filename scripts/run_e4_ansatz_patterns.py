"""Supplementary E4: path/ring/star RY/CX patterns on the fixed A/B graphs.

Uses pre-frozen docs/EXPERIMENT_PLAN.md. This script is never called by the
canonical Stage 1 reproduction pipeline.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from src.ansatz import make_pattern_ansatz
from src.fidelity import reduce_to_logical
from src.measurements import tfim_energy_from_counts
from src.metrics import mean_sd_sem
from src.noise import fixed_noise_model, load_noise_settings
from src.problem import FIELDS, J, N, exact_ground_state
from src.processors import load_processor
from src.randomness import derive_simulator_seed
from src.routing import compile_with_evidence
from src.vqe import run_vqe

SEEDS=(42,7,21)
PATTERNS=('path','ring','star')
SHOTS=4096

def json_safe(value):
    if isinstance(value,dict):return {str(k):json_safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [json_safe(v) for v in value]
    if isinstance(value,(np.integer,)):return int(value)
    if isinstance(value,(np.floating,)):return float(value)
    if isinstance(value,(bool,np.bool_)):return bool(value)
    if value is None or isinstance(value,(str,int,float)):return value
    raise TypeError(f'Not JSON serializable: {type(value).__name__}')

def main():
    (ROOT/'results/supplementary/raw').mkdir(parents=True,exist_ok=True)
    (ROOT/'results/supplementary/tables').mkdir(parents=True,exist_ok=True)
    (ROOT/'results/supplementary/figures').mkdir(parents=True,exist_ok=True)
    prior=json.loads((ROOT/'results/raw/vqe_runs.json').read_text())
    path_map={(float(r['g']),int(r['seed'])):r for r in prior}
    expected={(float(g),s) for g in FIELDS for s in SEEDS}
    if set(path_map)!=expected or len(prior)!=9:
        raise ValueError('Canonical input must contain exactly the nine saved Stage 1 VQE starts.')
    noise_settings=load_noise_settings()
    simulator=AerSimulator(noise_model=fixed_noise_model())
    records=[];raw=[];used_seeds=set()
    for pattern in PATTERNS:
        for g in FIELDS:
            exact_energy,_=exact_ground_state(g)
            for seed in SEEDS:
                if pattern=='path':
                    source=path_map[(float(g),seed)]['result']
                    parameters=np.asarray(source['parameters'],dtype=float)
                    optimizer_success=bool(source['success'])
                    optimizer_message=str(source['message'])
                    optimizer_nit=int(source['nit'])
                    initial_parameters=source['initial_parameters']
                    ideal_energy=float(source['energy'])
                else:
                    result=run_vqe(g,seed=seed,reps=3,pattern=pattern)
                    state=result.pop('state')
                    parameters=np.asarray(result['parameters'],dtype=float)
                    optimizer_success=bool(result['success'])
                    optimizer_message=str(result['message'])
                    optimizer_nit=int(result['nit'])
                    initial_parameters=result['initial_parameters']
                    ideal_energy=float(result['energy'])
                logical=make_pattern_ansatz(parameters,pattern=pattern,reps=3)
                logical_state=Statevector.from_instruction(logical)
                by_arch={}
                for processor_id in ('processor_A','processor_B'):
                    config,coupling=load_processor(ROOT/'processors'/f'{processor_id}.json')
                    compiled,evidence=compile_with_evidence(logical,coupling_map=coupling,
                        basis_gates=config['basis_gates'],optimization_level=1,layout_method='sabre',
                        routing_method='sabre',seed_transpiler=42)
                    if not evidence['instrumented_pipeline_matches_transpile_output']:
                        raise RuntimeError(f'Instrumented compilation mismatch: {pattern=} {g=} {seed=} {processor_id=}')
                    physical=Statevector.from_instruction(compiled).data
                    reduced=reduce_to_logical(np.outer(physical,physical.conj()),evidence['final_layout'],compiled.num_qubits,N)
                    semantic=float(np.vdot(logical_state.data,reduced@logical_state.data).real)
                    if not np.isclose(semantic,1.,atol=1e-9,rtol=0):
                        raise RuntimeError(f'Semantic state check failed: {pattern=} {g=} {seed=} {processor_id=} {semantic=}')
                    counts=compiled.count_ops()
                    row={
                        'study':'E4 supplementary ansatz-pattern comparison','pattern':pattern,
                        'g':float(g),'seed':seed,'architecture':config['name'],
                        'optimizer_success':optimizer_success,'optimizer_message':optimizer_message,'optimizer_nit':optimizer_nit,
                        'logical_energy':ideal_energy,'exact_energy':float(exact_energy),
                        'ideal_signed_error':ideal_energy-float(exact_energy),
                        'ideal_absolute_error':abs(ideal_energy-float(exact_energy)),
                        'ideal_relative_error':abs(ideal_energy-float(exact_energy))/abs(float(exact_energy)),
                        'logical_cx_count':int(logical.count_ops().get('cx',0)),
                        'compiled_cx_count':int(counts.get('cx',0)),'compiled_depth':int(compiled.depth()),
                        'routing_swap_count':len(evidence['routing_swaps']),'routing_swaps':evidence['routing_swaps'],
                        'final_circuit_swap_gate_count':int(counts.get('swap',0)),
                        'initial_layout':evidence['initial_layout'],'final_layout':evidence['final_layout'],
                        'observed_layout_passes':evidence['observed_layout_passes'],
                        'observed_routing_passes':evidence['observed_routing_passes'],
                        'pass_trace':evidence['pass_trace'],'semantic_fidelity':semantic,
                        'topology_status':config['topology_status'],
                        'optimization_level':evidence['optimization_level'],
                        'requested_layout_method':evidence['requested_layout_method'],
                        'requested_routing_method':evidence['requested_routing_method'],
                        'seed_transpiler':evidence['seed_transpiler'],
                        'basis_gates':config['basis_gates'],
                        'routing_swap_pass_evidence':evidence['routing_swap_pass_evidence'],
                        'instrumented_pipeline_matches_transpile_output':evidence['instrumented_pipeline_matches_transpile_output'],
                    }
                    by_arch[processor_id]={'row':row,'config':config,'coupling':coupling}
                # Sample both Pauli groups independently on each physical graph.
                per_pattern_counts={}
                for processor_id,entry in by_arch.items():
                    config=entry['config'];logical_counts={};seed_map={};evidence_map={};resource_map={}
                    for basis in ('Z','X'):
                        circuit=logical.copy();circuit.barrier()
                        if basis=='X':
                            for q in range(N):circuit.h(q)
                        circuit.measure_all()
                        compiled,evidence=compile_with_evidence(circuit,coupling_map=entry['coupling'],
                            basis_gates=config['basis_gates'],optimization_level=1,layout_method='sabre',
                            routing_method='sabre',seed_transpiler=42)
                        if not evidence['instrumented_pipeline_matches_transpile_output']:
                            raise RuntimeError(f'Measurement compilation mismatch: {pattern=} {g=} {seed=} {processor_id=} {basis=}')
                        if set(compiled.count_ops())-set(config['basis_gates'])-{'measure','barrier'}:
                            raise RuntimeError(f'Unsupported compiled operation: {compiled.count_ops()}')
                        variant=f"{noise_settings['variant']}|E4-{pattern}"
                        simseed=derive_simulator_seed(g,seed,config['name'],basis,batch=0,variant=variant)
                        if simseed in used_seeds:raise RuntimeError(f'Duplicate E4 simulator seed {simseed}')
                        used_seeds.add(simseed);seed_map[basis]=simseed;evidence_map[basis]=evidence
                        resource_map[basis]={'cx':int(compiled.count_ops().get('cx',0)),'depth':int(compiled.depth()),
                            'routing_swap_count':len(evidence['routing_swaps']),'routing_swaps':evidence['routing_swaps'],
                            'final_circuit_swap_gate_count':int(compiled.count_ops().get('swap',0))}
                        logical_counts[basis]=simulator.run(compiled,shots=SHOTS,seed_simulator=simseed).result().get_counts()
                    estimate=tfim_energy_from_counts(logical_counts['Z'],logical_counts['X'],g,N,J)
                    row=entry['row']
                    row.update({'noisy_energy':float(estimate['energy']),
                        'noisy_signed_error':float(estimate['energy']-exact_energy),
                        'noisy_absolute_error':abs(float(estimate['energy']-exact_energy)),
                        'noisy_relative_error':abs(float(estimate['energy']-exact_energy))/abs(float(exact_energy)),
                        'noisy_shift_from_ideal':float(estimate['energy']-ideal_energy),
                        'sampled_energy_z':float(estimate['energy_z']),'sampled_energy_x':float(estimate['energy_x']),
                        'shot_sem_z':float(estimate['standard_error_z']),'shot_sem_x':float(estimate['standard_error_x']),
                        'shot_sem':float(estimate['standard_error']),'shots_per_basis':SHOTS,
                        'noise_variant':variant,'noise_model':'same fixed synthetic model as Stage 1; pattern encoded only in simulator-seed derivation',
                        'Z_simulator_seed':seed_map['Z'],'X_simulator_seed':seed_map['X'],
                        'Z_cx_count':resource_map['Z']['cx'],'X_cx_count':resource_map['X']['cx'],
                        'Z_depth':resource_map['Z']['depth'],'X_depth':resource_map['X']['depth'],
                        'Z_routing_swap_count':resource_map['Z']['routing_swap_count'],'X_routing_swap_count':resource_map['X']['routing_swap_count'],
                        'uncertainty_method':'independent Z/X Pauli-group sample SEMs combined in quadrature'})
                    records.append(row)
                    per_pattern_counts[processor_id]={'Z_counts':logical_counts['Z'],'X_counts':logical_counts['X'],
                        'seeds':seed_map,'measurement_compilation':evidence_map}
                for processor_id,entry in by_arch.items():
                    raw.append({'pattern':pattern,'g':float(g),'seed':seed,'architecture':entry['config']['name'],
                        'optimizer_success':optimizer_success,'optimizer_message':optimizer_message,
                        'initial_parameters':initial_parameters,'final_parameters':parameters.tolist(),
                        'logical_energy':ideal_energy,'exact_energy':float(exact_energy),
                        'logical_cx_count':int(logical.count_ops().get('cx',0)),
                        'ideal_compilation':{k:entry['row'][k] for k in ('compiled_cx_count','compiled_depth','routing_swap_count','routing_swaps','final_circuit_swap_gate_count','initial_layout','final_layout','observed_layout_passes','observed_routing_passes','pass_trace','semantic_fidelity','optimization_level','requested_layout_method','requested_routing_method','seed_transpiler','basis_gates','routing_swap_pass_evidence','instrumented_pipeline_matches_transpile_output')}, 
                        'noisy':per_pattern_counts[processor_id]})
    full=pd.DataFrame(records).sort_values(['pattern','g','seed','architecture']).reset_index(drop=True)
    summary=[]
    for (pattern,arch),group in full.groupby(['pattern','architecture'],sort=True):
        out={'pattern':pattern,'architecture':arch,'n_runs':len(group),
            'optimizer_success_count':int(group.drop_duplicates(['g','seed']).optimizer_success.sum()),
            'optimizer_failure_count':int((~group.drop_duplicates(['g','seed']).optimizer_success).sum()),
            'semantic_fidelity_min':float(group.semantic_fidelity.min())}
        for col in ('ideal_absolute_error','compiled_cx_count','compiled_depth','routing_swap_count','noisy_absolute_error','noisy_signed_error','noisy_shift_from_ideal','shot_sem'):
            st=mean_sd_sem(group[col]);out[f'{col}_mean']=st['mean'];out[f'{col}_sample_sd']=st['sample_sd'];out[f'{col}_sem']=st['sem']
        summary.append(out)
    paired=[]
    for pattern in PATTERNS:
        subset=full[full.pattern==pattern]
        wide=subset.pivot(index=['g','seed'],columns='architecture',values='noisy_energy')
        for g in list(FIELDS)+['all']:
            if g=='all':pairs=wide
            else:pairs=wide.loc[float(g)]
            diff=pairs['Processor A_branch']-pairs['Processor B_ref12']
            st=mean_sd_sem(diff)
            paired.append({'pattern':pattern,'g':g,'difference':'A_minus_B','n_pairs':st['n'],
                'mean':st['mean'],'sample_sd':st['sample_sd'],'sem':st['sem'],
                'definition':'sampled A energy minus sampled B energy matched by field and VQE seed'})
    base=ROOT/'results/supplementary'
    full.to_csv(base/'tables/E4_ansatz_patterns.csv',index=False,float_format='%.16g')
    pd.DataFrame(summary).to_csv(base/'tables/E4_pattern_summary.csv',index=False,float_format='%.16g')
    pd.DataFrame(paired).to_csv(base/'tables/E4_paired_differences.csv',index=False,float_format='%.16g')
    (base/'raw/E4_ansatz_pattern_runs.json').write_text(json.dumps(json_safe(raw),indent=2)+'\n')
    print('E4 complete: path/ring/star; 27 pattern-field-start combinations (18 new ring/star optimizations); 54 A/B ideal compilations and 108 noisy basis samples.')
    print(pd.DataFrame(summary)[['pattern','architecture','n_runs','optimizer_success_count','optimizer_failure_count','compiled_cx_count_mean','compiled_depth_mean','routing_swap_count_mean','noisy_absolute_error_mean','shot_sem_mean']].to_string(index=False,float_format=lambda x:f'{x:.8g}'))
    print('Paired A-B noisy-energy differences:')
    print(pd.DataFrame(paired).to_string(index=False,float_format=lambda x:f'{x:.8g}'))
    print(f'Unique E4 simulator seeds: {len(used_seeds)}; expected {len(PATTERNS)*len(FIELDS)*len(SEEDS)*2*2}.')

if __name__=='__main__':main()
