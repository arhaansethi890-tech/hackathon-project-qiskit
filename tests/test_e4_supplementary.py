import json
from pathlib import Path
import pandas as pd
from src.processors import load_processor
ROOT=Path(__file__).resolve().parents[1]

def test_fixed_e4_ansatz_graph_definitions_are_connected():
    expected={
        'path4':{(0,1),(1,2),(2,3)},
        'ring4':{(0,1),(1,2),(2,3),(0,3)},
        'star4':{(0,1),(0,2),(0,3)},
    }
    for name,edges in expected.items():
        cfg,coupling=load_processor(ROOT/'supplementary/e4_path_ring_star'/f'{name}.json')
        assert cfg['qubit_count']==4
        assert {tuple(sorted(e)) for e in cfg['edges']}==edges
        assert coupling.is_connected()

def test_e4_plan_is_frozen_and_default_pipeline_excludes_execution():
    plan=(ROOT/'docs/EXPERIMENT_PLAN.md').read_text()
    reproduce=(ROOT/'scripts/reproduce.py').read_text()
    notebook=(ROOT/'main.ipynb').read_text()
    assert 'frozen before execution' in plan
    assert 'does not execute the supplementary E4 study' in reproduce
    assert 'run_e4_ansatz_patterns.py' not in reproduce
    assert 'scripts/run_e4_ansatz_patterns.py' not in notebook

def test_e4_real_ab_outputs_are_complete_and_preserve_canonical_path_runs():
    full=pd.read_csv(ROOT/'results/supplementary/tables/E4_ansatz_patterns.csv')
    summary=pd.read_csv(ROOT/'results/supplementary/tables/E4_pattern_summary.csv')
    paired=pd.read_csv(ROOT/'results/supplementary/tables/E4_paired_differences.csv')
    assert len(full)==54
    assert set(full.pattern)=={'path','ring','star'}
    assert set(full.architecture)=={'Processor A_branch','Processor B_ref12'}
    assert all(len(group)==9 for _,group in full.groupby(['pattern','architecture']))
    assert set(full.logical_cx_count)=={9,12}
    assert full.groupby('pattern').logical_cx_count.first().to_dict()=={'path':9,'ring':12,'star':9}
    assert full.instrumented_pipeline_matches_transpile_output.astype(str).str.lower().eq('true').all()
    assert full.semantic_fidelity.between(1-1e-9,1+1e-9).all()
    assert (full.shots_per_basis==4096).all()
    seeds=list(full.Z_simulator_seed)+list(full.X_simulator_seed)
    assert len(seeds)==108 and len(set(seeds))==108
    assert len(summary)==6 and (summary.n_runs==9).all()
    assert set(paired.g.astype(str))=={'0.5','1.0','1.5','all'}
    assert (paired[paired.g.astype(str)=='all'].n_pairs==9).all()
    raw=json.loads((ROOT/'results/supplementary/raw/E4_ansatz_pattern_runs.json').read_text())
    assert len(raw)==54
    for key,group in pd.DataFrame(raw).groupby(['pattern','g','seed']):
        assert len(group)==2
        assert group.iloc[0].final_parameters==group.iloc[1].final_parameters
    path=ROOT/'results/raw/vqe_runs.json'
    base={(float(r['g']),int(r['seed'])):r['result']['parameters'] for r in json.loads(path.read_text())}
    for _,r in full[full.pattern=='path'].drop_duplicates(['g','seed']).iterrows():
        matching=[item for item in raw if item['pattern']=='path' and item['g']==r.g and item['seed']==r.seed]
        assert len(matching)==2 and matching[0]['final_parameters']==base[(float(r.g),int(r.seed))]
