"""Load and validate explicit undirected processor coupling-graph JSON files."""
import json
from pathlib import Path
from qiskit.transpiler import CouplingMap


def load_processor(path):
    path = Path(path)
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read processor JSON at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: processor configuration must be a JSON object")
    try:
        name = data["name"]
        n = data["qubit_count"]
        raw_edges = data["edges"]
    except KeyError as exc:
        raise ValueError(f"{path}: missing required key {exc.args[0]!r}") from exc
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError(f"{name}: qubit_count must be a positive integer")
    if not isinstance(raw_edges, list) or not raw_edges:
        raise ValueError(f"{name}: edges must be a non-empty list")

    edges = []
    seen_edges = set()
    for index, edge in enumerate(raw_edges):
        if not isinstance(edge, list) or len(edge) != 2:
            raise ValueError(f"{name}: edge {index} must be a two-item list")
        a, b = edge
        if any(isinstance(q, bool) or not isinstance(q, int) for q in edge):
            raise ValueError(f"{name}: edge {index} endpoints must be integers")
        if a == b or min(a, b) < 0 or max(a, b) >= n:
            raise ValueError(f"{name}: edge {edge} outside valid {n}-qubit range")
        normalized = tuple(sorted((a, b)))
        if normalized in seen_edges:
            raise ValueError(f"{name}: duplicate undirected edge {normalized}")
        seen_edges.add(normalized)
        edges.append((a, b))

    directed_edges = []
    for a, b in edges:
        directed_edges.extend(((a, b), (b, a)))
    coupling = CouplingMap(couplinglist=[list(edge) for edge in directed_edges])
    if coupling.size() != n:
        raise ValueError(f"{name}: coupling map has {coupling.size()} nodes, expected {n}")
    if not coupling.is_connected():
        raise ValueError(f"{name}: coupling graph must be connected")
    return data, coupling
