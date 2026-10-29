# Supplementary E4 experiment plan — frozen before execution

## Question
How do path, ring, and star four-qubit RY/CX entangler patterns behave when compiled to the same fixed A/B coupling graphs, under the already declared level-1 Sabre workflow? This is a supplementary analysis, not part of the canonical PS-S1 notebook pipeline and not a replacement for the primary path-ansatz results.

## Graphs and freeze
Use `processors/processor_A.json` and `processors/processor_B.json` exactly as frozen before this study. They are the October 14 guide's reference graphs (5 and 9 nodes); no edge, node, layout, transpiler setting, seed, shot count, or primary result is changed after seeing E4 outcomes. No new map is optimized against the observed outcomes.

## Circuit definitions
All patterns use four qubits, four RY layers, three entangler sweeps, and 16 trainable parameters. Path has edges (0,1),(1,2),(2,3), giving 9 logical CX gates; ring adds (3,0), giving 12; star uses (0,1),(0,2),(0,3), giving 9. Each parameter vector is initialized once with NumPy `default_rng(seed)` and optimized once per (g, VQE seed, pattern) using the existing exact parameter-shift/L-BFGS-B implementation. The same optimized logical circuit is mapped to A and B; there is no per-architecture re-optimization. Existing canonical path results are reused, not re-fit.

## Fixed design and outputs
Fields are 0.5, 1.0, 1.5; initialization seeds are 42, 7, 21. The new ring/star work therefore adds 18 optimizations (two patterns × three fields × three starts); all 27 pattern/field/start combinations are summarized. Each logical circuit is compiled to both fixed graphs with basis `{rz,sx,x,cx}`, optimization level 1, Sabre layout/routing and transpiler seed 42. Record pass evidence, initial/final layouts, routing SWAPs, final circuit SWAP gates, CX, depth, and semantic fidelity. For each mapped circuit, additionally sample Z and X bases with 4096 shots per basis under the same fixed synthetic noise model used in the primary study; simulator seeds are obtained only through `derive_simulator_seed`, with pattern names included in the variant key to avoid collisions.

## Outcomes and analysis
Report every run, including optimizer failures, without filtering or retrying. Report absolute and signed ideal-energy error against the independent exact ground state; per-architecture compiled resource metrics; the compiler preservation check; and sampled noisy energy with its Pauli-group SEM. Keep the E4 tables, raw JSON, and figures in `results/supplementary/`. Distinguish shot SEM from between-start variation. Do not interpret small observed differences as a hardware performance claim or causal estimate.

## Execution status

This document was frozen before E4 execution. The separate command `python3 scripts/run_e4_ansatz_patterns.py` completed successfully on 2026-10-15 (final recorded run: exit 0, about 121 seconds). It produced 54 mapped A/B result rows from 27 pattern/field/start combinations, including 18 new ring/star optimizations, and 108 unique independent noisy-basis simulator seeds. The two E4 figures were generated from those tables. The default reproduction pipeline does not run E4; it only preserves and displays already-saved supplementary outputs. The primary maps, settings, and Stage 1 artifacts were not changed by the E4 runner.
