"""Stable independent Aer seeds for each experiment tuple."""
from __future__ import annotations
import hashlib
import json


def derive_simulator_seed(g: float, vqe_seed: int, architecture: str, basis: str, batch: int = 0, variant: str = "kit-literal-all-one-qubit-gates") -> int:
    """Hash the full experiment tuple to a deterministic unsigned 32-bit Aer seed."""
    if basis not in ("X", "Z"):
        raise ValueError("basis must be X or Z")
    if isinstance(batch, bool) or not isinstance(batch, int) or batch < 0:
        raise ValueError("batch must be a non-negative integer")
    if isinstance(vqe_seed, bool) or not isinstance(vqe_seed, int) or vqe_seed < 0:
        raise ValueError("vqe_seed must be a non-negative integer")
    payload=json.dumps({
        "seedDerivationVersion":1,
        "g":format(float(g),'.17g'),
        "vqe_seed":vqe_seed,
        "architecture":str(architecture),
        "basis":basis,
        "batch":batch,
        "variant":str(variant),
    },sort_keys=True,separators=(',',':')).encode('utf-8')
    return int.from_bytes(hashlib.sha256(payload).digest()[:4],byteorder='big',signed=False)
