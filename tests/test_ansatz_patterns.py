import numpy as np
import pytest
from src.ansatz import PATTERN_EDGES, make_ansatz, make_pattern_ansatz, parameter_count

def test_historical_ansatz_default_repetitions_are_preserved():
    p=np.zeros(parameter_count())
    assert parameter_count()==12
    assert int(make_ansatz(p).count_ops().get('cx',0))==6

def test_explicit_three_sweep_patterns_have_expected_cx_counts():
    p=np.zeros(parameter_count(reps=3))
    expected={'path':9,'ring':12,'star':9}
    for pattern,count in expected.items():
        qc=make_pattern_ansatz(p,pattern=pattern,reps=3)
        assert qc.num_qubits==4
        assert int(qc.count_ops().get('ry',0))==16
        assert int(qc.count_ops().get('cx',0))==count
        assert len(PATTERN_EDGES[pattern])*3==count

def test_pattern_builder_rejects_invalid_patterns_and_dimensions():
    with pytest.raises(ValueError):make_pattern_ansatz(np.zeros(16),pattern='complete')
    with pytest.raises(ValueError):make_pattern_ansatz(np.zeros(15),pattern='path',reps=3)
    with pytest.raises(ValueError):make_pattern_ansatz(np.full(16,np.nan),pattern='star',reps=3)
