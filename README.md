# QFF 2026 Phase 2 - PS-S1 Quantum Simulation

**Team:** Chicken Leg Piece — Swarup, Biswajit, Arhaan Sethi, Shorya Pratap Singh Chandrawat.

This repository continues the team's PS-S1 Phase 1 work with the locked Phase 2 inputs. Phase 2 uses the organizer-provided open-chain TFIM instances and HVA workflow, adds the common Processor D Bell-state study, and benchmarks the same PS-S1 circuits on Processors A, B and D.

## Quick start

Use Python 3.11, 3.12 or 3.13 in a dedicated environment:

```bash
python -m venv .venv
# Activate the environment using your operating system's command.
python -m pip install -r requirements.txt
jupyter notebook main.ipynb
```

The notebook loads the checked-in Phase 2 tables by default so it opens quickly. Set `RECOMPUTE = True` in its first code cell to rerun the official simulation pipeline. To regenerate the core PS-S1 outputs from a terminal:

```bash
python scripts/run_phase2_s1.py
```

The optional N=6 bonus tier is available with:

```bash
python scripts/run_phase2_s1.py --include-n6 --resume
```

The layer scan checkpoints after each completed field/layer. Continue an interrupted N=4 or combined run with `--resume`; to spend the remaining compute only on N=6 while keeping the checked-in N=4 results, use:

```bash
python scripts/run_phase2_s1.py --n6-only --resume
```

Regenerate the seed summary and the supplementary noisy A/B/D comparison from saved VQE results without repeating the optimizer search with:

```bash
python scripts/run_phase2_s1.py --supplement-only
```

The full recomputation may take longer than 30 minutes on a laptop. The notebook's `RECOMPUTE = False` path uses the saved results; all seeds, inputs, checkpoints, and commands are recorded so the run can be reproduced.

## Phase 2 scope

- PS-S1: open-chain TFIM, `J=1`, `N=4`, `g={0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 2.00}`. N=6 is optional.
- VQE uses the HVA, three official initialization seeds (0, 1, 2), and the locked instance files under `data/s1/`; the official index is `data/instances_index.json`.
- The layer study finds the smallest HVA depth reaching `|E - E0| < 10^-3` for each field. The results include exact references, `F`, `F2`, observables, optimizer calls, and parameter counts.
- Noisy PS-S1 observables and density-matrix fidelity are reported on D for `g=0.5, 1.0, 2.0`.
- The common Bell experiment measures `XX`, `YY`, and `ZZ` on a direct D pair and a farthest-apart D pair, ideal and noisy, with 4,096 shots per basis.
- D is a six-qubit cycle with opposite chords and native `rzz`. It preserves the four-site ring pattern that exposed routing overhead in the Phase 1 supplementary study, supports the optional six-qubit open-chain tier, and implements each HVA ZZ rotation with one two-qubit gate instead of the two-CX decomposition used on A/B. Its RZZ error rate equals the official CX rate.

## Reproducibility and outputs

The official `qff_sim.py` helper is included unchanged. It supplies the locked A/B topologies, noise, seeds, transpilation, metrics, Bell routine, HVA, and exact-state helpers. The Processor D file is checked by:

```bash
python tools/check_processor_d.py processors/processor_D.json 6
```

Phase 2 result tables are in `results/tables/`: `bell.csv`, `resources.csv`, `s1_results.csv`, `s1_noisy.csv`, and (after the supplement command) `s1_seed_summary.csv` plus `s1_noisy_architectures.csv`. Figures and the Processor D graph are in `results/figures/`. The complete input conventions and scoring checklist are summarized in `docs/PHASE2_SPEC.md`; the judge-facing walkthrough is in `DEMO_GUIDE.md`; the previous Phase 1 notebook, report, README, and dependency pins are retained as archives.

The file-by-file comparison with the previous public export is recorded in `CHANGE_AUDIT_REPORT.md`.

## Interpretation limits

All processor runs are local Aer simulations with the official synthetic noise model; no required run uses quantum hardware. Processor comparisons are limited to the locked graphs, circuits, seeds, fields, and noise model. The reported standard errors describe shot uncertainty where applicable; they are not evidence of a hardware advantage.

## AI assistance

AI tools assisted with code changes and documentation. The team reviewed the implementation and generated results and remains responsible for understanding and verifying the submission. See `AI_DISCLOSURE.md`.
