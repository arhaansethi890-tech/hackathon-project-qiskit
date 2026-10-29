import json
from pathlib import Path
import numpy as np
import pytest
from run_benchmark import classify_optimizer_run

ROOT=Path(__file__).resolve().parents[1]

def test_optimizer_status_and_energy_threshold_are_orthogonal():
    assert classify_optimizer_run(True,1e-6,1e-6)=='optimizer_success_and_project_threshold_met'
    assert classify_optimizer_run(True,1.1e-6,1e-6)=='optimizer_success_but_project_threshold_not_met'
    assert classify_optimizer_run(False,0.0,1e-6)=='optimizer_failure_or_iteration_limit'
    assert classify_optimizer_run(True,float('nan'),1e-6)=='invalid_or_nonfinite_result'

def test_reproduced_nine_trial_outcomes_and_failure_remain_visible():
    rows=json.loads((ROOT/'results/raw/vqe_runs.json').read_text())
    assert len(rows)==9
    classes=[r['optimizer_outcome_classification'] for r in rows]
    assert classes.count('optimizer_success_and_project_threshold_met')==8
    assert classes.count('optimizer_success_but_project_threshold_not_met')==0
    assert classes.count('optimizer_failure_or_iteration_limit')==1
    failed=next(r for r in rows if r['g']==1.5 and r['seed']==42)
    result=failed['result']
    assert result['success'] is False
    assert result['message']=='STOP: TOTAL NO. OF ITERATIONS REACHED LIMIT'
    assert result['nit']==500 and result['final_gradient_inf_norm']>1e-4
    assert failed['absolute_energy_error']>1e-6
    assert np.isclose(result['energy'],-6.503589956094921,atol=2e-12)
    assert np.isclose(failed['absolute_energy_error'],3.016010314924e-4,atol=1e-12)

def test_supplemental_restart_does_not_replace_original_failure():
    original=json.loads((ROOT/'results/raw/vqe_runs.json').read_text())
    restart=json.loads((ROOT/'results/raw/vqe_restart_diagnostic.json').read_text())
    failed=next(r for r in original if r['g']==1.5 and r['seed']==42)
    assert failed['result']['success'] is False
    assert restart['source_run_id']==failed['run_id']
    assert restart['status'].startswith('SUPPLEMENTAL')
    assert restart['restart_success'] is True and restart['meets_project_threshold'] is True
    assert restart['restart_nit']==206
