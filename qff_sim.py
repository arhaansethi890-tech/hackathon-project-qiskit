"""
qff_sim.py - Qiskit Fall Fest 2026, Phase 2 (Quantum Simulation Track) starter utilities.

Provided by the organizers so that every team measures things the SAME way.
You may read and copy this code freely. Do NOT change the official settings
(basis gates, noise rates, seed, shots, optimization level) for your required
benchmark runs - put any extra experiments in a clearly labelled separate section.

Tested with the pinned requirements.txt (qiskit 1.4.6, qiskit-aer 0.18.0) on
Python 3.11-3.13, and also with qiskit 2.x.
"""
from __future__ import annotations

import json
from collections import deque

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.transpiler import CouplingMap, StagedPassManager
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error, ReadoutError

# --------------------------------------------------------------------------
# 1. OFFICIAL BENCHMARK SETTINGS (fixed for all teams)
# --------------------------------------------------------------------------
BASIS_GATES = ["rz", "sx", "x", "cx"]
OPT_LEVEL = 1
SEED = 42
SHOTS = 4096
P1_DEPOL = 0.001   # 1-qubit depolarizing per 1-qubit gate (rz, sx, x)
P2_DEPOL = 0.005   # 2-qubit depolarizing per CX
P_READOUT = 0.01   # symmetric readout bit-flip per measured qubit

# Official reference processors (undirected edges; used in both directions)
PROCESSOR_A_EDGES = [(0, 1), (1, 2), (1, 3), (3, 4)]                      # 5 qubits
PROCESSOR_B_EDGES = [(0, 1), (1, 2), (1, 6), (2, 3), (2, 6), (2, 5),
                     (3, 4), (4, 5), (5, 6), (6, 7), (6, 8), (8, 0)]      # 9 qubits

# Processor D design limits
D_MAX_QUBITS = 12
D_MAX_DEGREE = 4
ALLOWED_D_GATE_SETS = (["rz", "sx", "x", "cx"], ["rz", "sx", "x", "cz"], ["rz", "sx", "x", "rzz"])
TWO_Q = ("cx", "cz", "rzz")


def coupling_map_from_edges(edges, num_qubits=None) -> CouplingMap:
    """Bidirectional CouplingMap from a list of undirected edges."""
    directed = []
    for a, b in edges:
        directed += [[int(a), int(b)], [int(b), int(a)]]
    cm = CouplingMap(directed)
    if num_qubits is not None:
        for q in range(num_qubits):
            if q not in cm.physical_qubits:
                cm.add_physical_qubit(q)
    return cm


PROCESSOR_A = {"name": "Processor A", "num_qubits": 5, "edges": PROCESSOR_A_EDGES}
PROCESSOR_B = {"name": "Processor B", "num_qubits": 9, "edges": PROCESSOR_B_EDGES}


# --------------------------------------------------------------------------
# 2. NOISE MODEL
# --------------------------------------------------------------------------
def official_noise_model(p1=P1_DEPOL, p2=P2_DEPOL, p_ro=P_READOUT, scale: float = 1.0) -> NoiseModel:
    """Official synthetic noise model (identical on every processor). `scale` multiplies all
    three error rates (PS-S3 noise sweep uses 0.5, 1 and 2)."""
    p1, p2, p_ro = p1 * scale, p2 * scale, p_ro * scale
    nm = NoiseModel(basis_gates=BASIS_GATES + ["cz", "rzz"])
    nm.add_all_qubit_quantum_error(depolarizing_error(p1, 1), ["rz", "sx", "x"])
    nm.add_all_qubit_quantum_error(depolarizing_error(p2, 2), ["cx", "cz", "rzz"])
    nm.add_all_qubit_readout_error(ReadoutError([[1 - p_ro, p_ro], [p_ro, 1 - p_ro]]))
    return nm


def simulator(noisy: bool, processor: dict | None = None, noise_model=None, scale: float = 1.0) -> AerSimulator:
    """AerSimulator for ideal (noisy=False) or noisy runs. Pass circuits that are
    ALREADY transpiled for the processor (see transpile_for)."""
    if not noisy:
        return AerSimulator(seed_simulator=SEED)
    nm = noise_model if noise_model is not None else official_noise_model(scale=scale)
    kw = {}
    if processor is not None:
        kw["coupling_map"] = coupling_map_from_edges(processor["edges"], processor["num_qubits"])
    basis = (processor or {}).get("basis_gates", BASIS_GATES)
    return AerSimulator(noise_model=nm, basis_gates=list(basis), seed_simulator=SEED, **kw)


# --------------------------------------------------------------------------
# 3. TRANSPILATION + OFFICIAL METRICS
# --------------------------------------------------------------------------
def _basis(processor):
    return list(processor.get("basis_gates", BASIS_GATES))


def _pass_manager(processor):
    cm = coupling_map_from_edges(processor["edges"], processor["num_qubits"])
    return generate_preset_pass_manager(optimization_level=OPT_LEVEL, basis_gates=_basis(processor),
                                        coupling_map=cm, seed_transpiler=SEED)


def transpile_for(qc: QuantumCircuit, processor: dict) -> QuantumCircuit:
    """Official transpilation: opt level 1, SABRE layout/routing, seed 42."""
    if qc.num_qubits > processor["num_qubits"]:
        raise ValueError(f"{processor['name']} has {processor['num_qubits']} qubits but the "
                         f"circuit needs {qc.num_qubits}: report 'not executable (capacity)'.")
    return _pass_manager(processor).run(qc)


def circuit_metrics(qc: QuantumCircuit, processor: dict) -> dict:
    """Official metric definitions (measurements/resets/barriers excluded from gate counts).

    logical_cx  : two-qubit gate count after transpiling with NO connectivity limit (same settings)
    cx          : two-qubit gate count (CX or CZ) after transpiling for the processor
    depth       : depth of the transpiled circuit, ignoring measure/barrier/reset
    two_q_depth : depth counting only CX gates
    swaps       : SWAP gates inserted by the routing stage (before basis translation)
    cx_overhead : cx - logical_cx  (extra CX caused by routing + layout)
    """
    if qc.num_qubits > processor["num_qubits"]:
        return {"processor": processor["name"], "executable": False,
                "reason": f"needs {qc.num_qubits} qubits > {processor['num_qubits']}"}
    pm = _pass_manager(processor)
    full = pm.run(qc)
    # Same init/layout/routing stages (same seed) -> count inserted SWAPs before decomposition
    routed = StagedPassManager(stages=["init", "layout", "routing"],
                               init=pm.init, layout=pm.layout, routing=pm.routing).run(qc)
    unconstrained = transpile(qc, basis_gates=_basis(processor), optimization_level=OPT_LEVEL,
                              seed_transpiler=SEED)
    skip = {"measure", "barrier", "reset"}
    ops = dict(full.count_ops())
    ops["cx"] = sum(ops.get(g, 0) for g in TWO_Q)
    uops = dict(unconstrained.count_ops())
    uops["cx"] = sum(uops.get(g, 0) for g in TWO_Q)
    return {
        "processor": processor["name"],
        "executable": True,
        "logical_qubits": qc.num_qubits,
        "physical_qubits": processor["num_qubits"],
        "logical_cx": uops["cx"],
        "cx": ops.get("cx", 0),
        "one_q_gates": sum(v for k, v in ops.items() if k in ("rz", "sx", "x")),
        "depth": full.depth(filter_function=lambda inst: inst.operation.name not in skip),
        "two_q_depth": full.depth(filter_function=lambda inst: inst.operation.num_qubits == 2
                                  and inst.operation.name not in skip),
        "swaps": routed.count_ops().get("swap", 0),
        "cx_overhead": ops["cx"] - uops["cx"],
    }


# --------------------------------------------------------------------------
# 4. BITSTRING CONVENTION
# --------------------------------------------------------------------------
def counts_to_x(bitstring: str) -> tuple:
    """Qiskit count keys are little-endian (qubit 0 is the RIGHT-most character).
    This returns (x0, x1, ..., x_{n-1}) with x_i = value of qubit i."""
    return tuple(int(b) for b in reversed(bitstring.replace(" ", "")))


# --------------------------------------------------------------------------
# 5. BELL-STATE VERIFICATION (Objective 1)
# --------------------------------------------------------------------------
def bell_circuit(basis: str) -> QuantumCircuit:
    """|Phi+> = (|00> + |11>)/sqrt(2) on logical qubits 0,1, measured in basis 'XX','YY' or 'ZZ'."""
    qc = QuantumCircuit(2, 2, name=f"bell_{basis}")
    qc.h(0)
    qc.cx(0, 1)
    if basis == "XX":
        qc.h([0, 1])
    elif basis == "YY":
        qc.sdg([0, 1])
        qc.h([0, 1])
    elif basis != "ZZ":
        raise ValueError("basis must be 'XX', 'YY' or 'ZZ'")
    qc.measure([0, 1], [0, 1])
    return qc


def parity_expectation(counts: dict) -> tuple:
    """<P> = (N_even - N_odd)/N for two-qubit parity, and its standard error."""
    n = sum(counts.values())
    even = sum(c for k, c in counts.items() if k.replace(" ", "").count("1") % 2 == 0)
    e = (2 * even - n) / n
    return e, float(np.sqrt(max(1 - e * e, 0.0) / n))


def bell_experiment(processor: dict, physical_pair: tuple, noisy: bool, shots: int = SHOTS,
                    noise_model=None) -> dict:
    """Run XX, YY, ZZ correlations for |Phi+> on a chosen PHYSICAL qubit pair.
    Fidelity F = (1 + <XX> - <YY> + <ZZ>)/4 (exact for |Phi+>). Ideal: XX=+1, YY=-1, ZZ=+1, F=1."""
    cm = coupling_map_from_edges(processor["edges"], processor["num_qubits"])
    sim = simulator(noisy, processor, noise_model)
    out = {"processor": processor["name"], "pair": tuple(physical_pair), "noisy": noisy,
           "shots": shots, "pair_distance": cm.distance(*physical_pair)}
    var = 0.0
    for b in ("XX", "YY", "ZZ"):
        tqc = transpile(bell_circuit(b), basis_gates=_basis(processor), coupling_map=cm,
                        initial_layout=list(physical_pair), optimization_level=OPT_LEVEL,
                        seed_transpiler=SEED)
        counts = sim.run(tqc, shots=shots).result().get_counts()
        e, se = parity_expectation(counts)
        out[b], out[b + "_se"] = e, se
        var += se ** 2
        if b == "ZZ":
            out["cx"] = sum(tqc.count_ops().get(g, 0) for g in TWO_Q)
    out["fidelity"] = (1 + out["XX"] - out["YY"] + out["ZZ"]) / 4
    out["fidelity_se"] = float(np.sqrt(var) / 4)
    return out


# --------------------------------------------------------------------------
# 6. PROCESSOR D: LOAD + VALIDATE processors/processor_D.json
# --------------------------------------------------------------------------
def load_processor(path: str) -> dict:
    with open(path) as f:
        p = json.load(f)
    p["edges"] = [tuple(e) for e in p["edges"]]
    return p


def validate_processor_d(p: dict, required_qubits: int) -> list:
    """Returns a list of rule violations (empty list = valid)."""
    errs = []
    n = p.get("num_qubits")
    if not isinstance(n, int) or n < required_qubits or n > D_MAX_QUBITS:
        errs.append(f"num_qubits must be an integer in [{required_qubits}, {D_MAX_QUBITS}]")
        return errs
    if sorted(p.get("basis_gates", [])) not in [sorted(g) for g in ALLOWED_D_GATE_SETS]:
        errs.append(f"basis_gates must be one of {list(ALLOWED_D_GATE_SETS)}")
    for key in ("error_rates", "justification"):
        if key not in p:
            errs.append(f"missing required field '{key}'")
    if "justification" in p and len(str(p["justification"]).split()) < 40:
        errs.append("justification must be one paragraph (at least 40 words)")
    deg = {q: 0 for q in range(n)}
    seen = set()
    for a, b in p.get("edges", []):
        if a == b or not (0 <= a < n and 0 <= b < n):
            errs.append(f"invalid edge {(a, b)}")
            continue
        key = tuple(sorted((a, b)))
        if key in seen:
            errs.append(f"duplicate edge {key}")
        seen.add(key)
        deg[a] += 1
        deg[b] += 1
    hi = [q for q, d in deg.items() if d > D_MAX_DEGREE]
    if hi:
        errs.append(f"qubits {hi} exceed max degree {D_MAX_DEGREE}")
    adj = {q: set() for q in range(n)}
    for a, b in seen:
        adj[a].add(b)
        adj[b].add(a)
    reach, dq = {0}, deque([0])
    while dq:
        for nb in adj[dq.popleft()]:
            if nb not in reach:
                reach.add(nb)
                dq.append(nb)
    if len(reach) != n:
        errs.append("coupling graph must be connected")
    nz = p.get("error_rates", {})
    if nz.get("p1", P1_DEPOL) < P1_DEPOL or nz.get("p2", P2_DEPOL) < P2_DEPOL \
            or nz.get("p_readout", P_READOUT) < P_READOUT:
        errs.append("noise rates in the JSON may not be lower (better) than the official model")
    return errs


# --------------------------------------------------------------------------
# 7. SIMULATION TRACK: TFIM, OBSERVABLES, ANSATZ, TROTTER, EXACT REFERENCES
# --------------------------------------------------------------------------
from qiskit.quantum_info import SparsePauliOp, Statevector, DensityMatrix, state_fidelity  # noqa: E402
from qiskit.circuit import ParameterVector  # noqa: E402
from scipy.sparse.linalg import expm_multiply  # noqa: E402

NEEL_LABEL_4 = "1010"     # Qiskit label: qubits 1 and 3 in |1>  ->  Z = (+1, -1, +1, -1)


def _pauli(n, ops):
    """ops = {qubit: 'X'|'Y'|'Z'} -> Qiskit label (qubit 0 right-most)."""
    lbl = ["I"] * n
    for q, p in ops.items():
        lbl[n - 1 - q] = p
    return "".join(lbl)


def tfim_hamiltonian(n: int, J: float = 1.0, g: float = 1.0, periodic: bool = False) -> SparsePauliOp:
    """H = -J sum_i Z_i Z_{i+1} - g sum_i X_i. Official runs: OPEN chain (periodic=False)."""
    bonds = [(i, i + 1) for i in range(n - 1)] + ([(n - 1, 0)] if periodic and n > 2 else [])
    terms = [(_pauli(n, {a: "Z", b: "Z"}), -J) for a, b in bonds] + [(_pauli(n, {i: "X"}), -g) for i in range(n)]
    return SparsePauliOp.from_list(terms)


def observable_ops(n: int) -> dict:
    """Official observables (all normalised per site / per bond)."""
    return {
        "mx": SparsePauliOp.from_list([(_pauli(n, {i: "X"}), 1 / n) for i in range(n)]),
        "czz_nn": SparsePauliOp.from_list([(_pauli(n, {i: "Z", i + 1: "Z"}), 1 / (n - 1)) for i in range(n - 1)]),
        "mz2": (SparsePauliOp.from_list([(_pauli(n, {i: "Z"}), 1.0) for i in range(n)]) ** 2).simplify() * (1 / n ** 2),
        "mz": SparsePauliOp.from_list([(_pauli(n, {i: "Z"}), 1 / n) for i in range(n)]),
        "z0": SparsePauliOp.from_list([(_pauli(n, {0: "Z"}), 1.0)]),
        "ms": SparsePauliOp.from_list([(_pauli(n, {i: "Z"}), (-1) ** i / n) for i in range(n)]),
    }


def expectations(state, ops: dict) -> dict:
    sv = state if isinstance(state, (Statevector, DensityMatrix)) else Statevector(state)
    return {k: float(np.real(sv.expectation_value(o))) for k, o in ops.items()}


def exact_spectrum(H: SparsePauliOp, k: int = 2):
    """Lowest k eigenvalues and eigenvectors (dense numpy)."""
    w, v = np.linalg.eigh(H.to_matrix())
    return w[:k], [Statevector(np.ascontiguousarray(v[:, i])) for i in range(k)]


def _zz(qc, a, b, theta, zz_mode):
    """exp(-i theta/2 Z_a Z_b). zz_mode 'cx': CX-RZ-CX ; 'rzz': one RZZ gate."""
    if zz_mode == "rzz":
        qc.rzz(theta, a, b)
    else:
        qc.cx(a, b)
        qc.rz(theta, b)
        qc.cx(a, b)


def hva_ansatz(n: int, layers: int, zz_mode: str = "cx"):
    """Hamiltonian Variational Ansatz (recommended for PS-S1): start in |+>^n (ground state of
    -g sum X), then `layers` x [ ZZ layer on all open-chain bonds with angle gamma_l,
    RX layer on all qubits with angle beta_l ]. 2 parameters per layer.
    Bonds are applied even bonds first, then odd bonds (maps onto a line coupling map)."""
    gam, bet = ParameterVector("gamma", layers), ParameterVector("beta", layers)
    qc = QuantumCircuit(n)
    qc.h(range(n))
    for l in range(layers):
        for start in (0, 1):
            for a in range(start, n - 1, 2):
                _zz(qc, a, a + 1, gam[l], zz_mode)
        for q in range(n):
            qc.rx(bet[l], q)
    return qc, list(gam) + list(bet)


def _bond_layers(n, periodic):
    """Even bonds (0,1),(2,3),... then odd bonds (1,2),(3,4),... ; a ring adds (n-1,0) to the
    odd layer (n even) so each layer is a set of disjoint pairs."""
    even = [(a, a + 1) for a in range(0, n - 1, 2)]
    odd = [(a, a + 1) for a in range(1, n - 1, 2)]
    layers = [even, odd]
    if periodic and n > 2:
        if n % 2 == 0:
            odd.append((n - 1, 0))
        else:
            layers.append([(n - 1, 0)])   # odd ring: closing bond in its own layer
    return layers


def trotter_circuit(n: int, J: float, g: float, t: float, steps: int, order: int = 1,
                    zz_mode: str = "cx", initial_label: str | None = None,
                    periodic: bool = False) -> QuantumCircuit:
    """Official Trotter circuits for H = -J sum ZZ - g sum X, dt = t/steps.
    PS-S2/S3 use the RING (periodic=True); PS-S1 models use the open chain.
    order=1:  U1(dt) = exp(-i H_X dt) exp(-i H_ZZ dt)          (ZZ layer first, then X layer)
    order=2:  U2(dt) = exp(-i H_X dt/2) exp(-i H_ZZ dt) exp(-i H_X dt/2)
    exp(+i J dt Z_aZ_b) = RZZ(-2 J dt) ;  exp(+i g dt X) = RX(-2 g dt).  No measurements."""
    if initial_label is None:                       # Neel state: Z_i = (-1)^i
        initial_label = "".join("1" if i % 2 else "0" for i in reversed(range(n)))
    qc = QuantumCircuit(n, name=f"trotter_o{order}_n{steps}")
    for q, b in enumerate(reversed(initial_label)):
        if b == "1":
            qc.x(q)
    dt = t / steps if steps else 0.0

    def zz_layer(tau):
        for layer in _bond_layers(n, periodic):
            for a, b in layer:
                _zz(qc, a, b, -2 * J * tau, zz_mode)

    def x_layer(tau):
        for q in range(n):
            qc.rx(-2 * g * tau, q)

    for _ in range(steps):
        if order == 1:
            zz_layer(dt)
            x_layer(dt)
        elif order == 2:
            x_layer(dt / 2)
            zz_layer(dt)
            x_layer(dt / 2)
        else:
            raise ValueError("order must be 1 or 2")
    return qc


def exact_evolution(H: SparsePauliOp, psi0: Statevector, times) -> list:
    """Exact |psi(t)> = exp(-i H t)|psi0> at each time (scipy expm_multiply)."""
    Hs = H.to_matrix(sparse=True)
    return [Statevector(np.ascontiguousarray(expm_multiply(-1j * Hs * t, psi0.data))) for t in times]


def state_error(psi_a: Statevector, psi_b: Statevector) -> float:
    """Official Trotter state error: 2-norm || |a> - |b> || (no phase alignment; all terms traceless)."""
    return float(np.linalg.norm(psi_a.data - psi_b.data))


def _layout_maps(tqc, n_logical):
    lay = tqc.layout
    if lay is None:
        return list(range(n_logical)), list(range(n_logical))
    return (list(lay.initial_index_layout(filter_ancillas=True))[:n_logical],
            list(lay.final_index_layout(filter_ancillas=True))[:n_logical])


def noisy_state_fidelity(circuit: QuantumCircuit, target: Statevector, processor: dict,
                         scale: float = 1.0, noisy: bool = True) -> float:
    """REQUIRED PS-S3 metric (density-matrix simulation, gate noise only, no readout):
    F = <psi_exact| rho |psi_exact>, where rho is the state of the logical qubits after the
    circuit (incl. its initial-state preparation) is transpiled for `processor` and run under the
    official noise model x `scale`. Layout/routing permutations are handled."""
    n = circuit.num_qubits
    tqc = transpile_for(circuit, processor)
    _, final = _layout_maps(tqc, n)
    run = tqc.copy()
    run.save_density_matrix(qubits=final, label="rho")
    sim = AerSimulator(method="density_matrix",
                       noise_model=official_noise_model(scale=scale) if noisy else None)
    rho = sim.run(run).result().data()["rho"]
    return float(state_fidelity(target, DensityMatrix(rho)))


def z_observables_from_counts(counts: dict, n: int) -> dict:
    """Z-basis observables from measured counts (keys little-endian): Z0, staggered Ms, Mz^2/N^2,
    nearest-neighbour ZZ, with standard errors of Z0 and Ms."""
    tot = sum(counts.values())
    z0 = ms = mz2 = czz = 0.0
    ms2 = z02 = 0.0
    for k, c in counts.items():
        z = [1 - 2 * int(b) for b in reversed(k.replace(" ", ""))][:n]
        w = c / tot
        z0 += w * z[0]
        m = sum((-1) ** i * z[i] for i in range(n)) / n
        ms += w * m
        ms2 += w * m * m
        mz2 += w * (sum(z) / n) ** 2
        czz += w * sum(z[i] * z[i + 1] for i in range(n - 1)) / (n - 1)
    return {"z0": z0, "z0_se": float(np.sqrt(max(1 - z0 ** 2, 0) / tot)), "ms": ms,
            "ms_se": float(np.sqrt(max(ms2 - ms ** 2, 0) / tot)), "mz2": mz2, "czz_nn": czz}


def run_z_measurement(circuit: QuantumCircuit, processor: dict, shots: int = SHOTS,
                      noisy: bool = True, scale: float = 1.0) -> dict:
    """Measure all logical qubits in Z (clbit i = logical qubit i), transpile for the processor,
    run ideal or noisy, return z_observables_from_counts."""
    n = circuit.num_qubits
    qc = circuit.copy()
    from qiskit import ClassicalRegister
    cr = ClassicalRegister(n, "m")
    qc.add_register(cr)
    qc.measure(range(n), cr)
    tqc = transpile_for(qc, processor)
    sim = simulator(noisy, processor, scale=scale) if noisy else AerSimulator(seed_simulator=SEED)
    counts = sim.run(tqc, shots=shots, seed_simulator=SEED).result().get_counts()
    return z_observables_from_counts(counts, n)


class CountedCost:
    """Wrap a cost function; counts calls and keeps the history (convergence curves)."""

    def __init__(self, fn):
        self.fn, self.calls, self.history = fn, 0, []

    def __call__(self, x):
        self.calls += 1
        v = float(self.fn(x))
        self.history.append(v)
        return v


def energy_statevector(circuit: QuantumCircuit, op: SparsePauliOp) -> float:
    return float(np.real(Statevector(circuit).expectation_value(op)))


def noisy_density_matrix(circuit: QuantumCircuit, processor: dict, scale: float = 1.0,
                         noisy: bool = True) -> DensityMatrix:
    """Density matrix of the logical qubits after `circuit` runs on `processor` under the
    official noise model x scale (gate noise only). Layout permutations are handled."""
    n = circuit.num_qubits
    tqc = transpile_for(circuit, processor)
    _, final = _layout_maps(tqc, n)
    run = tqc.copy()
    run.save_density_matrix(qubits=final, label="rho")
    sim = AerSimulator(method="density_matrix",
                       noise_model=official_noise_model(scale=scale) if noisy else None)
    return DensityMatrix(sim.run(run).result().data()["rho"])


def noisy_expectations(circuit: QuantumCircuit, ops: dict, processor: dict, scale: float = 1.0) -> dict:
    """PS-S1 noisy observables on Processor D: exact expectation values in the noisy density matrix."""
    rho = noisy_density_matrix(circuit, processor, scale)
    return {k: float(np.real(rho.expectation_value(o))) for k, o in ops.items()}
