"""FastAPI application for the local quantum simulation dashboard."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .simulation import run_simulation

logger = logging.getLogger(__name__)


class NoiseParameters(BaseModel):
    """Depolarizing error rates per gate and symmetric readout flip probability."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    p1: float = Field(default=0.001, ge=0.0, le=0.1)
    p2: float = Field(default=0.005, ge=0.0, le=0.25)
    p_readout: float = Field(default=0.01, ge=0.0, le=0.25)


class SimulationRequest(BaseModel):
    """Validated controls for one bounded exploratory simulation request."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    algorithm: Literal["hva-vqe", "random-ry"] = "hva-vqe"
    qubits: int = Field(default=4, ge=2, le=8)
    depth: int = Field(default=3, ge=1, le=8)
    g: float = Field(default=1.0, ge=0.0, le=4.0)
    shots: int = Field(default=2048, ge=256, le=32768)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    noise_enabled: bool = True
    noise: NoiseParameters = Field(default_factory=NoiseParameters)
    zz_mode: Literal["cx", "rzz"] = "rzz"


app = FastAPI(
    title="QFF Quantum Simulation API",
    description=(
        "Local exploratory simulations for the QFF Phase 2 PS-S1 project. "
        "This API does not alter the locked benchmark workflow or claim hardware results."
    ),
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Return a small readiness response for the dashboard."""
    return {"status": "ok", "engine": "qiskit-aer", "mode": "local exploratory"}


@app.get("/api/options")
def options() -> dict:
    """Describe available algorithms and guardrails to clients."""
    return {
        "algorithms": [
            {"id": "hva-vqe", "label": "TFIM Hamiltonian Variational Ansatz (VQE)"},
            {"id": "random-ry", "label": "Seeded random RY/CX circuit"},
        ],
        "limits": {"qubits": [2, 8], "depth": [1, 8], "shots": [256, 32768]},
        "benchmark_note": "Custom settings here are exploratory and separate from official benchmark results.",
    }


@app.post("/api/simulate")
def simulate(request: SimulationRequest) -> dict:
    """Run a validated circuit request and return counts and analysis values."""
    try:
        return run_simulation(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Exploratory quantum simulation failed")
        raise HTTPException(
            status_code=500,
            detail=f"Simulation failed ({type(exc).__name__}); see the local server log.",
        ) from exc


dashboard_dir = Path(__file__).resolve().parents[1] / "dashboard"
if dashboard_dir.is_dir():
    app.mount("/", StaticFiles(directory=dashboard_dir, html=True), name="dashboard")
