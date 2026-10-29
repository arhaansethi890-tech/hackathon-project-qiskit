# PS-S1 simulation report

## Pooled A/B comparison (first result)

| g | architecture | n | converged | failed | mean sampled E | mean abs total error | mean relative abs error | mean shot SEM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.5 | Processor A_branch | 3 | 3 | 0 | -3.10018 | 0.326855 | 0.0953755 | 0.0268557 |
| 0.5 | Processor B_ref12 | 3 | 3 | 0 | -3.12207 | 0.304964 | 0.0889877 | 0.026705 |
| 1 | Processor A_branch | 3 | 3 | 0 | -4.36019 | 0.398582 | 0.0837573 | 0.037403 |
| 1 | Processor B_ref12 | 3 | 3 | 0 | -4.40511 | 0.35366 | 0.0743175 | 0.0370011 |
| 1.5 | Processor A_branch | 3 | 2 | 1 | -6.0472 | 0.456691 | 0.0702181 | 0.0416518 |
| 1.5 | Processor B_ref12 | 3 | 2 | 1 | -6.00871 | 0.495184 | 0.0761366 | 0.0419727 |

All measurements are local simulations under the stated synthetic channel model. The pooled means average three VQE initializations per field and architecture; the nine matched pairs are the independent comparison units for the descriptive paired statistic. Shot SEM is not a confidence interval.

### Paired sampled-energy difference

A minus B over the nine matched `(g, initialization seed)` pairs: **mean 0.0094401; sample SD 0.0534977; SEM 0.0178326; n=9**. No CI is claimed.

### Sampled error decomposition

The sampled energy is the sum of its separately measured ZZ and X contributions. These are mean signed contributions to noisy-minus-exact error over the three fields and three starts per architecture; component errors can have opposite signs.

| architecture | mean ZZ contribution | mean X contribution | mean total signed error |
| --- | --- | --- | --- |
| Processor A_branch | 0.149143 | 0.2449 | 0.394043 |
| Processor B_ref12 | 0.151747 | 0.232856 | 0.384602 |

The decomposition closes to floating-point precision on a per-run basis (check `noisy_error_decomposition.csv`). `shot_sem_total` combines independent Pauli-group SEMs in quadrature.

## Supplementary E4 ansatz-pattern study

The experiment followed the frozen `docs/EXPERIMENT_PLAN.md`: 27 pattern/field/start combinations, 18 new ring/star optimizations, and identical logical parameters mapped to both A/B graphs. The primary maps/settings were not changed. This table reports generated means over starts; it is separate from the canonical Stage 1 comparison.

| pattern | architecture | runs | optimizer successes | optimizer failures | mean CX | mean depth | mean routing SWAPs | mean noisy abs error | mean shot SEM |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| path | Processor A_branch | 9 | 8 | 1 | 9 | 23 | 0 | 0.36933 | 0.0351789 |
| path | Processor B_ref12 | 9 | 8 | 1 | 9 | 23 | 0 | 0.381917 | 0.0352807 |
| ring | Processor A_branch | 9 | 9 | 0 | 27 | 55 | 5 | 0.813639 | 0.0405854 |
| ring | Processor B_ref12 | 9 | 9 | 0 | 12 | 28 | 0 | 0.528862 | 0.0377325 |
| star | Processor A_branch | 9 | 9 | 0 | 9 | 25 | 0 | 0.622585 | 0.0338163 |
| star | Processor B_ref12 | 9 | 9 | 0 | 9 | 25 | 0 | 0.618462 | 0.0338927 |

Pooled matched A-minus-B sampled-energy differences by pattern (nine field/seed pairs):

| pattern | matched pairs | mean A−B | sample SD | SEM |
| --- | --- | --- | --- | --- |
| path | 9 | -0.0125868 | 0.0699834 | 0.0233278 |
| ring | 9 | 0.284776 | 0.122527 | 0.0408422 |
| star | 9 | 0.00412326 | 0.0326867 | 0.0108956 |

Descriptive observation: the ring mapped to mean CX 27 / 12 and mean routing SWAPs 5 / 0 on A/B; its pooled paired noisy A−B mean was 0.284776 J (sample SD 0.122527, SEM 0.0408422). For star, mean CX was 9 / 9 and mean noisy absolute error was 0.622585 / 0.618462 J. These are finite local-simulation summaries, not hardware or causal performance claims.

See `results/supplementary/tables/E4_ansatz_patterns.csv` for each run and `E4_paired_differences.csv` for field-specific pairs. Shot SEM is per run; the paired SEM is across matched initialization/field pairs.

## Exact references

| g | exact E₀ | max spectrum diff | Σ⟨Xᵢ⟩ |
| --- | --- | --- | --- |
| 0.5 | -3.42703 | 3.10862e-15 | 1.84051 |
| 1 | -4.75877 | 5.32907e-15 | 3.24038 |
| 1.5 | -6.50389 | 3.55271e-15 | 3.66011 |

The maximum spectral discrepancies in the table are checked directly from generated spectra; the full eigenvalue spectra and exact observables are retained in the cross-check artifacts. The source-confirmed model is an open chain; the undefined magnetization axis/normalization remains explicitly disclosed.

## Canonical VQE and separate restart

All nine starts, including the seed-42 `g=1.5` iteration-limit failure, are visible in the README table and `ideal_architecture_results.csv`. The restart diagnostic is stored separately and is not substituted for that canonical run. The exact reference is used only for post-optimization classification and error measurement, not as the VQE objective.

## Architecture, routing and noise

The two fixed graphs are the guide's A/B references, with five and nine physical nodes. Compilation uses basis `{rz,sx,x,cx}`, level one, Sabre layout/routing and transpiler seed 42. The generated tables record actual pass traces, initial/final layouts, routing SWAP evidence, final-circuit SWAP count, CX count, depth, and semantic preservation. No hardware calibration is implied. The noise model uses per-gate depolarizing channels and symmetric readout flips as recorded in the processor JSON and per-run results; Z/X observables use independent simulator seeds and 4096 shots each.

## Proposed Processor D Design Ideology (Proposal Only — Not a Phase 1 Benchmark)

This section presents a conceptual architecture proposal addressing the hackathon judging criterion for Phase 1. As clarified by organizers, implementation and benchmarking of Processors C and D are not Phase 1 requirements; this section documents design rationale, topological trade-offs, and future empirical verification criteria without claiming implementation or simulation outcomes.

### 1. Measured and Simulated Phase 1 Evidence (Verified Repository Baseline)

The empirical baseline established in this repository rests strictly on the two fixed reference graphs under the declared synthetic noise model:
- **Processor A (`A_branch`)**: 5 nodes, 4 undirected edges `(0,1), (1,2), (1,3), (3,4)`, degree sequence `[3, 2, 1, 1, 1]`, tree (diameter 3, no cycles).
- **Processor B (`B_ref12`)**: 9 nodes, 12 undirected edges, degree sequence `[4, 4, 3, 3, 3, 3, 2, 2, 2]`, diameter 4, contains multiple cycles (including 3 4-cycles $C_4$).
- **Canonical Open-Chain VQE Benchmark**: For the primary 4-site open TFIM ($H = -J \sum_{i=0}^2 Z_i Z_{i+1} - g \sum_{i=0}^3 X_i$, $J=1$, $g \in \{0.5, 1.0, 1.5\}$), the 16-parameter `reps=3` nearest-neighbor CX ansatz compiled to exactly 9 CX, depth 23, and 0 routing SWAPs on both Processor A and Processor B across all nine canonical starts. Under the declared synthetic noise model (single-qubit $p=0.001$, CX $p=0.005$, readout $p=0.01$), the matched-seed paired energy difference $E_{\text{noisy},A} - E_{\text{noisy},B}$ over the 9 pairs yielded mean +0.00944 J, sample SD 0.05350 J, SEM 0.01783 J ($n=9$). The standard error of the mean exceeds the mean, demonstrating no statistically resolvable performance advantage between A and B for the open-chain problem.
- **Supplementary E4 Ansatz-Pattern Study**: When evaluating non-linear entangling structures on these fixed graphs, routing overhead diverged:
  - On Processor A (tree), the 12-CX logical ring ansatz required 5 routing SWAPs, resulting in mean compiled CX 27 and depth 55, with mean noisy absolute error 0.813639 J.
  - On Processor B (mesh containing cycles), the ring ansatz mapped with 0 routing SWAPs, compiling to 12 CX and depth 28, with mean noisy absolute error 0.528862 J.
  - The paired ring noisy difference (A minus B) was mean +0.284776 J (sample SD 0.122527 J, SEM 0.0408422 J, $n=9$). E4 remains supplementary evidence illustrating that topological mismatch induces SWAP overhead on cycle circuits.

### 2. Conceptual Processor D Proposal (Design Rationale & Trade-offs)

- **Proposed Topology**: A 4-qubit simple cycle graph ($C_4$), defined on physical vertices $V = \{0, 1, 2, 3\}$ with 4 bidirectional edges:
  $$E = \{(0, 1), (1, 2), (2, 3), (3, 0)\}$$
- **Topological Fit and Direct Interaction Mapping**:
  - *Open Chain Mapping*: The 4-site open-chain TFIM requires interactions across three nearest-neighbor bonds: `(0,1)`, `(1,2)`, and `(2,3)`. The path subgraph $P_4 \subset C_4$ natively executes these interactions with 0 routing SWAPs and identity layout $q_i \mapsto i$.
  - *Periodic / Ring Flexibility*: The additional coupler `(3,0)` natively closes the loop. Should periodic boundary conditions ($Z_3 Z_0$) or ring-entangled ansätze be deployed, the circuit compiles directly with 0 routing SWAPs and minimal depth, avoiding the 5-SWAP routing penalty observed on acyclic trees like Processor A.
  - *Graph Diameter & Homogeneity*: $C_4$ is 2-regular (every node has degree 2) with diameter 2. Unlike Processor A (degrees 3, 2, 1) and Processor B (degrees 4, 3, 2), every physical qubit experiences identical topological connectivity, eliminating degree-heterogeneity and routing bottlenecks.
- **Comparison Against Baselines**:
  - *vs. Minimal Linear Path ($P_4$, 4 nodes, 3 edges)*: $P_4$ has diameter 3 and requires SWAP gates to interact qubits 0 and 3. $C_4$ adds exactly one physical coupler `(3,0)`, reducing diameter from 3 to 2 and supporting cyclic permutations without increasing node count.
  - *vs. Processor A (`A_branch`, 5 nodes, 4 edges)*: Processor A leaves physical node 4 as a leaf and contains a high-degree hub (node 1) that cannot close loops. $C_4$ uses fewer physical qubits (4 vs 5) while providing cycle closure.
  - *vs. Processor B (`B_ref12`, 9 nodes, 12 edges)*: Processor B achieves zero-SWAP routing for both path and ring circuits, but requires 9 physical qubits (5 idle spectator qubits during a 4-qubit benchmark). $C_4$ provides the identical zero-SWAP routing capability for $P_4$ and $C_4$ circuits with a compact, dedicated 4-qubit footprint.
- **Physical Assumptions, Coupler Overheads & Limitations**:
  - *Coupler Overhead*: In superconducting transmon architectures, closing a planar 4-qubit loop requires routing an additional transmission-line or capacitive coupler `(3,0)`. An extra coupler introduces additional potential pathways for parasitic stray capacitive coupling, residual $ZZ$ interaction, and idle qubit dephasing.
  - *Crosstalk Not Measured*: While $C_4$ eliminates idle spectator qubits present in Processor B, any potential crosstalk mitigation or frequency crowding penalty is purely an unmodeled physical conjecture; the project's synthetic noise model does not incorporate spatial crosstalk or frequency collision physics.
  - *Scale Invariance*: $C_4$ is purpose-built for 4-site systems. It does not generalize to larger problem instances ($N > 4$) without expansion to larger 2D grid/heavy-hex layouts.

### 3. Future Empirical Verification (Requirements for a Phase 2 Study)

To validate this proposal empirically in a future development phase, the following evaluations would be required:
1. **Physical or Calibrated Simulation**: Incorporate calibrated hardware backend noise (e.g., via fake backend or pulse-level Hamiltonian models) reflecting actual transmon qubit frequency assignments and residual $ZZ$ crosstalk on the $C_4$ loop.
2. **Compilation Benchmarking**: Transpile the canonical open-chain and periodic ansätze onto the $C_4$ coupling map to verify zero-SWAP routing pass schedules and analyze gate parallelism.
3. **Comparative Noisy Execution**: Execute identical randomized benchmarking and noisy VQE runs comparing $P_4$, $C_4$, and the full 9-node $B$ mesh under identical gate error rates to isolate the impact of idle spectators vs. extra coupler calibration overhead.

## Provenance and limitations

The October 14, 2026 guide is the governing specification. The input Hamiltonian data file records the exact guide page for the model. The magnetization wording is genuinely underspecified; the Hamiltonian and boundary condition are not. The supplied source ZIP and `Problem_Statment_Details.pdf` were absent from the workspace, so ZIP extraction/hash verification is unavailable. This repository is publicly hosted on GitHub. No quantum hardware execution, portal contact, or hackathon portal submission is claimed; the local simulation workflow did not submit to the hackathon portal. The separate AI policy was not supplied, and no project license was added without all-member approval.
