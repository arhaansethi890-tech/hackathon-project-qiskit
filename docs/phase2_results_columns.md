# results/tables/ — required CSV files and columns

| File | One row per | Columns |
|------|-------------|---------|
| `bell.csv` (all PS) | pair × condition | pair, pair_distance, condition (ideal/noisy), two_qubit_gates, XX, XX_se, YY, YY_se, ZZ, ZZ_se, fidelity, fidelity_se |
| `resources.csv` (all PS) | circuit × processor | ps, circuit_label, processor (A/B/D), executable, logical_qubits, physical_qubits, logical_2q, two_q, depth, two_q_depth, swaps, routing_overhead_2q |
| `s1_results.csv` (S1) | N × g × layers | N, g, layers, best_energy, exact_E0, energy_err, fidelity, fidelity_2, mx, mx_exact, czz_nn, czz_nn_exact, mz2, mz2_exact, mz, optimizer_calls, n_params, two_q_on_D |
| `s1_noisy.csv` (S1) | g | g, layers, mx_noisy, czz_nn_noisy, mz2_noisy, energy_noisy, fidelity_noisy_dm |
| `s2_curves.csv` (S2) | order × steps × t | order, steps, t, z0, ms, z0_exact, ms_exact, z0_err, ms_err, loschmidt (optional) |
| `s2_loglog.csv` (S2) | order × steps | order, steps, state_error |
| `s2_zz.csv` (S2) | processor × construction | processor, basis, zz_construction (cx/rzz), two_q_per_step, depth_per_step |
| `s3_scan.csv` (S3) | processor × scale × steps | processor, noise_scale, steps, fidelity_noisy, fidelity_trotter_ideal, ms_noisy, ms_noisy_se, ms_exact, logical_2q, swap_2q, two_q |
| `s3_summary.csv` (S3) | processor × scale | processor, noise_scale, n_star, fidelity_at_n_star |
| `mitigation.csv` (optional bonus) | method | method, ms_raw, ms_mitigated, extra_shots |
