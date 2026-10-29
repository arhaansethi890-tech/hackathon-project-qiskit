# Glossary

- **A/B:** The guide's two reference coupling graphs: A has 5 physical nodes and B has 9. The labels refer to simulated graph configurations, not calibrated devices.
- **Canonical start:** One independent initialization of the fixed VQE ansatz for a specified field value and seed.
- **Exact reference:** Numerically computed ground-state energy from independently cross-checked Hamiltonian implementations; used for post-run error measurement, not VQE optimization.
- **Ideal energy error:** `E_VQE - E_0` (signed) or its absolute value, explicitly labeled.
- **Optimizer success:** The optimizer's own termination flag. It is not identical to meeting the project reporting tolerance.
- **Project energy tolerance:** A local reporting convention; not specified by the organizer guide.
- **Routing SWAP evidence:** SWAP operations observed in the output DAG of routing-capable compilation passes. The final-circuit SWAP gate count is separately recorded.
- **Shot SEM:** Standard error of a Pauli-group energy estimate from finite shot counts. Independent Z/X group SEMs are combined in quadrature.
- **Between-start sample SD/SEM:** Descriptive variation across independent VQE initialization seeds; not the same as shot SEM.
- **Paired difference:** For each matching field and VQE seed, sampled A energy minus sampled B energy.
- **Magnetization convention:** The guide does not define axis/normalization. Project observables are labeled `Mz_per_site`, `Mx_per_site`, and `Mz2_normalized`.
- **E4:** Separate, frozen supplementary path/ring/star ansatz-pattern study on the same fixed A/B maps. It is not run by default and does not modify primary results.
