import math
import pytest
from src.metrics import mean_sd_sem, signed_and_absolute_error, shot_sem

def test_descriptive_statistics_use_sample_sd_and_sem():
    m=mean_sd_sem([1,2,3])
    assert m['n']==3 and m['mean']==2
    assert math.isclose(m['sample_sd'],1)
    assert math.isclose(m['sem'],1/math.sqrt(3))
    assert math.isnan(mean_sd_sem([2])['sem'])

def test_energy_error_sign_and_magnitude_are_explicit():
    e=signed_and_absolute_error(-2,-3)
    assert e['signed_error']==1 and e['absolute_error']==1
    assert e['relative_absolute_error']==pytest.approx(1/3)

def test_independent_pauli_group_sem_combination_and_validation():
    assert shot_sem([4,9],[4,9])==pytest.approx(math.sqrt(2))
    with pytest.raises(ValueError):shot_sem([1],[0])
