# QFF 2026 Phase 2 — Quantum Simulation Challenge Kit

Read **QFF2026_Phase2_Simulation_Problem_Statements.docx** first. It is the authoritative description of every task, rule, definition and deadline. This kit holds every input it refers to.

| When (IST) | What |
|---|---|
| Day 1, 6:00 PM | Hackathon starts (help desk for clarifications 6:00–8:00 PM) |
| **Day 2, 5:40 PM** | **Final commit; repository URL submitted on the hackathon portal** (https://qffsrmap2026.com/learning/hackathon) |

## Setup (dedicated environment)

```bash
python3 -m venv sim-env && source sim-env/bin/activate      # Python 3.11, 3.12 or 3.13
pip install --upgrade pip && pip install -r requirements.txt
cd starter && jupyter notebook starter_sim.ipynb             # runs in under a minute
```

## Contents

| Path | What it is |
|---|---|
| `data/instances_index.json` | Every locked value: g grid, times, step lists, noise scales, gate conventions, processors, settings |
| `data/s1/` | PS-S1: open-chain TFIM operators, N = 4 (required) and N = 6 (optional), 7 values of g, with exact E₀ and E₁ |
| `data/s2/` | PS-S2: open-chain TFIM, N = 4, g = 1 |
| `data/s3/` | PS-S3: ring TFIM, N = 4, g = 1 |
| `starter/qff_sim.py` | Official settings, Processors A/B, noise model (with scale factor), resource metrics, Bell experiment, Processor D checker, TFIM builder, observables, HVA ansatz, Trotter circuits (1st/2nd order, CX or RZZ construction), exact evolution, density-matrix fidelity, Z-basis measurement |
| `starter/starter_sim.ipynb` | Worked example of the official workflow |
| `starter/processor_D_template.json` | Processor D file format |
| `tools/check_processor_d.py` | Copy `starter/processor_D_template.json` to `processors/processor_D.json` in your repository, edit it, then run `python tools/check_processor_d.py processors/processor_D.json 4` from the kit root. Self-test on the template: `python tools/check_processor_d.py starter/processor_D_template.json 4` |
| `templates/results_columns.md` | Required result tables |
| `MANIFEST.sha256` | Checksums |

Answer keys are **not** in this kit.
