from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]


def test_default_notebook_uses_the_phase2_runner_and_saved_results():
    notebook = nbformat.read(ROOT / "main.ipynb", as_version=4)
    code = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")

    assert "from scripts.run_phase2_s1 import" in code
    assert "RECOMPUTE = False" in code
    assert "results = run_phase2_s1()" in code
    assert "scripts/reproduce.py" not in code


def test_notebook_has_a_standard_kernel_and_no_saved_cell_errors():
    notebook = nbformat.read(ROOT / "main.ipynb", as_version=4)
    assert notebook.metadata.kernelspec.name == "python3"
    assert notebook.metadata.kernelspec.language == "python"
    cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert cells
    assert not any(output.output_type == "error" for cell in cells for output in cell.outputs)
    markdown = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "markdown").lower()
    assert "phase 2" in markdown
    assert "locked instance" in markdown


def test_current_readme_and_report_describe_phase2_and_local_dashboard():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    report = (ROOT / "report.md").read_text(encoding="utf-8")
    assert "python scripts/run_phase2_s1.py" in readme
    assert "Local API and dashboard" in readme
    assert "no portal submission or hardware run is claimed" in report
