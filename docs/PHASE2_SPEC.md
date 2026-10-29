# QFF 2026 Phase 2 - PS-S1 checklist

This repository continues the same team's PS-S1 entry. The Phase 2 Simulation
Problem Statements document supersedes the Phase 1 numerical conventions and
locks all inputs for the final benchmark.

## Locked PS-S1 inputs

- Open-chain TFIM, `J=1`, `N=4` required; `N=6` optional bonus.
- `g = 0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 2.00`.
- VQE only, using an HVA with two shared parameters per layer.
- Initialization seeds `0, 1, 2`, with `numpy.random.default_rng(seed)` and
  parameters drawn uniformly from `(-pi, pi)`.
- Find the smallest layer count reaching `|E - E0| < 1e-3` at each field.
- Report `mx`, nearest-neighbour `czz_nn`, `mz2`, the symmetry diagnostic `mz`,
  exact references, `F`, `F2`, optimizer calls, and parameter count.
- On Processor D, report noisy density-matrix observables and fidelity at
  `g = 0.5, 1.0, 2.0`.

## Common Phase 2 work

- Bell state `|Phi+>` on a direct D edge and on a farthest-apart D pair; ideal
  and noisy runs for `XX`, `YY`, `ZZ`, 4,096 shots per basis, and fidelity with
  its standard error.
- Processor D JSON passes `tools/check_processor_d.py`; the topology, native
  gates, error rates, and measured-bottleneck justification are frozen and
  included in the report.
- D uses the allowed native-RZZ gate set at the official two-qubit error rate.
  The same HVA unitary is built with CX-RZ-CX on A/B and one RZZ per ZZ bond
  on D, making the compiled two-qubit-cost trade-off explicit.
- Resource table covers the required A, B, and D benchmarks with the official
  `qff_sim.py` metric definitions and settings.
- `main.ipynb` runs from the repository root. The default notebook loads the
  checked-in result tables; set `RECOMPUTE = True` to regenerate them.

## Official settings

Basis `{rz, sx, x, cx}`, optimization level 1, SABRE layout/routing, transpiler
seed 42, simulator seed 42, and synthetic noise `p1=0.001`, `p2=0.005`,
`p_readout=0.01`. Bell and Z-measurement runs use 4,096 shots. The official
`qff_sim.py` helper is kept unchanged; extra team analysis is kept in
`scripts/run_phase2_s1.py`.
