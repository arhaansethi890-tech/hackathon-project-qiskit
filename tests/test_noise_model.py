import json
from pathlib import Path
import numpy as np
import pytest
from qiskit_aer.noise import depolarizing_error

from src.noise import fixed_noise_model, load_noise_settings

ROOT=Path(__file__).resolve().parents[1]


def test_kit_literal_noise_attaches_per_gate_to_all_single_qubit_basis_operations():
    settings=load_noise_settings()
    assert settings['scope_quote'].endswith('per 1-qubit gate')
    assert settings['single_qubit_noisy_gates']==['rz','sx','x']
    assert settings['rz_noiseless'] is False
    assert settings['cx_depolarizing_p']==.005
    assert settings['single_qubit_depolarizing_p']==.001
    model=fixed_noise_model()
    assert {'rz','sx','x','cx','measure'}.issubset(set(model.noise_instructions))
    errors=model.to_dict()['errors']
    oneq=[e for e in errors if e['type']=='qerror' and set(e['operations']) & {'rz','sx','x'}]
    assert len(oneq)==3
    expected=depolarizing_error(.001,1).to_dict()
    for item in oneq:
        assert item['probabilities']==pytest.approx(expected['probabilities'])
    cx=[e for e in errors if e['type']=='qerror' and 'cx' in e['operations']]
    assert len(cx)==1
    assert cx[0]['probabilities']==pytest.approx(depolarizing_error(.005,2).to_dict()['probabilities'])


def test_rz_virtual_is_separately_labeled_sensitivity_not_default():
    settings=load_noise_settings(rz_noiseless=True)
    assert settings['variant']=='project-rz-noiseless'
    assert settings['single_qubit_noisy_gates']==['sx','x']
    assert settings['rz_noiseless'] is True
    assert 'rz' not in fixed_noise_model(rz_noiseless=True).noise_instructions


def test_all_processor_noise_configs_are_identical_and_valid():
    configs=[json.loads((ROOT/'processors'/f'processor_{p}.json').read_text()) for p in ('A','B')]
    normalized=[]
    for i,cfg in zip(('A','B'),configs):
        settings=load_noise_settings(ROOT/'processors'/f'processor_{i}.json')
        normalized.append((settings['single_qubit_depolarizing_p'],tuple(settings['single_qubit_noisy_gates']),settings['cx_depolarizing_p'],tuple(tuple(r) for r in settings['readout_error_matrix'])))
    assert normalized[0]==normalized[1]
    assert np.allclose(configs[0]['noise_model']['readout_error_matrix'],[[.99,.01],[.01,.99]])


def test_invalid_noise_settings_fail_clearly(tmp_path):
    original=json.loads((ROOT/'processors/processor_A.json').read_text())
    for key,bad in [('single_qubit_depolarizing_p',-0.1),('cx_depolarizing_p',float('inf')),('readout_error_matrix',[[.98,.03],[.01,.99]])]:
        obj=json.loads(json.dumps(original));obj['noise_model'][key]=bad
        path=tmp_path/f'{key}.json';path.write_text(json.dumps(obj))
        with pytest.raises(ValueError):load_noise_settings(path)
