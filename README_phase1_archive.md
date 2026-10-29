# PS-S1: exact, variational, and noisy A/B simulation

**Qiskit Fall Fest 2026 · Phase 1 · SRM University-AP**  
**Team Chicken Leg Piece:** Swarup · Biswajit · Arhaan Sethi · Shorya Pratap Singh Chandrawat (submitting lead as recorded in project metadata).

This repository records a reproducible local simulation study of the four-site open transverse-field Ising model. All reported hardware-architecture outcomes are simulations under the declared synthetic noise model; no quantum hardware was run. This repository is publicly hosted on GitHub for project sharing; the local simulation workflow did not submit to the hackathon portal, and portal submission is not claimed unless confirmed by the team. No license is added because member approval was not established.

## Main result

The exact reference values are cross-checked by dense and sparse spin Hamiltonians, a Qiskit Pauli operator, and an independent free-fermion spectrum. The nine canonical VQE starts are retained, including the unsuccessful optimizer termination. The separate restart diagnostic is clearly labeled and never overwrites that canonical failure. The table below pools all three initialization seeds within each field and graph; `shot SEM` is sampling uncertainty for a single run, whereas the pooled SD/SEM describe variation across starts.

| g | architecture | n | converged | failed | mean sampled E | mean abs total error | mean relative abs error | mean shot SEM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.5 | Processor A_branch | 3 | 3 | 0 | -3.10018 | 0.326855 | 0.0953755 | 0.0268557 |
| 0.5 | Processor B_ref12 | 3 | 3 | 0 | -3.12207 | 0.304964 | 0.0889877 | 0.026705 |
| 1 | Processor A_branch | 3 | 3 | 0 | -4.36019 | 0.398582 | 0.0837573 | 0.037403 |
| 1 | Processor B_ref12 | 3 | 3 | 0 | -4.40511 | 0.35366 | 0.0743175 | 0.0370011 |
| 1.5 | Processor A_branch | 3 | 2 | 1 | -6.0472 | 0.456691 | 0.0702181 | 0.0416518 |
| 1.5 | Processor B_ref12 | 3 | 2 | 1 | -6.00871 | 0.495184 | 0.0761366 | 0.0419727 |

Matched-seed sampled-energy difference, defined as A minus B over all fields and starts: **n=9, mean=0.0094401, sample SD=0.0534977, SEM=0.0178326**. These are descriptive paired statistics, not hardware-performance claims.

## Hamiltonian and conventions

The October 14, 2026 Master Challenge Guide (page 5) specifies the open four-site model `H = −J Σᵢ ZᵢZᵢ₊₁ − g Σᵢ Xᵢ`, with `J=1` and `g` values `0.5, 1.0, 1.5`. The Hamiltonian and open boundary are settled by the guide and spectrum checks. The guide says “magnetization” but does not define its axis or normalization. We therefore label the project conventions explicitly (`Mz_per_site`, `Mx_per_site`, `Mz2_normalized`) and do not present one as source-defined.

| g | exact E₀ | max spectrum diff | Σ⟨Xᵢ⟩ |
|---|---:|---:|---:|
| 0.5 | -3.42703 | 3.10862e-15 | 1.84051 |
| 1 | -4.75877 | 5.32907e-15 | 3.24038 |
| 1.5 | -6.50389 | 3.55271e-15 | 3.66011 |

## All canonical VQE starts

The table reports raw optimizer success separately from the project energy tolerance. The tolerance is a project reporting convention, not an organizer mandate.

| g | init seed | VQE energy | exact energy | Absolute error | optimizer success | termination |
| --- | --- | --- | --- | --- | --- | --- |
| 0.5 | 7 | -3.42703 | -3.42703 | 1.33582e-12 | 1 | CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH |
| 0.5 | 21 | -3.42703 | -3.42703 | 2.03393e-13 | 1 | CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH |
| 0.5 | 42 | -3.42703 | -3.42703 | 3.23741e-13 | 1 | CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH |
| 1 | 7 | -4.75877 | -4.75877 | 2.62226e-11 | 1 | CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH |
| 1 | 21 | -4.75877 | -4.75877 | 2.37499e-12 | 1 | CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH |
| 1 | 42 | -4.75877 | -4.75877 | 2.76223e-13 | 1 | CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH |
| 1.5 | 7 | -6.50389 | -6.50389 | 1.0747e-13 | 1 | CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH |
| 1.5 | 21 | -6.50389 | -6.50389 | 4.06608e-12 | 1 | CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH |
| 1.5 | 42 | -6.50359 | -6.50389 | 0.000301601 | 0 | STOP: TOTAL NO. OF ITERATIONS REACHED LIMIT |

## Fixed reference graphs

The guide presents these as reference examples and permits valid participant-designed alternatives. We freeze the two reference graphs before E4; this is not hardware calibration. Their topology descriptors are descriptive and not performance evidence.

| graph | nodes | edges | degree sequence | diameter | mean path length |
| --- | --- | --- | --- | --- | --- |
| A_branch | 5 | 4 | [3, 2, 1, 1, 1] | 3 | 1.8 |
| B_ref12 | 9 | 12 | [5, 4, 3, 3, 2, 2, 2, 2, 1] | 4 | 1.94444 |

## Reproduction

Tested with Python 3.13.16 and the exact pins in `requirements.txt`. From the repository root, create/activate a Python environment and install those pins. Then run the notebook using the standard `python3` kernel:

```bash
python3 -m nbconvert --to notebook --execute --output-dir .executed-output --ExecutePreprocessor.kernel_name=python3 main.ipynb
```

The notebook calls the canonical pipeline in a fixed order: exact checks → graph descriptors → nine-start VQE and ideal compilation → separate restart diagnostic → fixed-model noisy sampling → pooled/paired metrics and error decomposition → processed-data export → figures → generated documentation. The manifest is a frozen release snapshot and is not regenerated as part of this command. To run the separate supplementary study after the Stage 1 gate, use `python3 scripts/run_e4_ansatz_patterns.py`; it is not part of the default workflow.

## Supplementary E4 ansatz-pattern study

This separate, pre-frozen study reuses the nine canonical path starts and optimizes ring/star once per field and initialization seed. Each fitted logical circuit is compiled to both fixed A/B graphs; no per-architecture re-optimization or post-outcome map change is made. E4 remains supplementary and does not replace the primary path results.

| pattern | architecture | runs | optimizer successes | optimizer failures | mean CX | mean depth | mean routing SWAPs | mean noisy abs error | mean shot SEM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| path | Processor A_branch | 9 | 8 | 1 | 9 | 23 | 0 | 0.36933 | 0.0351789 |
| path | Processor B_ref12 | 9 | 8 | 1 | 9 | 23 | 0 | 0.381917 | 0.0352807 |
| ring | Processor A_branch | 9 | 9 | 0 | 27 | 55 | 5 | 0.813639 | 0.0405854 |
| ring | Processor B_ref12 | 9 | 9 | 0 | 12 | 28 | 0 | 0.528862 | 0.0377325 |
| star | Processor A_branch | 9 | 9 | 0 | 9 | 25 | 0 | 0.622585 | 0.0338163 |
| star | Processor B_ref12 | 9 | 9 | 0 | 9 | 25 | 0 | 0.618462 | 0.0338927 |

Matched-seed noisy-energy difference (A minus B) pooled over the nine field/seed pairs per pattern:

| pattern | matched pairs | mean A−B | sample SD | SEM |
| --- | --- | --- | --- | --- |
| path | 9 | -0.0125868 | 0.0699834 | 0.0233278 |
| ring | 9 | 0.284776 | 0.122527 | 0.0408422 |
| star | 9 | 0.00412326 | 0.0326867 | 0.0108956 |

Descriptive observation: the ring mapped to mean CX 27 / 12 and mean routing SWAPs 5 / 0 on A/B; its pooled paired noisy A−B mean was 0.284776 J (sample SD 0.122527, SEM 0.0408422). For star, mean CX was 9 / 9 and mean noisy absolute error was 0.622585 / 0.618462 J. These are finite local-simulation summaries, not hardware or causal performance claims.

The full per-run table and raw optimizer/count records are under `results/supplementary/`; shot SEMs and between-start SD/SEM are different quantities. No hardware conclusion is implied.

## Methods and evaluation

The canonical objective is the expectation of the source-confirmed Hamiltonian under the four-qubit RY/CX circuit. Initialization vectors are generated with NumPy `default_rng(seed)` from a fixed uniform interval. The exact parameter-shift derivative feeds L-BFGS-B. The solver receives only the Hamiltonian and current parameters; the exact ground-state energy is read later for classification and reporting.

Every field uses the same three independent initialization seeds. No extra restart is silently counted as an independent seed. The failed optimization status remains visible. In the separate restart diagnostic, saved failed-run parameters are used to start a new optimization; that output is stored apart from canonical data.

The graphs are the guide's fixed reference examples. Their use is motivated by reproducibility and a direct comparison on the specified A/B pair, not by post-hoc selection for favorable outcomes. The guide permits valid alternatives, but this project does not change the primary maps after observing results.

## Compilation and resource evidence

The logical circuit is compiled once for each graph with the same requested basis, optimization level, layout/routing methods, and transpiler seed. The compilation instrumentation records the actual pass trace and the output of routing-related passes.

- `cx_count` and `depth` are read from the compiled circuit.
- Routing-pass SWAPs and final-circuit SWAP gates are separate metrics.
- Initial and final layouts are saved; idle physical wires are not treated as logical qubits.
- The compiled state is reduced back to logical qubits and checked against the original ideal state.
- No noisy-state fidelity is inferred from Pauli measurement counts.

## Sampling, uncertainty, and interpretation

Z and X observables are estimated in separate measurement bases with separate deterministic simulator seeds. For each basis, the declared shot count is used; the total shots per energy are the sum of the group shots. The combined shot SEM is computed from independent per-group sample variances in quadrature.

The per-run shot SEM quantifies finite-sample uncertainty under this simulator setup. The sample SD and SEM across initialization seeds quantify between-start variability. The pooled A/B comparison is descriptive; it does not by itself establish a causal or hardware ranking. The paired statistic matches A and B on both field value and VQE initialization seed.

The error decomposition evaluates exact and sampled Hamiltonian contributions separately: the three ZZ bonds and the four X fields. It reports signed component deviations, their sum, total noisy error, and a closure residual. Opposite-signed component errors can cancel, so the total absolute error is not the sum of component absolute errors.

## Interpretation boundary

The synthetic noise assumptions are applied to simulated gates and readout only. They are not measured calibration data, and the five- and nine-node graphs do not identify actual quantum processors.

The report does not claim a statistically significant architecture winner, a hardware advantage, or generalization beyond the declared circuit, noise model, seeds, fields, and graph pair. The plotted error bars are explicitly ±1 shot SEM, not confidence intervals.

The undefined magnetization wording is retained as an ambiguity. It does not make the Hamiltonian uncertain: the source specifies the open-chain terms and independent spectra agree.

## Metric definitions

- `E₀` is the smallest eigenvalue of the open-chain Hamiltonian.
- Signed ideal error is `E_VQE − E₀`; absolute ideal error is its magnitude.
- Relative absolute error is `|E_est − E₀| / |E₀|`.
- A noisy estimate uses the sampled ZZ and X contributions together.
- Total noisy signed error is sampled energy minus `E₀`.
- Per-run shot SEM is not a between-seed SEM and is not labeled a confidence interval.
- The pooled table's SD uses the sample convention (`ddof=1`).
- The paired difference is sampled A energy minus sampled B energy.
- Optimizer success is the optimizer-reported status; the project tolerance is a separate flag.
- Routing SWAP evidence is collected from the observed pass DAGs; final SWAP gates are counted separately.

## Fixed experiment ledger

- Problem instance: the guide's four-site open chain.
- Coupling: `J=1`; the three fields appear in `data/raw/hamiltonian_s1.json`.
- Ansatz: four RY layers and three entangler sweeps in the canonical run.
- Parameter count: sixteen for the canonical configuration.
- Canonical initialization seeds: 42, 7, and 21.
- Optimizer: L-BFGS-B with exact parameter-shift gradients.
- Basis: `rz`, `sx`, `x`, and `cx`.
- Transpilation: optimization level 1; Sabre layout and routing; seed 42.
- Noise and shot settings: frozen in both processor JSON files and the run tables.
- Primary architecture rows are never selected based on their measured outcomes.

## Suggested reading order

1. Read the governing-source notes in `docs/SOURCES.md`.
2. Check the model text in `data/raw/hamiltonian_s1.json`.
3. Inspect the exact cross-check before interpreting VQE errors.
4. Read all nine canonical starts, including the failure.
5. Compare graph-resource evidence separately from sampled energy.
6. Read the pooled table with its `row_type` and uncertainty definitions.
7. Review the signed ZZ/X decomposition before interpreting total error.
8. Use the manifest only as the hash snapshot for this frozen repository state.
9. Treat E4 as supplementary and consult its frozen plan before invoking it.
10. Review the scope limits before making any claim outside simulation.

## Reproduction setup

From a clean checkout or filesystem copy, create a virtual environment using the Python version used for the recorded run. Install the exact dependencies with `python3 -m pip install -r requirements.txt`. The registered Jupyter kernel name used by the notebook is `python3`.

The nbconvert command above writes the executed notebook copy to a temporary output directory. The pipeline writes regenerated deterministic project outputs under the project tree. Review `git status --short` if the directory is a Git checkout; differences must be investigated, not automatically discarded.

The standalone clean-room runner also executes pytest, writes verification logs outside the repository, and retains its scratch copy. It is a filesystem-copy check only. It does not prove that a remote Git clone, hosted CI, portal, or hardware job occurred.

The default notebook intentionally does not invoke the E4 runner, the historical COBYLA runner, or archived stress/noise experiments. The canonical reproduction script is the single source of the default pipeline order.

## Key files

- `main.ipynb`: executable analysis and visible result tables/figures.
- `report.md`: canonical Markdown report at repository root, presenting the verified Phase 1 A/B benchmark analysis and the clearly separated proposed Processor D design ideology.
- `src/problem.py`, `src/ansatz.py`, `src/vqe.py`: model, ansatz and optimizer. `make_ansatz` retains its historical default of two repetitions; the canonical workflow explicitly uses three.
- `src/routing.py`, `src/metrics.py`, `src/visualization.py`: evidence-based compilation, metrics and plots.
- `data/raw/hamiltonian_s1.json`: source-verified model inputs; not a substitute for missing source documents.
- `results/raw/`: exact and VQE/noisy count records. `results/tables/`: generated tables; `data/processed/`: analysis-ready copies with a data dictionary.
- `processors/`: frozen A/B reference graphs and synthetic noise settings. `results/experiment_manifest.json`: path-safe SHA-256 snapshot.
- `docs/`: source, specification, QA, glossary, reproduction and rubric notes. `docs/EXPERIMENT_PLAN.md` freezes the supplementary E4 design.

## Scope and limitations

This repository is publicly hosted on GitHub. No hardware execution, portal access, organizer contact, team/problem selection check, or hackathon portal submission is claimed; the local workflow did not submit to the hackathon portal. The separate AI policy referenced by the instructions was not supplied; contributors must confirm the applicable policy. No license is included because explicit approval from all four members was not obtained. The supplied source ZIP and `Problem_Statment_Details.pdf` were absent from the available workspace; the private handoff records this provenance limitation. No ZIP-based extraction or checksum comparison is claimed.
