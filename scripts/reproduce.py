"""Command-line entry point for the current Phase 2 PS-S1 simulation pipeline."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_phase2_s1 import main


if __name__ == "__main__":
    main()
