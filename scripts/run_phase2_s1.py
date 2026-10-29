"""Reproducible QFF 2026 Phase 2 PS-S1 and common Bell benchmark.

The organizer-provided qff_sim.py is kept unchanged. This module applies its
locked processors, noise model, measurements, and transpilation settings to the
team's PS-S1 VQE study.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from qiskit.quantum_info import SparsePauliOp, Statevector, state_fidelity
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import qff_sim as qff  # noqa: E402

DATA_DIR = ROOT / "data" / "s1"
TABLES_DIR = ROOT / "results" / "tables"
RAW_DIR = ROOT / "results" / "raw"
FIGURES_DIR = ROOT / "results" / "figures"
G_GRID = (0.25, 0.50, 0.75, 1.00, 1.25, 1.50, 2.00)
SEEDS = (0, 1, 2)
NOISY_G = (0.50, 1.00, 2.00)
ENERGY_TOL = 1e-3
DEFAULT_MAX_LAYERS = 12
OPTIMIZER_MAXITER = 800

PROCESSORS = {
    "A": qff.PROCESSOR_A,
    "B": qff.PROCESSOR_B,
}


def _d_path() -> Path:
    return ROOT / "processors" / "processor_D.json"


def load_d() -> dict[str, Any]:
    return qff.load_processor(str(_d_path()))


def _instance(n: int, g: float) -> tuple[SparsePauliOp, float, float]:
    path = DATA_DIR / f"tfim_open_N{n}_g{g:.2f}.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing locked Phase 2 instance: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    op = SparsePauliOp.from_list(
        [(str(label), float(coefficient)) for label, coefficient in payload["operator"]]
    )
    exact0 = float(payload["meta"]["E0_exact"])
    exact1 = float(payload["meta"]["E1_exact"])
    return op, exact0, exact1


def _bind(circuit, parameters, values):
    return circuit.assign_parameters(
        {parameter: float(value) for parameter, value in zip(parameters, values)},
        inplace=False,
    )


def _optimize_hva(n: int, g: float, layers: int, seed: int, hamiltonian: SparsePauliOp) -> dict[str, Any]:
    circuit, parameters = qff.hva_ansatz(n, layers, zz_mode="cx")
    rng = np.random.default_rng(seed)
    initial = rng.uniform(-np.pi, np.pi, size=len(parameters))
    def raw_objective(values):
        bound = _bind(circuit, parameters, values)
        return float(np.real(Statevector.from_instruction(bound).expectation_value(hamiltonian)))

    counted_objective = qff.CountedCost(raw_objective)

    result = minimize(
        counted_objective,
        initial,
        method="L-BFGS-B",
        options={"maxiter": OPTIMIZER_MAXITER, "ftol": 1e-12, "gtol": 1e-8, "maxls": 30},
    )
    bound = _bind(circuit, parameters, result.x)
    state = Statevector.from_instruction(bound)
    energy = float(np.real(state.expectation_value(hamiltonian)))
    return {
        "n": n,
        "g": float(g),
        "layers": int(layers),
        "seed": int(seed),
        "energy": energy,
        "parameters": np.asarray(result.x, dtype=float).tolist(),
        "calls": int(counted_objective.calls),
        "optimizer_success": bool(result.success),
        "optimizer_message": str(result.message),
        "state": state,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Refusing to write an empty result table: {path}")
    names = fieldnames or list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _to_json(value: Any):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")


def _save_diagnostics(optimizations: list[dict[str, Any]]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    payload = []
    for run in optimizations:
        payload.append({k: v for k, v in run.items() if k != "state"})
    (RAW_DIR / "phase2_s1_optimizer_runs.json").write_text(
        json.dumps(payload, indent=2, default=_to_json) + "\n", encoding="utf-8"
    )


def _metrics_row(ps: str, label: str, processor: dict, circuit) -> dict[str, Any]:
    metrics = qff.circuit_metrics(circuit, processor)
    row = {
        "ps": ps,
        "circuit_label": label,
        "processor": processor["name"],
        "executable": bool(metrics.get("executable", False)),
        "logical_qubits": int(circuit.num_qubits),
        "physical_qubits": int(processor["num_qubits"]),
        "logical_2q": metrics.get("logical_cx", ""),
        "two_q": metrics.get("cx", ""),
        "depth": metrics.get("depth", ""),
        "two_q_depth": metrics.get("two_q_depth", ""),
        "swaps": metrics.get("swaps", ""),
        "routing_overhead_2q": metrics.get("cx_overhead", ""),
    }
    if not metrics.get("executable", False):
        row["reason"] = metrics.get("reason", "capacity")
    return row


def _selected_best(runs: list[dict[str, Any]], exact0: float) -> dict[str, Any]:
    return min(runs, key=lambda run: abs(run["energy"] - exact0))


def _state_metrics(best: dict[str, Any], hamiltonian: SparsePauliOp, exact0: float,
                   exact1: float, exact_states: list[Statevector], n: int) -> dict[str, Any]:
    state = best["state"]
    ops = qff.observable_ops(n)
    obs = qff.expectations(state, ops)
    exact_obs = qff.expectations(exact_states[0], ops)
    f0 = float(abs(np.vdot(exact_states[0].data, state.data)) ** 2)
    f1 = float(abs(np.vdot(exact_states[1].data, state.data)) ** 2)
    return {
        "best_energy": best["energy"],
        "exact_E0": exact0,
        "exact_E1": exact1,
        "energy_err": best["energy"] - exact0,
        "fidelity": min(1.0, f0),
        "fidelity_2": min(1.0, f0 + f1),
        "mx": obs["mx"],
        "mx_exact": exact_obs["mx"],
        "czz_nn": obs["czz_nn"],
        "czz_nn_exact": exact_obs["czz_nn"],
        "mz2": obs["mz2"],
        "mz2_exact": exact_obs["mz2"],
        "mz": obs["mz"],
        "mz_exact": exact_obs["mz"],
        "optimizer_calls": int(best["calls"]),
        "n_params": 2 * int(best["layers"]),
        "best_seed": int(best["seed"]),
        "optimizer_success": bool(best["optimizer_success"]),
    }


def run_s1_grid(n: int, max_layers: int) -> tuple[list[dict[str, Any]], dict[float, dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    final_by_g: dict[float, dict[str, Any]] = {}
    all_runs: list[dict[str, Any]] = []
    for g in G_GRID:
        print(f"[PS-S1] N={n}, g={g:.2f}: starting exact check and HVA layer scan", flush=True)
        hamiltonian, locked_e0, locked_e1 = _instance(n, g)
        eigenvalues, exact_states = qff.exact_spectrum(hamiltonian, k=2)
        if not math.isclose(float(eigenvalues[0]), locked_e0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"N={n}, g={g}: computed E0 differs from locked instance")
        if not math.isclose(float(eigenvalues[1]), locked_e1, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"N={n}, g={g}: computed E1 differs from locked instance")

        chosen_layer = None
        chosen_run = None
        best_any = None
        for layers in range(1, max_layers + 1):
            layer_runs = [_optimize_hva(n, g, layers, seed, hamiltonian) for seed in SEEDS]
            all_runs.extend(layer_runs)
            best = _selected_best(layer_runs, locked_e0)
            state_metrics = _state_metrics(best, hamiltonian, locked_e0, locked_e1, exact_states, n)
            row = {
                "N": n,
                "g": g,
                "layers": layers,
                **state_metrics,
                "optimizer_calls": sum(int(run["calls"]) for run in layer_runs),
                "energy_tolerance_met": abs(state_metrics["energy_err"]) < ENERGY_TOL,
                "two_q_on_D": qff.circuit_metrics(
                    qff.hva_ansatz(n, layers, zz_mode="rzz")[0], load_d()
                )["cx"],
            }
            rows.append(row)
            print(
                f"[PS-S1] N={n}, g={g:.2f}, L={layers}: best |E-E0|="
                f"{abs(state_metrics['energy_err']):.3e}; calls={row['optimizer_calls']}",
                flush=True,
            )
            if best_any is None or abs(best["energy"] - locked_e0) < abs(best_any["energy"] - locked_e0):
                best_any = best
                chosen_layer = layers
                chosen_run = best
            if abs(state_metrics["energy_err"]) < ENERGY_TOL:
                chosen_layer, chosen_run = layers, best
                break
        if chosen_run is None:
            raise RuntimeError(f"No VQE runs produced for N={n}, g={g}")
        final_by_g[g] = {
            "n": n,
            "g": g,
            "layers": chosen_layer,
            "run": chosen_run,
            "hamiltonian": hamiltonian,
            "exact0": locked_e0,
            "exact1": locked_e1,
            "exact_states": exact_states,
            "tolerance_met": abs(chosen_run["energy"] - locked_e0) < ENERGY_TOL,
        }
    return rows, final_by_g, all_runs


def _bell_rows(processor_d: dict) -> list[dict[str, Any]]:
    cm = qff.coupling_map_from_edges(processor_d["edges"], processor_d["num_qubits"])
    n = processor_d["num_qubits"]
    distances = [(cm.distance(a, b), a, b) for a in range(n) for b in range(a + 1, n)]
    max_dist = max(item[0] for item in distances)
    far = min((a, b) for dist, a, b in distances if dist == max_dist)
    pairs = [("direct", (0, 1)), ("farthest", far)]
    rows = []
    for label, pair in pairs:
        for noisy in (False, True):
            result = qff.bell_experiment(processor_d, pair, noisy=noisy, shots=qff.SHOTS)
            rows.append({
                "pair": label,
                "physical_pair": f"{pair[0]}-{pair[1]}",
                "pair_distance": int(result["pair_distance"]),
                "condition": "noisy" if noisy else "ideal",
                "two_qubit_gates": int(result["cx"]),
                "XX": result["XX"], "XX_se": result["XX_se"],
                "YY": result["YY"], "YY_se": result["YY_se"],
                "ZZ": result["ZZ"], "ZZ_se": result["ZZ_se"],
                "fidelity": result["fidelity"], "fidelity_se": result["fidelity_se"],
            })
    return rows


def _phase2_resources(final_by_g: dict[float, dict[str, Any]], n: int = 4) -> list[dict[str, Any]]:
    processors = {**PROCESSORS, "D": load_d()}
    rows = []
    for g, record in final_by_g.items():
        if record["n"] != n:
            continue
        cx_circuit, cx_parameters = qff.hva_ansatz(n, record["layers"], zz_mode="cx")
        d_circuit, d_parameters = qff.hva_ansatz(n, record["layers"], zz_mode="rzz")
        cx_state = Statevector.from_instruction(_bind(cx_circuit, cx_parameters, record["run"]["parameters"]))
        d_state = Statevector.from_instruction(_bind(d_circuit, d_parameters, record["run"]["parameters"]))
        if state_fidelity(cx_state, d_state) < 1.0 - 1e-10:
            raise ValueError(f"D native-RZZ HVA changed the ideal state for N={n}, g={g}")
        for key, processor in processors.items():
            zz_mode = "rzz" if key == "D" else "cx"
            circuit, _ = qff.hva_ansatz(n, record["layers"], zz_mode=zz_mode)
            label = f"HVA_N{n}_g{g:.2f}_L{record['layers']}"
            row = _metrics_row("PS-S1", label, processor, circuit)
            row["processor"] = key
            rows.append(row)
    return rows


def _farthest_pair(processor: dict) -> tuple[int, int]:
    cm = qff.coupling_map_from_edges(processor["edges"], processor["num_qubits"])
    distances = [(cm.distance(a, b), a, b) for a in range(processor["num_qubits"])
                 for b in range(a + 1, processor["num_qubits"])]
    farthest = max(distance for distance, _, _ in distances)
    return min((a, b) for distance, a, b in distances if distance == farthest)


def _noisy_s1(final_by_g: dict[float, dict[str, Any]], n: int = 4) -> list[dict[str, Any]]:
    processor_d = load_d()
    rows = []
    for g in NOISY_G:
        record = final_by_g[g]
        if record["n"] != n:
            continue
        qc, params = qff.hva_ansatz(n, record["layers"], zz_mode="rzz")
        bound = _bind(qc, params, record["run"]["parameters"])
        rho = qff.noisy_density_matrix(bound, processor_d, noisy=True)
        ops = qff.observable_ops(n)
        obs = qff.expectations(rho, ops)
        energy = float(np.real(rho.expectation_value(record["hamiltonian"])))
        f_dm = float(state_fidelity(record["exact_states"][0], rho))
        rows.append({
            "g": g,
            "layers": record["layers"],
            "mx_noisy": obs["mx"],
            "czz_nn_noisy": obs["czz_nn"],
            "mz2_noisy": obs["mz2"],
            "energy_noisy": energy,
            "fidelity_noisy_dm": f_dm,
        })
    return rows


def _plot_outputs(s1_rows: list[dict[str, Any]], noisy_rows: list[dict[str, Any]],
                  resources: list[dict[str, Any]], bell_rows: list[dict[str, Any]], d: dict[str, Any]) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    n4 = [r for r in s1_rows if int(r["N"]) == 4]
    chosen = {}
    for row in n4:
        g = float(row["g"])
        if g not in chosen or abs(float(row["energy_err"])) < abs(float(chosen[g]["energy_err"])):
            chosen[g] = row
    gs = sorted(chosen)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), constrained_layout=True)
    metrics = (("mx", "mx_exact", r"$m_x$"),
               ("czz_nn", "czz_nn_exact", r"$C_{zz}$"),
               ("mz2", "mz2_exact", r"$\langle M_z^2\rangle/N^2$"))
    for ax, (value, exact, title) in zip(axes, metrics):
        ax.plot(gs, [float(chosen[g][exact]) for g in gs], "k--o", label="exact")
        ax.plot(gs, [float(chosen[g][value]) for g in gs], "C0-s", label="HVA VQE")
        ax.set_xlabel("Transverse field g")
        ax.set_title(title)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Expectation value")
    axes[-1].legend(frameon=False)
    fig.suptitle("PS-S1: observables across the finite-size crossover")
    fig.savefig(FIGURES_DIR / "phase2_s1_observables.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0), constrained_layout=True)
    exact_energy = [float(chosen[g]["exact_E0"]) for g in gs]
    vqe_energy = [float(chosen[g]["best_energy"]) for g in gs]
    energy_error = [float(chosen[g]["energy_err"]) for g in gs]
    axes[0].plot(gs, exact_energy, "k--o", label="exact E0")
    axes[0].plot(gs, vqe_energy, "C0-s", label="HVA VQE")
    axes[0].set_ylabel("Ground-state energy")
    axes[0].legend(frameon=False)
    axes[1].semilogy(gs, [max(abs(e), 1e-14) for e in energy_error], "C3-o")
    axes[1].axhline(ENERGY_TOL, color="black", linestyle="--", linewidth=0.8, label="10⁻³ tolerance")
    axes[1].set_ylabel("Absolute energy error")
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.set_xlabel("Transverse field g")
        ax.grid(alpha=0.25)
    fig.suptitle("PS-S1 ground-state energy and VQE error")
    fig.savefig(FIGURES_DIR / "phase2_s1_energy.png", dpi=180)
    plt.close(fig)

    min_layers = {}
    for g in gs:
        good = [int(r["layers"]) for r in n4 if float(r["g"]) == g and bool(r["energy_tolerance_met"])]
        min_layers[g] = min(good) if good else np.nan
    fig, ax = plt.subplots(figsize=(6.6, 4.2), constrained_layout=True)
    ax.plot(gs, [min_layers[g] for g in gs], "C1-o")
    ax.set_xlabel("Transverse field g")
    ax.set_ylabel("Minimum HVA layers for |E − E₀| < 10⁻³")
    ax.set_title("Layer study: ordered-side state preparation cost")
    ax.grid(alpha=0.25)
    fig.savefig(FIGURES_DIR / "phase2_s1_layer_study.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2), constrained_layout=True)
    for processor, marker in (("A", "o"), ("B", "s"), ("D", "^") ):
        subset = [r for r in resources if r["processor"] == processor and str(r["circuit_label"]).startswith("HVA_N4")]
        subset.sort(key=lambda r: float(str(r["circuit_label"]).split("_g")[1].split("_L")[0]))
        rg = [float(str(r["circuit_label"]).split("_g")[1].split("_L")[0]) for r in subset]
        axes[0].plot(rg, [float(r["two_q"]) for r in subset], marker=marker, label=processor)
        axes[1].plot(rg, [float(r["depth"]) for r in subset], marker=marker, label=processor)
    axes[0].set_title("Compiled two-qubit gates")
    axes[1].set_title("Transpiled circuit depth")
    for ax in axes:
        ax.set_xlabel("g")
        ax.grid(alpha=0.25)
        ax.legend(frameon=False)
    fig.suptitle("PS-S1 HVA resource comparison")
    fig.savefig(FIGURES_DIR / "phase2_s1_resources.png", dpi=180)
    plt.close(fig)

    labels = [f"{r['pair']}\n{r['condition']}" for r in bell_rows]
    vals = [float(r["fidelity"]) for r in bell_rows]
    errors = [float(r["fidelity_se"]) for r in bell_rows]
    colors = ["#4c78a8" if r["condition"] == "ideal" else "#f58518" for r in bell_rows]
    fig, ax = plt.subplots(figsize=(8.5, 4.4), constrained_layout=True)
    ax.bar(labels, vals, yerr=errors, capsize=4, color=colors, alpha=0.85)
    ax.axhline(1, color="black", linestyle="--", linewidth=0.8)
    ax.set_ylim(0, 1.08)
    ax.set_ylabel(r"Bell fidelity $F_{\Phi^+}$")
    ax.set_title("Processor D Bell verification (bars ± one standard error)")
    ax.grid(axis="y", alpha=0.25)
    fig.savefig(FIGURES_DIR / "phase2_bell_fidelity.png", dpi=180)
    plt.close(fig)

    edges = [tuple(edge) for edge in d["edges"]]
    n = d["num_qubits"]
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False) + np.pi / 2
    pos = {i: np.array([np.cos(theta[i]), np.sin(theta[i])]) for i in range(n)}
    fig, ax = plt.subplots(figsize=(5.5, 5.2), constrained_layout=True)
    for a, b in edges:
        ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color="#4c78a8", linewidth=2, zorder=1)
    ax.scatter([pos[i][0] for i in range(n)], [pos[i][1] for i in range(n)], s=600,
               color="#f2cf5b", edgecolor="#333333", zorder=2)
    for i in range(n):
        ax.text(pos[i][0], pos[i][1], str(i), ha="center", va="center", fontsize=12, weight="bold", zorder=3)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Processor D: six-qubit cycle with opposite chords")
    fig.savefig(FIGURES_DIR / "processor_D_topology.png", dpi=180)
    plt.close(fig)


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(value) for value in row) + " |" for row in rows]
    return "\n".join([head, rule, *body])


def _write_phase2_report(s1_rows: list[dict[str, Any]], noisy_rows: list[dict[str, Any]],
                         resources: list[dict[str, Any]], bell_rows: list[dict[str, Any]],
                         include_n6: bool, max_layers: int) -> None:
    finals = []
    for n in ((4, 6) if include_n6 else (4,)):
        for g in G_GRID:
            candidates = [r for r in s1_rows if int(r["N"]) == n and math.isclose(float(r["g"]), g)]
            passing = [r for r in candidates if bool(r["energy_tolerance_met"])]
            picked = min(passing, key=lambda r: int(r["layers"])) if passing else min(
                candidates, key=lambda r: abs(float(r["energy_err"]))
            )
            finals.append(picked)

    n4 = [r for r in finals if int(r["N"]) == 4]
    n4_energy_table = [[
        f"{float(r['g']):.2f}", str(r["layers"]), f"{float(r['best_energy']):.8f}",
        f"{float(r['exact_E0']):.8f}", f"{float(r['exact_E1']):.8f}",
        f"{float(r['energy_err']):.2e}", f"{float(r['fidelity']):.5f}",
        f"{float(r['fidelity_2']):.5f}", str(r["best_seed"]),
    ] for r in n4]
    n4_observable_table = [[
        f"{float(r['g']):.2f}", f"{float(r['mx']):.5f}", f"{float(r['mx_exact']):.5f}",
        f"{float(r['czz_nn']):.5f}", f"{float(r['czz_nn_exact']):.5f}",
        f"{float(r['mz2']):.5f}", f"{float(r['mz2_exact']):.5f}",
        f"{float(r['mz']):+.2e}", f"{float(r['mz_exact']):+.2e}",
    ] for r in n4]

    noise_table = [[
        f"{float(r['g']):.2f}", str(r["layers"]), f"{float(r['energy_noisy']):.6f}",
        f"{float(r['fidelity_noisy_dm']):.5f}", f"{float(r['mx_noisy']):.5f}",
        f"{float(r['czz_nn_noisy']):.5f}", f"{float(r['mz2_noisy']):.5f}",
    ] for r in noisy_rows]

    bell_table = [[
        r["pair"], r["physical_pair"], str(r["pair_distance"]), r["condition"],
        f"{float(r['XX']):+.4f} ± {float(r['XX_se']):.4f}",
        f"{float(r['YY']):+.4f} ± {float(r['YY_se']):.4f}",
        f"{float(r['ZZ']):+.4f} ± {float(r['ZZ_se']):.4f}",
        f"{float(r['fidelity']):.4f} ± {float(r['fidelity_se']):.4f}",
    ] for r in bell_rows]

    resource_summary = []
    for processor in ("A", "B", "D"):
        subset = [r for r in resources if r["processor"] == processor
                  and str(r["circuit_label"]).startswith("HVA_N4")]
        resource_summary.append([
            processor,
            str(subset[0]["physical_qubits"] if subset else "-"),
            f"{np.mean([float(r['logical_2q']) for r in subset]):.1f}" if subset else "-",
            f"{np.mean([float(r['two_q']) for r in subset]):.1f}" if subset else "-",
            f"{np.mean([float(r['depth']) for r in subset]):.1f}" if subset else "-",
            f"{np.mean([float(r['swaps']) for r in subset]):.1f}" if subset else "-",
        ])

    min_layer_text = ", ".join(
        f"g={float(r['g']):.2f}: L={r['layers']}" +
        ("" if bool(r["energy_tolerance_met"]) else " (tolerance not reached)")
        for r in n4
    )
    n6_section = ""
    if include_n6:
        n6_rows = [r for r in finals if int(r["N"]) == 6]
        n6_table = [[f"{float(r['g']):.2f}", str(r["layers"]),
                     f"{float(r['best_energy']):.8f}", f"{float(r['exact_E0']):.8f}",
                     f"{float(r['exact_E1']):.8f}", f"{float(r['energy_err']):.2e}",
                     f"{float(r['fidelity']):.5f}", f"{float(r['fidelity_2']):.5f}",
                     str(r["best_seed"])] for r in n6_rows]
        n6_section = "\n## Optional N=6 tier\n\n" + _md_table(
            ["g", "minimum layer", "VQE E", "E0", "E1", "energy error", "F", "F2", "best seed"], n6_table
        ) + "\n\nProcessor A is marked not executable for N=6 because it has only five physical qubits; B and D are benchmarked.\n"

    report = f"""# QFF 2026 Phase 2 — PS-S1 report

**Team:** Chicken Leg Piece  
**Problem:** PS-S1, open-chain transverse-field Ising ground state  
**Status:** local Phase 2 simulation artifacts; the team submits the public repository URL through the hackathon portal.

## Summary

We reproduced the locked N=4 instances at all seven fields, used the HVA with seeds 0, 1 and 2, and recorded the first layer count reaching `|E - E0| < 10^-3` where achieved (search bound L={max_layers}). The same logical HVA is compiled on A/B using CX-based ZZ rotations and on D using native RZZ rotations at the same two-qubit error rate. All noisy values are local density-matrix simulations, not hardware measurements.

Minimum-layer outcomes: {min_layer_text}.

## Locked method and references

The Phase 2 specification supersedes Phase 1 inputs: `H = -Σ ZᵢZᵢ₊₁ - gΣXᵢ`, open boundary, `J=1`. Each instance is loaded from `data/s1/`; exact E0 and E1 are checked against dense diagonalization. PS-S1 uses VQE only. Parameter initialization uses `numpy.random.default_rng(seed)` with a uniform draw in `(-π, π)` and the official seeds 0, 1, 2. Each layer has two shared HVA parameters. The layer search runs in increasing L and stops at the first L meeting the energy tolerance; all three seeds are run at each attempted layer. `optimizer_calls` in the CSV is the sum over those three starts.

## N=4 VQE and finite-size crossover

The table reports the best of the three official starts at the selected minimum layer. `F2` sums overlaps with the two lowest exact eigenstates, which is informative where the low-field levels are close. `mz` is the symmetry diagnostic and should remain near zero for a spin-flip-symmetric state.

{_md_table(["g", "L", "VQE E", "E0", "E1", "E−E0", "F", "F2", "best seed"], n4_energy_table)}

| g | mx (VQE) | mx (exact) | Czz (VQE) | Czz (exact) | mz²/N² (VQE) | mz²/N² (exact) | mz (VQE) | mz (exact) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
{chr(10).join('| ' + ' | '.join(row) + ' |' for row in n4_observable_table)}

![PS-S1 energy results](results/figures/phase2_s1_energy.png)

![PS-S1 observables across g](results/figures/phase2_s1_observables.png)

![Minimum HVA layer study](results/figures/phase2_s1_layer_study.png)

The exact observables show the finite-size crossover: transverse magnetization grows as g increases, while nearest-neighbour Z correlation and squared longitudinal magnetization decrease. Across the locked grid, `mx` has the largest end-to-end change (about 0.75), narrowly ahead of `Czz` (about 0.71); `mz2` remains a useful finite-size order parameter. At finite N this is a smooth crossover rather than a sharp thermodynamic phase transition. The measured layer counts are four for g≤0.75 and three at g=1.0, 1.5 and 2.0, with g=1.25 also requiring four; this is a general low-field increase, not a strictly monotone curve. On the ordered side the state needs strong long-range Z correlations, while the HVA starts in the transverse-field product state |+〉^N, so extra alternating entangling/rotation layers are needed to build those correlations.

## Noisy Processor D results

The required noisy PS-S1 run uses the selected converged circuit at g=0.5, 1.0 and 2.0. The density matrix includes gate noise and excludes readout noise, as specified for the fidelity definition.

{_md_table(["g", "L", "noisy energy", "noisy F", "mx", "Czz", "mz²/N²"], noise_table)}

## Processor D and architecture comparison

D is a six-qubit cycle with opposite chords and native RZZ. It contains a four-qubit cycle, retains the open-chain path needed by PS-S1, and supports the optional N=6 instances. The Phase 1 supplementary ring ansatz measured five routing SWAPs on A and none on B. For the Phase 2 HVA, A/B use the official CX basis, requiring two CX gates for each ZZ rotation; D uses one RZZ at the same p2=0.005. The extra couplers and calibration burden are a trade-off; crosstalk is not represented by the supplied depolarizing noise model.

Average N=4 metrics across the seven selected HVA circuits (the detailed per-field records are in `results/tables/resources.csv`):

{_md_table(["processor", "physical qubits", "mean logical 2q", "mean compiled 2q", "mean depth", "mean routing SWAPs"], resource_summary)}

![PS-S1 compiled resources](results/figures/phase2_s1_resources.png)

![Processor D topology](results/figures/processor_D_topology.png)

## Common Bell-state objective

We prepare `|Φ+>` on one directly coupled D pair and one farthest-apart pair. Each row pools the three measured Pauli bases with 4,096 shots per basis. The fidelity is `F=(1+XX−YY+ZZ)/4`; the standard error propagates the three independent parity-estimator errors in quadrature.

{_md_table(["pair", "physical qubits", "distance", "condition", "XX ± SE", "YY ± SE", "ZZ ± SE", "F ± SE"], bell_table)}

![Processor D Bell fidelity](results/figures/phase2_bell_fidelity.png)

## Reproducibility and limits

The required gates, noise parameters, shot count, seeds, and transpilation settings are supplied by the unchanged `qff_sim.py`. The tables are generated by `scripts/run_phase2_s1.py`; `main.ipynb` loads the checked-in tables by default and can recompute them with `RECOMPUTE = True`. Processor D is validated with `tools/check_processor_d.py`. The full result is limited to the small locked model and synthetic noise; it establishes no hardware advantage. AI assistance is disclosed in `AI_DISCLOSURE.md`.

{n6_section}
"""
    (ROOT / "report.md").write_text(report, encoding="utf-8")


def generate_phase2_outputs(max_layers: int = DEFAULT_MAX_LAYERS, include_n6: bool = False) -> dict[str, Any]:
    d = load_d()
    violations = qff.validate_processor_d(d, required_qubits=6 if include_n6 else 4)
    if violations:
        raise ValueError("Processor D fails the official checker: " + "; ".join(violations))
    all_rows: list[dict[str, Any]] = []
    all_final: dict[tuple[int, float], dict[str, Any]] = {}
    all_runs: list[dict[str, Any]] = []
    sizes = (4, 6) if include_n6 else (4,)
    for n in sizes:
        rows, finals, runs = run_s1_grid(n, max_layers)
        all_rows.extend(rows)
        all_runs.extend(runs)
        for g, value in finals.items():
            all_final[(n, g)] = value

    _write_csv(TABLES_DIR / "s1_results.csv", all_rows)
    _save_diagnostics(all_runs)
    final4 = {g: all_final[(4, g)] for g in G_GRID}
    noisy_rows = _noisy_s1(final4)
    _write_csv(TABLES_DIR / "s1_noisy.csv", noisy_rows)

    resources = _phase2_resources(final4)
    if include_n6:
        resources.extend(_phase2_resources({g: all_final[(6, g)] for g in G_GRID}, n=6))
    _write_csv(TABLES_DIR / "resources.csv", resources)

    bell_rows = _bell_rows(d)
    _write_csv(TABLES_DIR / "bell.csv", bell_rows)
    raw_parameters = {
        f"N{n}_g{g:.2f}": {
            "layers": record["layers"],
            "seed": record["run"]["seed"],
            "parameters": record["run"]["parameters"],
            "energy": record["run"]["energy"],
            "exact_E0": record["exact0"],
            "energy_tolerance_met": record["tolerance_met"],
        }
        for (n, g), record in all_final.items()
    }
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "phase2_s1_best_parameters.json").write_text(
        json.dumps(raw_parameters, indent=2, default=_to_json) + "\n", encoding="utf-8"
    )
    _plot_outputs(all_rows, noisy_rows, resources, bell_rows, d)
    _write_phase2_report(all_rows, noisy_rows, resources, bell_rows, include_n6, max_layers)
    return {
        "n4_rows": sum(int(r["N"]) == 4 for r in all_rows),
        "n6_rows": sum(int(r["N"]) == 6 for r in all_rows),
        "n4_tolerance_g": [g for g in G_GRID if all_final[(4, g)]["tolerance_met"]],
        "n4_min_layers": {f"{g:.2f}": (all_final[(4, g)]["layers"] if all_final[(4, g)]["tolerance_met"] else None) for g in G_GRID},
        "n6_tolerance_g": [g for g in G_GRID if include_n6 and all_final[(6, g)]["tolerance_met"]],
        "d_qubits": d["num_qubits"],
        "d_edges": len(d["edges"]),
    }


def load_phase2_outputs() -> dict[str, Any]:
    required = [TABLES_DIR / name for name in ("s1_results.csv", "s1_noisy.csv", "resources.csv", "bell.csv")]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing generated Phase 2 outputs; run scripts/run_phase2_s1.py. " + ", ".join(missing))
    s1_rows = _read_csv(required[0])
    min_layers = {}
    for g in G_GRID:
        rows = [r for r in s1_rows if int(r["N"]) == 4 and math.isclose(float(r["g"]), g)]
        met = [r for r in rows if r["energy_tolerance_met"].lower() == "true"]
        min_layers[f"{g:.2f}"] = int(min(met, key=lambda r: int(r["layers"]))["layers"]) if met else None
    return {
        "s1_results": s1_rows,
        "s1_noisy": _read_csv(required[1]),
        "resources": _read_csv(required[2]),
        "bell": _read_csv(required[3]),
        "n4_min_layers": min_layers,
        "n4_tolerance_g": [float(g) for g, layer in min_layers.items() if layer is not None],
    }


def run_phase2_s1(recompute: bool = False, include_n6: bool = False,
                  max_layers: int = DEFAULT_MAX_LAYERS) -> dict[str, Any]:
    if recompute:
        return generate_phase2_outputs(max_layers=max_layers, include_n6=include_n6)
    return load_phase2_outputs()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-layers", type=int, default=DEFAULT_MAX_LAYERS)
    parser.add_argument("--include-n6", action="store_true", help="Run the optional six-qubit bonus tier")
    args = parser.parse_args()
    summary = generate_phase2_outputs(max_layers=args.max_layers, include_n6=args.include_n6)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
