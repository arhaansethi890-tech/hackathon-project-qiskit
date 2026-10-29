# Local API and interactive dashboard

The dashboard provides an exploratory interface for small local Qiskit Aer
experiments. It is separate from the required Phase 2 benchmark: custom qubit
counts, circuit depths, noise rates, and optimizer settings do not alter the
locked benchmark tables or `qff_sim.py` settings.

## Start the dashboard

Create and activate the project virtual environment, then install the pinned
dependencies from the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The same server exposes
interactive API documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
The backend binds to loopback by default and runs only local Aer simulations.

## Request example

```powershell
$body = @{
  algorithm = "hva-vqe"
  qubits = 4
  depth = 3
  g = 1.0
  shots = 2048
  seed = 42
  zz_mode = "rzz"
  noise_enabled = $true
  noise = @{ p1 = 0.001; p2 = 0.005; p_readout = 0.01 }
} | ConvertTo-Json -Depth 4
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/simulate `
  -ContentType 'application/json' -Body $body
```

`GET /api/health` checks readiness, `GET /api/options` describes the available
algorithms and guardrails, and `POST /api/simulate` returns shot counts,
probabilities for every basis state, an ideal statevector, energy and fidelity
metrics, optimizer history, compiled circuit text, and OpenQASM 3 where supported.
The observable results include per-site transverse magnetization `mx`, the
average open-chain nearest-neighbor correlation `czz_nn`, and normalized
`mz2 = ⟨(Σᵢ Zᵢ)²⟩ / N²`. Qiskit bitstrings put qubit 0 at the right-most character.

## Limits and interpretation

- The API accepts 2–8 qubits, 1–8 circuit layers, and 256–32,768 shots. The
  qubit limit bounds the cost of dense exact references and statevector output.
- The HVA option optimizes an open-chain TFIM. The random RY/CX option is a
  reproducible comparison circuit. Both return ideal energy and overlap with the
  exact TFIM ground state; only the HVA uses an optimizer.
- `RZZ` uses one native two-qubit gate for each ZZ rotation in the exploratory
  circuit. `CX` uses the `CX–RZ–CX` decomposition. Both are simulated with local
  synthetic noise when the noise toggle is enabled.
- Ideal statevectors are returned as `[real, imaginary]` amplitude pairs. Noisy
  fidelity is calculated from a pre-measurement density matrix; readout noise
  affects the separate sampled counts.
- No device topology, cloud service, or quantum hardware is used. Custom API
  results are exploratory and must not be presented as required benchmark runs.

## Separate frontend hosting

The API serves the dashboard itself. For frontend iteration with a static server,
serve the `dashboard/` directory on a local origin such as port 5500 and open it
with `?api=http://127.0.0.1:8000`; FastAPI allows that local development origin.
