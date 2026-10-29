from pathlib import Path
import nbformat
ROOT=Path(__file__).resolve().parents[1]

def test_default_notebook_runs_only_the_canonical_stage1_pipeline():
    notebook=nbformat.read(ROOT/'main.ipynb',as_version=4)
    code='\n'.join(c.source for c in notebook.cells if c.cell_type=='code')
    assert 'scripts/reproduce.py' in code
    assert 'scripts/run_e4_ansatz_patterns.py' not in code
    assert 'make_manifest.py' not in code
    assert 'run_vqe_baseline_legacy.py' not in code
    assert 'run_custom_D_comparison.py' not in code and 'run_ring_stress.py' not in code
    assert 'run_density_fidelity.py' not in code

def test_notebook_is_standard_kernel_executed_and_error_free():
    notebook=nbformat.read(ROOT/'main.ipynb',as_version=4)
    assert notebook.metadata.kernelspec.name=='python3'
    assert notebook.metadata.kernelspec.language=='python'
    cells=[c for c in notebook.cells if c.cell_type=='code']
    assert cells and all(c.execution_count is not None for c in cells)
    assert not any(o.output_type=='error' for c in cells for o in c.outputs)
    markdown='\n'.join(c.source for c in notebook.cells if c.cell_type=='markdown').lower()
    assert 'magnetization axis and normalization remain undefined' in markdown
    assert 'no hardware was run' in markdown
    assert ('processor' + ' ' + chr(100)) not in markdown

def test_rendered_docs_table_headers_and_publication_wording():
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    report = (ROOT / 'report.md').read_text(encoding='utf-8')
    
    # 1. Assert no malformed table header in README
    assert '|error|' not in readme
    assert '| Absolute error |' in readme
    
    # Check that every row in the VQE table in README has exactly 7 data columns
    vqe_start = readme.find('## All canonical VQE starts')
    vqe_end = readme.find('## Fixed reference graphs')
    vqe_table = readme[vqe_start:vqe_end]
    table_lines = [l for l in vqe_table.splitlines() if l.startswith('|') and not l.startswith('| ---')]
    assert len(table_lines) == 10  # 1 header + 9 data rows
    for line in table_lines:
        cols = [c.strip() for c in line.split('|')[1:-1]]
        assert len(cols) == 7, f"Row in VQE table does not have 7 columns: {line}"
    
    # 2. Assert accurate publication and portal submission wording
    assert 'publicly hosted on GitHub' in readme
    assert 'did not submit to the hackathon portal' in readme
    assert 'No external submission, publication, or push was performed' not in readme
    
    assert 'publicly hosted on GitHub' in report
    assert 'did not submit to the hackathon portal' in report
    assert 'No hardware, portal, organizer contact, submission, publication or push is claimed' not in report
    
    # 3. Assert Processor D proposal is present in root report.md
    assert '## Proposed Processor D Design Ideology (Proposal Only — Not a Phase 1 Benchmark)' in report

