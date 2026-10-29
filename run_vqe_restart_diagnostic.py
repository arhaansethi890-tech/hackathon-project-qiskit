"""Supplemental restart from the preserved g=1.5, seed-42 max-iteration result."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.problem import exact_ground_state,PROJECT_VQE_ABS_ERROR_TOLERANCE
from src.vqe import run_vqe

ROOT=Path(__file__).resolve().parent
runs=json.loads((ROOT/'results/raw/vqe_runs.json').read_text())
base=next(r for r in runs if float(r['g'])==1.5 and int(r['seed'])==42)
original=base['result']
restart=run_vqe(1.5,seed=42,reps=original['reps'],maxiter=2000,initial_parameters=original['parameters'])
ref,_=exact_ground_state(1.5);error=abs(restart['energy']-ref)
row={
 'status':'SUPPLEMENTAL_RESTART_NOT_A_REPLACEMENT_FOR_BASELINE',
 'source_run_id':base['run_id'],'g':1.5,'initial_vqe_seed':42,
 'initial_parameters_source':'saved final parameters from original unsuccessful maxiter=500 run',
 'original_termination':original['message'],'original_nit':original['nit'],
 'restart_optimizer':restart['optimizer'],'restart_success':restart['success'],
 'restart_message':restart['message'],'restart_nit':restart['nit'],'restart_nfev':restart['nfev'],
 'restart_energy':restart['energy'],'exact_reference':ref,'absolute_error':error,
 'relative_error':error/abs(ref),'final_gradient_inf_norm':restart['final_gradient_inf_norm'],
 'project_threshold':PROJECT_VQE_ABS_ERROR_TOLERANCE,
 'meets_project_threshold':bool(restart['success'] and error<=PROJECT_VQE_ABS_ERROR_TOLERANCE),
 'parameters':restart['parameters'],'history':restart['history'],
}
(ROOT/'results/raw/vqe_restart_diagnostic.json').write_text(json.dumps(row,indent=2)+'\n')
pd.DataFrame([row]).drop(columns=['parameters','history']).to_csv(ROOT/'results/tables/vqe_restart_diagnostic.csv',index=False,float_format='%.16g')
print(json.dumps({k:row[k] for k in ('original_termination','original_nit','restart_success','restart_message','restart_nit','restart_energy','absolute_error','relative_error','final_gradient_inf_norm','meets_project_threshold')},indent=2))
