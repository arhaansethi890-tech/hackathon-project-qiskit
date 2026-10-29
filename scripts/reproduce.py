"""Run the canonical PS-S1 project pipeline in its fixed, auditable order.

This command does not execute the supplementary E4 study and does not regenerate
or promote the release manifest. Run from any working directory.
"""
from __future__ import annotations
import subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STEPS=(
    ("exact validation", "run_exact_validation.py"),
    ("graph analysis", "run_graph_analysis.py"),
    ("canonical VQE and A/B compilation", "run_benchmark.py"),
    ("separate VQE restart diagnostic", "run_vqe_restart_diagnostic.py"),
    ("fixed-model noisy A/B sampling", "run_noisy.py"),
    ("pooled, paired, and error-decomposition metrics", "run_ab_comparison.py"),
    ("processed-data export", "run_processed_data.py"),
    ("figures", "make_figures.py"),
    ("generated README and report tables", "scripts/render_docs.py"),
)
def main():
    for label, script in STEPS:
        print(f"[run] {label}", flush=True)
        subprocess.run([sys.executable, str(ROOT/script)], cwd=ROOT, check=True)
    print("Canonical PS-S1 pipeline completed. E4 was not run; manifest is a frozen release snapshot.")
if __name__ == "__main__": main()
