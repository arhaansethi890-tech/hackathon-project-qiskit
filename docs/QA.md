# Quality assurance

The project uses explicit assertions and tests for Hamiltonian consistency, exact diagonalization, observable estimators, noise settings, ansatz parameter dimensions, transpilation pass evidence, compiler-output cross-checks, semantic state preservation, manifest hashes, notebook execution, and supplementary E4 isolation. The preserved optimizer failure is tested as a distinct outcome; no failure is deleted or retried in the canonical table.

Final validation must be rerun in the pinned environment and recorded with exact commands, exit codes, runtimes, counts, and logs. A clean filesystem copy is not a Git clone. A clone must be performed only from a real Git repository if the required clean-clone gate is specified; otherwise report NOT RUN. No external push or publication is part of validation.

The project tests do not prove hardware performance, portal selection, organizer approval, contributor consent, or AI-policy compliance. See the private handoff for immutable-input hashing and the unavailable-ZIP limitation.
