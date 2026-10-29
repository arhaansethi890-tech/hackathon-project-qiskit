"""Run the nine canonical VQE starts and map each saved circuit to primary A/B."""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd
from qiskit.quantum_info import Statevector

from src.ansatz import make_ansatz, parameter_count
from src.fidelity import pure_state_fidelity, reduce_to_logical
from src.problem import FIELDS, N, PROJECT_VQE_ABS_ERROR_TOLERANCE, exact_ground_state, state_observables
from src.processors import load_processor
from src.routing import compile_with_evidence
from src.vqe import run_vqe

ROOT=Path(__file__).resolve().parent
SEEDS=(42,7,21)


def classify_optimizer_run(success: bool, absolute_error: float, threshold: float) -> str:
    if not np.isfinite(absolute_error):
        return 'invalid_or_nonfinite_result'
    if success and absolute_error <= threshold:
        return 'optimizer_success_and_project_threshold_met'
    if success:
        return 'optimizer_success_but_project_threshold_not_met'
    return 'optimizer_failure_or_iteration_limit'


def main():
    for rel in ('results/raw','results/tables','results/figures','results/logs'):
        (ROOT/rel).mkdir(parents=True,exist_ok=True)
    rows=[]; raw=[]
    for g in FIELDS:
        ref,exact=exact_ground_state(g)
        exact_obs=state_observables(exact)
        for seed in SEEDS:
            result=run_vqe(g,seed=seed)
            state=result.pop('state')
            fidelity=pure_state_fidelity(exact,state.data)
            vqe_obs=state_observables(state.data)
            base=make_ansatz(result['parameters'],reps=result['reps'])
            absolute_error=abs(result['energy']-ref)
            relative_error=absolute_error/abs(ref)
            outcome=classify_optimizer_run(result['success'],absolute_error,PROJECT_VQE_ABS_ERROR_TOLERANCE)
            run_id=f'S1-g{str(g).replace(".","p")}-vqe{seed}'
            common={
                'model_status':'PS-S1 simulation; October 14, 2026 Master Guide verified',
                'problem_id':'S1','run_id':run_id,'instance_id':f'g={g}','g':float(g),'seed':int(seed),
                'objective_or_accuracy':float(result['energy']),'vqe_initial_energy':float(result['initial_energy']),
                'classical_reference':float(ref),'approximation_or_error':float(absolute_error),
                'relative_energy_error':float(relative_error),'vqe_success':bool(result['success']),'error_definition_absolute':'abs(E_vqe - E0)',
                'relative_error_definition':'abs(E_vqe - E0)/abs(E0)','fidelity':float(fidelity),
                **{f'exact_{k}':v for k,v in exact_obs.items() if k not in ('z_sites','x_sites')},
                **{f'vqe_{k}':v for k,v in vqe_obs.items() if k not in ('z_sites','x_sites')},
                **{f'error_{k}':v-exact_obs[k] for k,v in vqe_obs.items() if k not in ('z_sites','x_sites','zz_correlators')},
                **{f'exact_ZZ_{i}_{i+1}':v for i,v in enumerate(exact_obs['zz_correlators'])},
                **{f'vqe_ZZ_{i}_{i+1}':v for i,v in enumerate(vqe_obs['zz_correlators'])},
                **{f'error_ZZ_{i}_{i+1}':v-exact_obs['zz_correlators'][i] for i,v in enumerate(vqe_obs['zz_correlators'])},
                'exact_z_sites':exact_obs['z_sites'],'vqe_z_sites':vqe_obs['z_sites'],
                'exact_x_sites':exact_obs['x_sites'],'vqe_x_sites':vqe_obs['x_sites'],
                'optimizer':'L-BFGS-B','optimizer_success':bool(result['success']),
                'optimizer_termination_message':result['message'],'optimizer_outcome_classification':outcome,
                'meets_project_energy_tolerance':outcome=='optimizer_success_and_project_threshold_met',
                'project_energy_tolerance':PROJECT_VQE_ABS_ERROR_TOLERANCE,
                'project_tolerance_authority':'project reporting convention, not an organizer mandate',
                'vqe_nit':int(result['nit']),'vqe_nfev':int(result['nfev']),
                'final_gradient_inf_norm':float(result['final_gradient_inf_norm']),
                'final_gradient_l2_norm':float(result['final_gradient_l2_norm']),
                'initial_parameters':result['initial_parameters'],'final_parameters':result['parameters'],
                'iterations_energy_history':result['history'],'initialization':result['initialization'],
                'variational_parameters':parameter_count(reps=result['reps']),
                'ansatz_repetitions':int(result['reps']),'logical_qubits':N,
                'logical_cx_count':int(base.count_ops().get('cx',0)),'logical_depth':int(base.depth()),
                'maxiter':int(result['maxiter']),'ftol':float(result['ftol']),
                'gtol':float(result['gtol']),'maxls':int(result['maxls']),
            }
            rows.append({**common,'architecture':'ideal logical','physical_qubits':N,
                         'cx_count':int(base.count_ops().get('cx',0)),'depth':int(base.depth()),
                         'swap_count':0,'routing_swaps':[],'final_circuit_swap_gate_count':0,
                         'noise_model':'ideal Statevector; no shot noise','shots':None,
                         'topology_status':'not applicable'})
            raw_record={'run_id':run_id,'model_status':common['model_status'],'g':float(g),'seed':int(seed),
                        'result':{**result,'statevector_real':state.data.real.tolist(),'statevector_imag':state.data.imag.tolist()},
                        'exact_energy':float(ref),'absolute_energy_error':float(absolute_error),
                        'relative_energy_error':float(relative_error),'fidelity':float(fidelity),
                        'optimizer_outcome_classification':outcome}
            raw.append(raw_record)

            for processor_id in ('processor_A','processor_B'):
                config,coupling=load_processor(ROOT/'processors'/f'{processor_id}.json')
                compiled,evidence=compile_with_evidence(
                    base,coupling_map=coupling,basis_gates=config['basis_gates'],
                    optimization_level=1,layout_method='sabre',routing_method='sabre',seed_transpiler=42)
                if not evidence['instrumented_pipeline_matches_transpile_output']:
                    raise RuntimeError(f"Compilation pipelines disagree for {run_id} on {config['name']}")
                physical=Statevector.from_instruction(compiled).data
                mapping=evidence['final_layout']
                reduced=reduce_to_logical(np.outer(physical,physical.conj()),mapping,compiled.num_qubits,N)
                semantic=float(np.vdot(state.data,reduced@state.data).real)
                if not np.isclose(semantic,1.0,atol=1e-9):
                    raise RuntimeError(f"Mapped-state semantic check failed for {run_id} on {config['name']}: {semantic}")
                counts=compiled.count_ops()
                row={**common,'architecture':config['name'],'physical_qubits':int(config['qubit_count']),
                     'cx_count':int(counts.get('cx',0)),'depth':int(compiled.depth()),
                     'single_qubit_gate_count':int(sum(counts.get(gate,0) for gate in ('rz','sx','x'))),
                     'swap_count':len(evidence['routing_swaps']),'routing_swaps':evidence['routing_swaps'],
                     'final_circuit_swap_gate_count':int(counts.get('swap',0)),
                     'initial_layout':evidence['initial_layout'],'final_layout':evidence['final_layout'],
                     'physical_qubits_used':sorted(set(evidence['final_layout'])),
                     'available_physical_qubits':list(range(int(config['qubit_count']))),
                     'cx_overhead_vs_logical_cx':int(counts.get('cx',0))-int(base.count_ops().get('cx',0)),
                     'compiled_semantic_fidelity':semantic,'shots':None,
                     'noise_model':'ideal Statevector; no shot noise',
                     'topology_status':config['topology_status'],
                     'optimization_level':evidence['optimization_level'],
                     'requested_layout_method':evidence['requested_layout_method'],
                     'requested_routing_method':evidence['requested_routing_method'],
                     'seed_transpiler':evidence['seed_transpiler'],
                     'basis_gates':config['basis_gates'],
                     **{key:evidence[key] for key in ('layout_selection_pass','observed_layout_selection_passes','observed_layout_passes','routing_pass','observed_routing_passes','routing_swap_pass_evidence','pass_trace','instrumented_pipeline_matches_transpile_output')}}
                rows.append(row)
                raw_record.setdefault('compiled',{})[processor_id]={
                    key:row[key] for key in ('cx_count','depth','swap_count','routing_swaps','final_circuit_swap_gate_count',
                        'initial_layout','final_layout','compiled_semantic_fidelity','layout_selection_pass',
                        'observed_layout_selection_passes','observed_routing_passes','pass_trace',
                        'instrumented_pipeline_matches_transpile_output','transpiled_circuit') if key in row}
                raw_record['compiled'][processor_id]['transpiled_circuit']=compiled.draw(output='text').__str__()

    table=ROOT/'results/tables/ideal_architecture_results.csv'
    rawfile=ROOT/'results/raw/vqe_runs.json'
    pd.DataFrame(rows).to_csv(table,index=False,float_format='%.16g')
    rawfile.write_text(json.dumps(raw,indent=2)+'\n',encoding='utf-8',newline='\n')
    baseline=next(run for run in raw if run['g']==1.0 and run['seed']==42)
    logical=make_ansatz(baseline['result']['parameters'],reps=baseline['result']['reps'])
    logical_text=logical.draw(output='text').__str__()
    (ROOT/'results/logs/circuit_comparison.txt').write_text(
        'Logical circuit (g=1, VQE seed=42):\n'+logical_text+
        '\n\nCompiled details and actual pass evidence are in ideal_architecture_results.csv and raw JSON.\n',
        encoding='utf-8',newline='\n')
    df=pd.DataFrame(rows)
    print(f'Finished {len(raw)} principal VQE starts and {len(rows)} ideal result rows.')
    print('Actual optimizer classifications:')
    print(df[df.architecture=='ideal logical'].groupby('optimizer_outcome_classification').size().to_string())
    print(df[df.architecture=='ideal logical'][['g','seed','optimizer_success','optimizer_termination_message','approximation_or_error','relative_energy_error','final_gradient_inf_norm','optimizer_outcome_classification']].to_string(index=False))
    print('Resource means:')
    print(df.groupby('architecture')[['approximation_or_error','cx_count','depth']].mean().to_string())
    print(f'Saved {table.relative_to(ROOT)} and {rawfile.relative_to(ROOT)}')

if __name__=='__main__':
    main()
