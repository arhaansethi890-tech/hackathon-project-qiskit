#!/usr/bin/env python3
"""Reproduce the scientific notebook and tests in a fresh, non-promoting worktree.

Run from any directory with the project's Python environment active. The source
worktree is copied without generated primary result/output trees, user uploads,
caches, installed environments, or frontend dependencies. Frozen supplementary E4
artifacts are copied for preservation/rendering tests but are never rerun or promoted.
"""
from __future__ import annotations

import argparse
import fnmatch
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    ".git", ".venv", ".cache", ".local", ".npm", ".arena", ".ipython",
    ".pytest_cache", ".ruff_cache", ".mypy_cache", ".tox", ".nox", ".config", ".jupyter",
    "__pycache__", "node_modules", "dist", "build", "coverage", "target",
    "out", "uploads", "backups", "public", "test-results",
    "playwright-report",
}


def ignored(directory: str, names: list[str]) -> set[str]:
    current=Path(directory).resolve()
    skip={name for name in names if name in EXCLUDED or fnmatch.fnmatch(name, ".v3_*")}
    if current==ROOT/"results":
        skip.update(name for name in names if name!="supplementary")
    if current==ROOT/"results"/"supplementary":
        skip.update(name for name in names if name not in {"raw","tables","figures"})
    return skip


def notebook_execution_issues(notebook) -> list[str]:
    """Reject nbconvert's exit-zero notebooks that contain cell errors or skips."""
    code_cells = [(index, cell) for index, cell in enumerate(notebook.cells) if cell.cell_type == "code"]
    issues = []
    if not code_cells:
        issues.append("notebook has no code cells")
    for index, cell in code_cells:
        if cell.execution_count is None:
            issues.append(f"code cell {index} has no execution count")
        for output in cell.get("outputs", []):
            if output.output_type == "error":
                issues.append(f"code cell {index} error: {output.ename}: {output.evalue}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="new worktree path (must be named .v3_*)")
    parser.add_argument("--kernel", default="python3", help="registered Jupyter kernel (default: python3)")
    parser.add_argument("--logs-dir", help="external log directory; defaults to a temp directory outside the project")
    args = parser.parse_args()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    worktree = Path(args.output) if args.output else ROOT / f".v3_cleanroom_{stamp}"
    if not worktree.is_absolute():
        worktree = ROOT / worktree
    worktree = worktree.resolve()
    try:
        worktree.relative_to(ROOT)
    except ValueError:
        parser.error("--output must be inside the project root")
    if worktree == ROOT or not worktree.name.startswith(".v3_"):
        parser.error("--output must be a new directory named with the .v3_ prefix")
    if worktree.exists():
        parser.error(f"output already exists; refusing to overwrite: {worktree}")

    logs_dir = Path(args.logs_dir).expanduser().resolve() if args.logs_dir else Path(tempfile.gettempdir()) / "qff-s1-cleanroom-logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stem = datetime.now(timezone.utc).strftime("%Y-%m-%d_cleanroom")
    notebook_log = logs_dir / f"{stem}_notebook.txt"
    tests_log = logs_dir / f"{stem}_pytest.txt"
    if notebook_log.exists() or tests_log.exists():
        stem = f"{stem}_{stamp[-6:]}"
        notebook_log = logs_dir / f"{stem}_notebook.txt"
        tests_log = logs_dir / f"{stem}_pytest.txt"

    shutil.copytree(ROOT, worktree, ignore=ignored)
    for directory in ("raw", "tables", "figures", "logs"):
        (worktree / "results" / directory).mkdir(parents=True, exist_ok=True)

    try:
        import nbformat
    except ImportError as exc:
        shutil.rmtree(worktree, ignore_errors=True)
        parser.error(f"nbformat is required in the active Python environment: {exc}")
    notebook_path = worktree / "main.ipynb"
    notebook = nbformat.read(notebook_path, as_version=4)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    nbformat.write(notebook, notebook_path)

    commands = (
        ("notebook", [
            sys.executable, "-m", "nbconvert", "--to", "notebook", "--execute",
            "--inplace", "--ExecutePreprocessor.timeout=1800",
            f"--ExecutePreprocessor.kernel_name={args.kernel}", "main.ipynb",
        ], notebook_log),
        ("pytest", [sys.executable, "-m", "pytest", "-q"], tests_log),
    )
    for label, command, log_path in commands:
        result = subprocess.run(
            command, cwd=worktree, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, check=False,
        )
        validation_issues = []
        validation_summary = ""
        if label == "notebook" and result.returncode == 0:
            try:
                executed = nbformat.read(notebook_path, as_version=4)
                code_count = sum(cell.cell_type == "code" for cell in executed.cells)
                validation_issues = notebook_execution_issues(executed)
                validation_summary = (
                    f"Post-run notebook validation: {code_count} code cells; "
                    f"{len(validation_issues)} errors or unexecuted cells."
                )
            except Exception as exc:
                validation_issues = [f"cannot validate executed notebook: {exc}"]
                validation_summary = f"Post-run notebook validation failed: {exc}"
        safe_command = "python " + " ".join(command[1:])
        log_path.write_text(
            f"Command: {safe_command}\nWorking directory: isolated clean-room copy\n"
            f"Exit code: {result.returncode}\n{validation_summary}\n\n{result.stdout}",
            encoding="utf-8",
        )
        effective_exit = result.returncode or (1 if validation_issues else 0)
        print(f"{label}: exit {effective_exit}; external log: {log_path}")
        if effective_exit:
            print(result.stdout[-6000:])
            for issue in validation_issues:
                print(f"Notebook validation: {issue}")
            print(f"Review the non-promoted worktree: {worktree}")
            return effective_exit

    print(f"Clean-room outputs retained, not promoted: {worktree}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
