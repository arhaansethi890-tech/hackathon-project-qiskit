"""Evidence-based instrumentation for Qiskit preset-pass-manager compilation."""
from __future__ import annotations

from qiskit import transpile
from qiskit.transpiler import generate_preset_pass_manager

LAYOUT_SELECTOR_PASSES = {
    "SabreLayout", "VF2Layout", "TrivialLayout", "DenseLayout",
    "NoiseAdaptiveLayout", "CSPLayout",
}
ROUTING_PASSES = {
    "SabreSwap", "BasicSwap", "LookaheadSwap", "StochasticSwap",
    "Commuting2qGateRouter", "StarPreRouting",
}


def _ops_for_pass_dag(dag):
    """Return operation names and wire indices using the public DAGCircuit.find_bit API."""
    operations=[]
    for node in dag.op_nodes():
        if node.op.name == "swap":
            operations.append([int(dag.find_bit(qubit).index) for qubit in node.qargs])
    return operations


def compile_with_evidence(circuit, *, coupling_map, basis_gates, optimization_level=1,
                          layout_method="sabre", routing_method="sabre", seed_transpiler=42):
    """Compile once with callback evidence, then cross-check against qiskit.transpile.

    The requested strategy is recorded separately from observed pass names. Routing
    SWAPs are captured from the output DAG of routing-capable passes. Final-circuit
    SWAP gates are counted separately by callers from the compiled circuit.
    """
    kwargs={
        "coupling_map":coupling_map,
        "basis_gates":list(basis_gates),
        "optimization_level":int(optimization_level),
        "layout_method":layout_method,
        "routing_method":routing_method,
        "seed_transpiler":int(seed_transpiler),
    }
    manager=generate_preset_pass_manager(**kwargs)
    trace=[]; pass_swaps=[]

    def capture(**event):
        name=event["pass_"].__class__.__name__
        trace.append(name)
        if name == "SabreLayout" or name in ROUTING_PASSES:
            swaps=_ops_for_pass_dag(event["dag"])
            if swaps:
                pass_swaps.append({"pass":name,"swaps":swaps})

    compiled=manager.run(circuit,callback=capture)
    reference=transpile(circuit,**kwargs)
    try:
        same_layout=(compiled.layout.final_index_layout()==reference.layout.final_index_layout())
        same_initial=(compiled.layout.initial_layout.get_virtual_bits()==reference.layout.initial_layout.get_virtual_bits())
    except Exception:
        same_layout=False; same_initial=False
    same_output=(compiled.count_ops()==reference.count_ops() and same_layout and same_initial
                 and abs(float(compiled.global_phase-reference.global_phase))<1e-12)
    selectors=[name for name in trace if name in LAYOUT_SELECTOR_PASSES]
    route_passes=[name for name in trace if name=="SabreLayout" or name in ROUTING_PASSES]
    layout_passes=[name for name in trace if name in LAYOUT_SELECTOR_PASSES or name in {"VF2PostLayout","SabrePreLayout"}]
    swaps=[edge for group in pass_swaps for edge in group["swaps"]]
    evidence={
        "requested_layout_method":layout_method,
        "requested_routing_method":routing_method,
        "seed_transpiler":int(seed_transpiler),
        "optimization_level":int(optimization_level),
        "pass_trace":trace,
        "observed_layout_passes":layout_passes,
        "observed_layout_selection_passes":selectors,
        "layout_selection_pass":selectors[-1] if selectors else "NOT VERIFIED",
        "observed_routing_passes":route_passes,
        "routing_pass":", ".join(dict.fromkeys(route_passes)) if route_passes else "No routing pass observed",
        "routing_swap_pass_evidence":pass_swaps,
        "routing_swaps":swaps,
        "instrumented_pipeline_matches_transpile_output":bool(same_output),
    }
    try:
        evidence["initial_layout"]=[compiled.layout.initial_layout.get_virtual_bits().get(q) for q in circuit.qubits]
        evidence["final_layout"]=list(compiled.layout.final_index_layout()[:circuit.num_qubits])
    except Exception:
        evidence["initial_layout"]=None; evidence["final_layout"]=None
    return compiled,evidence
