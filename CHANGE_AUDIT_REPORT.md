# Phase 2 Change Audit Report

**Project:** QFF 2026 Phase 2, PS-S1 Quantum Simulation  
**Team:** Chicken Leg Piece  
**Comparison basis:** Phase 1 public-export SHA-256 manifest preserved as `PUBLIC_EXPORT_SHA256SUMS_phase1_archive.txt`.

## Executive summary

The project was updated from the team's Phase 1 PS-S1 experiment to the Phase 2 submission requirements. The Phase 2 package adds the locked organizer inputs, a Processor D design, the Phase 2 VQE/Bell simulation pipeline, result tables and figures, and updated project documentation.

The archived Phase 1 checksum manifest lists 102 files. Comparing those baseline contents with the current project found 94 byte-for-byte matches and eight modified files. The prior versions of `README.md`, `main.ipynb`, `report.md`, `requirements.txt`, and `results/experiment_manifest.json` were retained under archive names and verified against their original hashes. Other Phase 1 source files, tests, and historical results remain unchanged.

## Previously existing files modified

| File | Change made |
| --- | --- |
| `.github/workflows/ci.yml` | Replaced the Phase 1 workflow with Phase 2 dependency installation, dependency consistency checking, Processor D validation, and execution of the notebook using checked-in results. |
| `.gitignore` | Added `.venv*/` and `.uv-cache/` rules for local Python environments and package caches; the file also excludes Python/Jupyter caches and credential files. |
| `AI_DISCLOSURE.md` | Updated the disclosure to describe AI assistance in adapting the Phase 1 project to Phase 2, while assigning review and responsibility to the team. |
| `README.md` | Rewrote the project overview and run instructions for Phase 2; documented locked inputs, N=4/N=6 scope, Bell study, Processor D, outputs, reproducibility, and interpretation limits. Added a link to this audit. |
| `main.ipynb` | Replaced the Phase 1 notebook with a Phase 2 notebook that loads saved results by default, supports an explicit recomputation option, displays result tables and figures, and documents the N=6 option. The table display limit was raised to show all saved layer rows. |
| `project_metadata.json` | Updated the event and problem statement to QFF 2026 Phase 2 / PS-S1, recorded the team fields from the project, and stated that this local workflow did not submit to the portal. |
| `report.md` | Replaced the Phase 1 report with the Phase 2 results report: exact and variational energies, fidelities, observables, noisy Processor D results, A/B/D resources, and Bell results with propagated standard errors. |
| `requirements.txt` | Replaced Phase 1 pins with the official Phase 2 environment: Qiskit 1.4.6, Qiskit Aer 0.18.0, NumPy 2.4.6, SciPy 1.17.1, Matplotlib 3.11.2, Notebook 7.6.3, nbconvert 7.17.2, and ipykernel 7.4.0. |

## New Phase 2 files and artifacts

Thirty-seven Phase 2 support and result files were added (this audit report is additional):

- `qff_sim.py`: the organizer's simulation helper, copied unchanged.
- `processors/processor_D.json`: six-qubit cycle with opposite chords, native RZZ basis, official error rates, and the design justification.
- `tools/check_processor_d.py`: the official Processor D checker adapted to import the unchanged helper from the project root.
- `scripts/run_phase2_s1.py`: the Phase 2 pipeline for exact references, seeded HVA VQE layer scans, noisy D observables, A/B/D resource metrics, Bell measurements, tables, plots, and report generation.
- `data/instances_index.json` and 14 locked inputs under `data/s1/`: seven N=4 and seven N=6 open-chain TFIM instances across the required field grid.
- Six Phase 2 reference files under `docs/`: the official challenge-kit README, official kit checksum manifest, official problem statement, results-column template, Processor D template, and a concise Phase 2 specification/checklist.
- Four result tables under `results/tables/`: `s1_results.csv`, `s1_noisy.csv`, `resources.csv`, and `bell.csv`.
- Two raw-result files under `results/raw/`: selected VQE parameters and optimizer-run records.
- Six figures under `results/figures/`: the energy, observables, layer study, resources, Bell fidelity, and Processor D topology plots.

## Phase 1 files preserved

The prior versions of the README, notebook, report, dependency pins, and experiment manifest were retained as `README_phase1_archive.md`, `main_phase1_archive.ipynb`, `report_phase1_archive.md`, `requirements_phase1_archive.txt`, and `results/experiment_manifest_phase1_archive.json`. The Phase 1 checksum list was renamed to `PUBLIC_EXPORT_SHA256SUMS_phase1_archive.txt`. Hashes for the five archived content files match their Phase 1 manifest entries. The remaining Phase 1 source modules, tests, processor A/B definitions, and historical results are unchanged by SHA-256 comparison.

## Results and validation state

- N=4 meets `|E - E0| < 10^-3` at all seven fields. The selected layer counts are 4, 4, 4, 3, 4, 3, and 3 for increasing `g` values 0.25 through 2.00.
- On the seven selected N=4 circuits, Processor D averages 10.7 compiled two-qubit gates versus 21.4 for A and B, with average depth 28.0 versus 42.3.
- Bell fidelity is 0.9598 ± 0.0022 for the direct D pair and 0.9459 ± 0.0025 for the farthest pair.
- The official Processor D checker passed. The `qff_sim.py` SHA-256 is `dd0305834f88164f01f9b2a17f7333eb48a966cb81951b1953eed0e218de4cfc`, matching the official Phase 2 kit manifest. The 14 locked S1 instance files were previously confirmed against the official manifest.
- The optional N=6 optimization attempt was stopped after a long run because it had not produced completed saved results. The submission's reported simulation results are therefore N=4 only; the code and locked N=6 inputs remain available for a future run.
- A fresh-kernel notebook execution was attempted but did not complete in this local environment. Jupyter initially lacked permission to write to its default Windows profile folder; after redirecting Jupyter data and temporary paths into the workspace, the conversion still did not return. This audit does not claim that notebook execution was verified.
- No `pytest` suite was run. No public repository was created, and no portal submission was made by this workflow.

## Follow-up improvements for Phase 2 presentation and longer runs

The following follow-up changes were added after the initial audit:

| Area | New change |
| --- | --- |
| Long VQE scans | Added atomic per-field checkpoints after each complete HVA layer, with metadata validation and `--resume` support. An interrupted layer is safely repeated rather than treated as complete. |
| Optional N=6 tier | Added `--n6-only --resume`, which reuses the checked-in N=4 tables and saved optimizer records and spends new optimization time only on N=6. |
| Seed transparency | Added `results/tables/s1_seed_summary.csv` and a matching 21-row report table showing all three official seeds at the selected N=4 layer, including error, tolerance outcome, and optimizer calls. |
| Supplementary architecture noise study | Added `--supplement-only` to restore saved VQE states and compute the same-parameter A/B/D noisy density-matrix comparison at the three required fields, plus its CSV and figure. This is kept separate from the required D-only table. The local Windows Python is 3.10 and has no Qiskit installation, so the new A/B/D simulation table and figure were not generated in this environment; the pinned Python 3.11–3.13 environment is required. |
| Notebook and CI | Added optional seed/supplement displays and explicit resume/N=6/supplement controls to the notebook. CI now uses isolated Jupyter directories and a named kernel, then generates the supplemental comparison from saved runs before executing the notebook. |
| Judge preparation | Added `DEMO_GUIDE.md` with a timed three-minute walkthrough, accurate claim language, and likely judge questions. |

The initial audit statement above that no public repository had been created describes the state at the time of that audit. The project was subsequently published to `https://github.com/arhaansethi890-tech/hackathon-project-qiskit`; the follow-up changes are intended for that repository. The initial audit and this follow-up do not claim a portal submission or a hardware run.

## Submission location

The Phase 2 files were copied into the project folder named by the team: `C:\Users\arhaa\Downloads\hackathon project qiskit\hackathon project qiskit`. The clean prepared copy is under the Codex task's `outputs/phase2_submission` directory.
