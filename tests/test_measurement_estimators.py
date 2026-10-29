import numpy as np
import pytest
from src.measurements import tfim_energy_from_counts
from src.randomness import derive_simulator_seed


def test_synthetic_all_up_counts_match_term_signs_and_coefficients():
    shots=32
    out=tfim_energy_from_counts({'0000':shots},{'0000':shots},g=.5)
    assert out['energy_z']==pytest.approx(-3.0)
    assert out['energy_x']==pytest.approx(-2.0)
    assert out['energy']==pytest.approx(-5.0)
    assert out['standard_error_z']==pytest.approx(0.0)
    assert out['standard_error_x']==pytest.approx(0.0)
    assert out['standard_error']==pytest.approx(0.0)
    assert out['shots_z']==shots and out['shots_x']==shots


def test_count_estimator_combines_independent_group_standard_errors():
    # Z outcomes differ in domain-wall count; X outcomes differ in total spin.
    z_counts={'0000':10,'0100':10}
    x_counts={'0000':10,'1111':10}
    out=tfim_energy_from_counts(z_counts,x_counts,g=1.0)
    assert out['standard_error_z']>0 and out['standard_error_x']>0
    assert out['standard_error']==pytest.approx(np.hypot(out['standard_error_z'],out['standard_error_x']))
    assert out['independence_assumption'].startswith('independent simulator seeds')


def test_simulator_seed_derivation_is_stable_and_unique_for_benchmark_grid():
    tuples=[]
    for g in (.5,1.,1.5):
      for vqe in (42,7,21):
       for arch in ('Processor A','Processor B'):
        for basis in ('X','Z'):
         for variant in ('kit-literal-all-one-qubit-gates','project-rz-noiseless'):
          t=(g,vqe,arch,basis,0,variant);tuples.append(t)
    seeds=[derive_simulator_seed(*t) for t in tuples]
    assert len(seeds)==len(set(seeds))
    t=(1.0,42,'Processor A','Z',0,'kit-literal-all-one-qubit-gates')
    assert derive_simulator_seed(*t)==derive_simulator_seed(*t)
    assert derive_simulator_seed(*t)!=derive_simulator_seed(1.0,42,'Processor B','Z',0,'kit-literal-all-one-qubit-gates')
    with pytest.raises(ValueError):derive_simulator_seed(1,42,'A','Y')

def test_per_run_magnetization_correlator_estimators_use_per_shot_standard_errors():
    from src.measurements import observable_estimates_from_counts
    z=observable_estimates_from_counts({'0000':50,'1111':50},4,'Z')
    assert z['Mz_per_site']==0.0 and z['Mz2_normalized']==1.0
    assert [z[f'ZZ_{i}_{i+1}'] for i in range(3)]==[1.0,1.0,1.0]
    assert z['Mz_per_site_se']>0 and z['Mz2_normalized_se']==0
    x=observable_estimates_from_counts({'0000':50,'1111':50},4,'X')
    assert x['Mx_per_site']==0.0 and x['Mx_per_site_se']>0
