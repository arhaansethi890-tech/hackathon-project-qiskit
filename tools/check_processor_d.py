"""Check your Processor D file.   python tools/check_processor_d.py processors/processor_D.json <qubits_needed>
<qubits_needed> = qubits of the largest circuit in your required runs (4 for the N = 4 runs, 6 if you do the PS-S1 N = 6 tier)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from qff_sim import load_processor, validate_processor_d  # noqa: E402

if len(sys.argv) != 3:
    print(__doc__); sys.exit(1)
errs = validate_processor_d(load_processor(sys.argv[1]), int(sys.argv[2]))
if errs:
    print("INVALID Processor D:"); [print("  -", e) for e in errs]; sys.exit(2)
print("OK - Processor D satisfies all design rules.")
