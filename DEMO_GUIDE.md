# Judge Demo Guide

## Three-minute walkthrough

Keep `main.ipynb` open on the results and figures, with `report.md` available for the full tables. The notebook loads the checked-in results by default. Do not spend the presentation waiting for VQE to run.

### 0:00–0:30 — State the problem and the contribution

“We study the open-chain transverse-field Ising model on the seven locked N=4 instances. Our submission combines a reproducible three-seed HVA layer study with a Processor D design that supports the required Bell experiment and the PS-S1 circuits. We compare D against the supplied A and B processors using the same logical circuits and official noise settings.”

Show the project summary in `report.md`. State up front that all processor results are simulations under the supplied synthetic model.

### 0:30–1:10 — Establish reproducibility

Show `main.ipynb` and its saved-result default. Point to the locked input files under `data/s1/`, the fixed seeds 0, 1, and 2, the exact E0/E1 references, and the generated result tables. Mention that the optimizer scan stores a checkpoint after each completed field and layer, so a long run can continue after interruption.

### 1:10–1:50 — Explain the physics result

Show `phase2_s1_observables.png` and `phase2_s1_layer_study.png`. Explain that increasing transverse field raises `mx`, while nearest-neighbour `Czz` and normalized `mz²` decrease. With only four sites, this is a smooth finite-size crossover, not a sharp thermodynamic phase transition. The minimum successful layers on the locked grid are 4, 4, 4, 3, 4, 3, and 3 from low to high field; all seven meet the `10⁻³` energy tolerance.

### 1:50–2:25 — Make the Processor D case

Show `phase2_s1_resources.png` and `processor_D_topology.png`. D uses a six-qubit cycle with opposite chords and native RZZ. On the seven selected N=4 HVA circuits, it averages 10.7 compiled two-qubit gates and depth 28.0, compared with 21.4 compiled two-qubit gates and depth 42.3 for both A and B. Explain the mechanism: the HVA ZZ rotation maps to one native RZZ on D, while the supplied A/B basis uses two CX gates. The design also contains an open path for PS-S1 and supports N=6.

### 2:25–2:45 — Show validation and noise results

Show the Bell fidelity figure and report table. The direct pair is `0–1`; the farthest pair is `0–3`. Their noisy simulated fidelities are `0.9598 ± 0.0022` and `0.9459 ± 0.0025`, respectively, using 4,096 shots per Pauli basis. Then point to the required noisy D PS-S1 table for `g=0.5, 1.0, 2.0`.

### 2:45–3:00 — Close with a precise claim

“The evidence supports a resource-efficiency result within the locked small-circuit simulation: D reduces compiled two-qubit gate count for these HVA circuits while preserving the ideal state. The supplied noise model does not establish a hardware advantage, and our results do not claim one.”

## Likely judge questions

**Why choose D?** The graph contains the needed cycle and path patterns, supports the optional six-qubit tier, and its native RZZ basis reduces the compiled two-qubit count for these HVA circuits under the supplied mapping.

**Did you run on quantum hardware?** No. The results use the official local Aer simulation and synthetic noise model.

**Is the layer trend monotonic?** No. The observed counts are 4, 4, 4, 3, 4, 3, and 3. Report the measured grid as-is; do not describe it as a monotonic law.

**What does the three-seed table add?** It makes the spread among the required initialization seeds visible at the selected layer, rather than presenting only the best start.

**What is optional?** N=6 is a bonus tier. The checked-in headline results are the required N=4 cases. Use `python scripts/run_phase2_s1.py --n6-only --resume` only when there is enough time and compute to pursue the bonus.

## Before presenting

- Open the notebook and confirm the saved tables and figures display.
- Read the report's result tables and the interpretation limits.
- If the supplemental noisy A/B/D table is desired, install `requirements.txt` and run `python scripts/run_phase2_s1.py --supplement-only` ahead of the presentation.
- Keep the optional N=6 run out of the timed live demo.
