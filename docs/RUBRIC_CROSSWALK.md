# File-level rubric crosswalk

Weights are transcribed from the October 14, 2026 Master Challenge Guide, page 7. This maps evidence to files; it is not a score prediction.

| Guide category | Evidence files | What is established / not established |
|---|---|---|
| Scientific & algorithmic correctness (30 points) | `src/problem.py`, `src/qiskit_problem.py`, `run_exact_validation.py`, `results/tables/exact_crosscheck.csv`, `run_benchmark.py`, `results/raw/vqe_runs.json`, `results/tables/ideal_architecture_results.csv` | Independent exact references, per-start VQE outputs and optimizer classification, preserved failure, separate restart, and project observables. Not hardware accuracy. |
| Processor A/B architectural analysis & creativity (35 points) | `processors/processor_A.json`, `processors/processor_B.json`, `src/graph_analysis.py`, `run_graph_analysis.py`, `src/routing.py`, `results/tables/graph_descriptors.csv`, `results/tables/ideal_architecture_results.csv`, `results/tables/noisy_results.csv`, `results/supplementary/` | Uses the guide's reference graphs, which it permits as examples alongside valid participant-designed graphs; actual compiler/resource evidence and fixed-model simulation are reported. Topology descriptors are not performance metrics. E4 is separate. |
| Reproducibility & code quality (20 points) | `requirements.txt`, `main.ipynb`, `pytest.ini`, `tests/`, `.github/workflows/ci.yml`, `make_manifest.py`, `results/experiment_manifest.json`, `docs/CLEAN_REPRODUCTION.md` | Pinned environment, standard Python kernel workflow, path-safe hashes, tests, and clean-room runner. No hosted CI execution is claimed. |
| Documentation & visualizations (15 points) | `README.md`, `report.md`, `AI_DISCLOSURE.md`, `docs/SOURCES.md`, `docs/SPEC_DECISIONS.md`, `docs/GLOSSARY.md`, `docs/DATA_DICTIONARY.md`, `docs/RUBRIC_CROSSWALK.md`, `results/figures/` | Scope, methods, assumptions, source trail, data definitions, results, and limitations. AI-policy compliance is not asserted. |

Outside this crosswalk: portal team/problem selection, hardware access, organizer communication, submission, publication, contributor approval/licensing, and AI-policy compliance. None is claimed.
