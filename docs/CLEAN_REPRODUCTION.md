# Clean reproduction protocol

Use the exact pins in `requirements.txt` in a fresh Python virtual environment. Execute `main.ipynb` with the standard `python3` Jupyter kernel. The Phase 2 notebook imports `scripts/run_phase2_s1.py`: by default it loads the checked-in tables; set `RECOMPUTE = True` to regenerate the Phase 2 simulation outputs. `scripts/reproduce.py` is the Phase 2 command-line entry point. The archived Phase 1 sequence is retained as `scripts/reproduce_phase1_archive.py` and is not used by the Phase 2 notebook.

The separate clean-room helper `scripts/cleanroom_reproduce.py` copies source to a new `.v3_*` directory, omits generated primary outputs, preserves only frozen E4 supplementary artifacts for reporting/tests, executes the notebook with a registered kernel, then runs pytest. It defaults to kernel name `python3` and writes logs outside the project tree. Use an external private log directory when retaining verification evidence. The helper's directory copy is not a Git clone; it must never be reported as one.

No verification outcome is asserted by this protocol document. Final executed commands, exit codes, durations, test counts, artifact comparisons, and any deviations belong in the private handoff after the final run.
