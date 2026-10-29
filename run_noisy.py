"""Run independent-seed, 4096-shot noisy measurements for every saved VQE trial."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Statevector

from src.ansatz import make_ansatz
from src.measurements import observable_estimates_from_counts, spin_sum_estimate, tfim_energy_from_counts
from src.noise import fixed_noise_model, load_noise_settings
from src.problem import FIELDS, J, N, exact_ground_state, state_observables
from src.processors import load_processor
from src.randomness import derive_simulator_seed
from src.routing import compile_with_evidence

ROOT=Path(__file__).resolve().parent
SHOTS=4096


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--variant',choices=['kit-literal','project-rz-noiseless'],default='kit-literal')
    args=parser.parse_args()
    rz_noiseless=args.variant=='project-rz-noiseless'
    settings=load_noise_settings(rz_noiseless=rz_noiseless)
    simulator=AerSimulator(noise_model=fixed_noise_model(rz_noiseless=rz_noiseless))
    runs=json.loads((ROOT/'results/raw/vqe_runs.json').read_text())
    vqe={(float(run['g']),int(run['seed'])):run for run in runs}
    expected={(float(g),seed) for g in FIELDS for seed in (42,7,21)}
    if set(vqe)!=expected or len(runs)!=len(expected):
        raise ValueError(f"VQE input runs incomplete or duplicated: expected {len(expected)}, found {len(runs)}")

    rows=[]; raw=[]; seen_seeds=set()
    for g in FIELDS:
        reference,exact_state=exact_ground_state(g)
        exact_observables=state_observables(exact_state)
        for vqe_seed in (42,7,21):
            run=vqe[(float(g),vqe_seed)]; result=run['result']
            logical=make_ansatz(result['parameters'],reps=result['reps'])
            ideal_state=Statevector.from_instruction(logical)
            ideal_observables=state_observables(ideal_state.data)
            counts_by_basis={}; evidence_by_basis={}; circuit_by_basis={}; sim_seeds={}
            for basis in ('Z','X'):
                circuit=logical.copy()
                circuit.barrier()
                if basis=='X':
                    for q in range(N): circuit.h(q)
                circuit.measure_all()
                for processor_id in ('processor_A','processor_B'):
                    config_path=ROOT/'processors'/f'{processor_id}.json'
                    config,coupling=load_processor(config_path)
                    compiled,evidence=compile_with_evidence(
                        circuit,coupling_map=coupling,basis_gates=config['basis_gates'],
                        optimization_level=1,layout_method='sabre',routing_method='sabre',seed_transpiler=42)
                    if not evidence['instrumented_pipeline_matches_transpile_output']:
                        raise RuntimeError(f"Instrumented/API transpilation mismatch: {config['name']} g={g} {basis}")
                    if set(compiled.count_ops())-set(config['basis_gates'])-{'measure','barrier'}:
                        raise RuntimeError(f"Compiled circuit has unsupported operations: {compiled.count_ops()}")
                    seed=derive_simulator_seed(g,vqe_seed,config['name'],basis,batch=0,variant=settings['variant'])
                    if seed in seen_seeds:
                        raise RuntimeError(f"Aer seed collision for {g=} {vqe_seed=} {config['name']=} {basis=}: {seed}")
                    seen_seeds.add(seed); sim_seeds[(config['name'],basis)]=seed
                    counts=simulator.run(compiled,shots=SHOTS,seed_simulator=seed).result().get_counts()
                    counts_by_basis[(config['name'],basis)]=counts
                    evidence_by_basis[(config['name'],basis)]=evidence
                    circuit_by_basis[(config['name'],basis)]=compiled
            for processor_id in ('processor_A','processor_B'):
                config,_=load_processor(ROOT/'processors'/f'{processor_id}.json')
                name=config['name']
                zcounts=counts_by_basis[(name,'Z')]; xcounts=counts_by_basis[(name,'X')]
                estimate=tfim_energy_from_counts(zcounts,xcounts,g,N,J)
                mz,mz_se=spin_sum_estimate(zcounts,N)
                mx,mx_se=spin_sum_estimate(xcounts,N)
                zobs=observable_estimates_from_counts(zcounts,N,'Z')
                xobs=observable_estimates_from_counts(xcounts,N,'X')
                cz=circuit_by_basis[(name,'Z')]; cx=circuit_by_basis[(name,'X')]
                ze=evidence_by_basis[(name,'Z')]; xe=evidence_by_basis[(name,'X')]
                row={
                    'model_status':'PS-S1 simulation; October 14, 2026 Master Guide verified',
                    'problem_id':'S1','instance_id':f'g={g}','g':float(g),'seed':vqe_seed,'initialization_seed':vqe_seed,
                    'architecture':name,'logical_qubits':N,'physical_qubits':config['qubit_count'],
                    'topology_status':config['topology_status'],
                    'objective_or_accuracy':estimate['energy'],'classical_reference':reference,
                    'approximation_or_error':abs(estimate['energy']-reference),
                    'ideal_variational_energy':float(result['energy']),
                    'ideal_variational_error_signed':float(result['energy']-reference),
                    'ideal_variational_error_absolute':abs(float(result['energy']-reference)),
                    'noisy_shift_from_ideal':float(estimate['energy']-result['energy']),
                    'total_noisy_error_signed':float(estimate['energy']-reference),
                    'total_noisy_error_absolute':abs(float(estimate['energy']-reference)),
                    'relative_energy_error':abs(estimate['energy']-reference)/abs(reference),
                    'standard_error':estimate['standard_error'],
                    'standard_error_z':estimate['standard_error_z'],'standard_error_x':estimate['standard_error_x'],
                    'sampled_energy_z':estimate['energy_z'],'sampled_energy_x':estimate['energy_x'],
                    'magnetization_z_sum':mz,'magnetization_z_sum_se':mz_se,
                    'magnetization_x_sum':mx,'magnetization_x_sum_se':mx_se,
                    'Mz_per_site':zobs['Mz_per_site'],'Mz_per_site_se':zobs['Mz_per_site_se'],
                    'Mx_per_site':xobs['Mx_per_site'],'Mx_per_site_se':xobs['Mx_per_site_se'],
                    'Mz2_normalized':zobs['Mz2_normalized'],'Mz2_normalized_se':zobs['Mz2_normalized_se'],
                    **{k:v for k,v in zobs.items() if k.startswith('ZZ_')},
                    **{f'exact_{k}':v for k,v in exact_observables.items() if k not in ('z_sites','x_sites')},
                    **{f'vqe_{k}':v for k,v in ideal_observables.items() if k not in ('z_sites','x_sites')},
                    **{f'noisy_{k}':v for k,v in {**zobs,**xobs}.items() if k in ('Mz_per_site','Mx_per_site','Mz2_normalized','ZZ_0_1','ZZ_1_2','ZZ_2_3')},
                    **{f'noisy_error_{k}':v-exact_observables[k] for k,v in {**zobs,**xobs}.items() if k in exact_observables and k not in ('z_sites','x_sites')},
                    **{f'exact_ZZ_{i}_{i+1}':v for i,v in enumerate(exact_observables['zz_correlators'])},
                    **{f'vqe_ZZ_{i}_{i+1}':v for i,v in enumerate(ideal_observables['zz_correlators'])},
                    **{f'noisy_ZZ_{i}_{i+1}':zobs[f'ZZ_{i}_{i+1}'] for i in range(N-1)},
                    **{f'noisy_error_ZZ_{i}_{i+1}':zobs[f'ZZ_{i}_{i+1}']-exact_observables['zz_correlators'][i] for i in range(N-1)},
                    'fidelity':'Not available from Pauli samples',
                    'variational_parameters':len(result['parameters']),
                    'cx_count':int(cz.count_ops().get('cx',0)),'depth':int(cz.depth()),
                    'swap_count':len(ze['routing_swaps']),'routing_swaps':ze['routing_swaps'],
                    'final_circuit_swap_gate_count':int(cz.count_ops().get('swap',0)),
                    'initial_layout':ze['initial_layout'],'final_layout':ze['final_layout'],
                    'Z_initial_layout':ze['initial_layout'],'X_initial_layout':xe['initial_layout'],
                    'Z_final_layout':ze['final_layout'],'X_final_layout':xe['final_layout'],
                    'Z_routing_swaps':ze['routing_swaps'],'X_routing_swaps':xe['routing_swaps'],
                    'shots':SHOTS,'noise_variant':settings['variant'],
                    'noise_model':f"single-qubit p={settings['single_qubit_depolarizing_p']} on {','.join(settings['single_qubit_noisy_gates'])}; CX p={settings['cx_depolarizing_p']}; readout symmetric p={settings['readout_flip_probability']}",
                    'noise_single_qubit_gates':settings['single_qubit_noisy_gates'],
                    'noise_rz_noiseless':settings['rz_noiseless'],
                    'transpiler_seed':42,'optimization_level':1,
                    'requested_layout_method':'sabre','requested_routing_method':'sabre',
                    'layout_selection_pass':ze['layout_selection_pass'],'routing_pass':ze['routing_pass'],
                    'Z_layout_selection_pass':ze['layout_selection_pass'],'X_layout_selection_pass':xe['layout_selection_pass'],
                    'pass_trace':ze['pass_trace'],'Z_pass_trace':ze['pass_trace'],'X_pass_trace':xe['pass_trace'],
                    'instrumented_pipeline_matches_transpile_output':ze['instrumented_pipeline_matches_transpile_output'] and xe['instrumented_pipeline_matches_transpile_output'],
                    'Z_instrumented_match':ze['instrumented_pipeline_matches_transpile_output'],
                    'X_instrumented_match':xe['instrumented_pipeline_matches_transpile_output'],
                    'Z_simulator_seed':sim_seeds[(name,'Z')],'X_simulator_seed':sim_seeds[(name,'X')],
                    'energy_error_definition':'absolute sampled energy difference from exact reference',
                    'uncertainty_method':'per-shot Pauli-group sample SEM; independent Z/X simulator seeds; combined in quadrature',
                }
                rows.append(row)
                raw.append({
                    **{key:row[key] for key in ('model_status','g','seed','architecture','noise_variant','shots','Z_simulator_seed','X_simulator_seed')},
                    'Z_counts':zcounts,'X_counts':xcounts,
                    'sampled_energy_z':estimate['energy_z'],'sampled_energy_x':estimate['energy_x'],
                    'standard_error_z':estimate['standard_error_z'],'standard_error_x':estimate['standard_error_x'],
                    'standard_error':estimate['standard_error'],
                    'magnetization_z_sum':mz,'magnetization_z_sum_se':mz_se,
                    'magnetization_x_sum':mx,'magnetization_x_sum_se':mx_se,
                    'Mz_per_site':zobs['Mz_per_site'],'Mz_per_site_se':zobs['Mz_per_site_se'],
                    'Mx_per_site':xobs['Mx_per_site'],'Mx_per_site_se':xobs['Mx_per_site_se'],
                    'Mz2_normalized':zobs['Mz2_normalized'],'Mz2_normalized_se':zobs['Mz2_normalized_se'],
                    **{k:v for k,v in zobs.items() if k.startswith('ZZ_')},
                    **{f'exact_{k}':v for k,v in exact_observables.items() if k not in ('z_sites','x_sites')},
                    **{f'vqe_{k}':v for k,v in ideal_observables.items() if k not in ('z_sites','x_sites')},
                    **{f'noisy_{k}':v for k,v in {**zobs,**xobs}.items() if k in ('Mz_per_site','Mx_per_site','Mz2_normalized','ZZ_0_1','ZZ_1_2','ZZ_2_3')},
                    **{f'noisy_error_{k}':v-exact_observables[k] for k,v in {**zobs,**xobs}.items() if k in exact_observables and k not in ('z_sites','x_sites')},
                    **{f'exact_ZZ_{i}_{i+1}':v for i,v in enumerate(exact_observables['zz_correlators'])},
                    **{f'vqe_ZZ_{i}_{i+1}':v for i,v in enumerate(ideal_observables['zz_correlators'])},
                    **{f'noisy_ZZ_{i}_{i+1}':zobs[f'ZZ_{i}_{i+1}'] for i in range(N-1)},
                    **{f'noisy_error_ZZ_{i}_{i+1}':zobs[f'ZZ_{i}_{i+1}']-exact_observables['zz_correlators'][i] for i in range(N-1)},
                    'Z_compilation':ze,'X_compilation':xe,
                })

    suffix='' if args.variant=='kit-literal' else '_rz_virtual'
    table=ROOT/'results/tables'/f'noisy_results{suffix}.csv'
    rawfile=ROOT/'results/raw'/f'noisy_counts{suffix}.json'
    pd.DataFrame(rows).to_csv(table,index=False,float_format='%.16g')
    rawfile.write_text(json.dumps(raw,indent=2)+'\n')
    print(f"Noise variant={settings['variant']}; gates={settings['single_qubit_noisy_gates']}; records={len(rows)}; independent seeds={len(seen_seeds)}")
    print(pd.DataFrame(rows).groupby('architecture')[['approximation_or_error','standard_error','magnetization_z_sum']].mean().to_string())
    print(f"Saved {table.relative_to(ROOT)} and {rawfile.relative_to(ROOT)}")

if __name__=='__main__':
    main()
