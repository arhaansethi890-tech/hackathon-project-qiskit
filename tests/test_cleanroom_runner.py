"""The isolated runner must not trust nbconvert's exit status alone."""
import nbformat

from scripts.cleanroom_reproduce import notebook_execution_issues


def test_notebook_validator_rejects_exit_zero_cell_errors_and_unexecuted_cells():
    failed_cell = nbformat.v4.new_code_cell(
        "raise RuntimeError('boom')",
        execution_count=1,
        outputs=[nbformat.v4.new_output(
            "error", ename="RuntimeError", evalue="boom", traceback=[]
        )],
    )
    skipped_cell = nbformat.v4.new_code_cell("pass", execution_count=None, outputs=[])
    issues = notebook_execution_issues(
        nbformat.v4.new_notebook(cells=[failed_cell, skipped_cell])
    )
    assert any("RuntimeError: boom" in issue for issue in issues)
    assert any("code cell 1 has no execution count" in issue for issue in issues)

    success_cell = nbformat.v4.new_code_cell(
        "print('ok')",
        execution_count=1,
        outputs=[nbformat.v4.new_output("stream", name="stdout", text="ok\n")],
    )
    assert notebook_execution_issues(nbformat.v4.new_notebook(cells=[success_cell])) == []
