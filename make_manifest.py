"""Create a deterministic, path-safe source and artifact SHA-256 manifest."""
import hashlib
import json
import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import nbformat
from src.problem import FIELDS,J,N,PROJECT_VQE_ABS_ERROR_TOLERANCE
ROOT=Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def notebook_source_bytes(path):
    nb=nbformat.read(path,as_version=4)
    stable={"metadata":nb.metadata,"cells":[{"cell_type":c.cell_type,"metadata":{k:v for k,v in c.metadata.items() if k!="execution"},"source":c.source} for c in nb.cells]}
    return json.dumps(stable,sort_keys=True,ensure_ascii=False).encode()
def notebook_digest(path):
    return hashlib.sha256(notebook_source_bytes(path)).hexdigest()
def listed(patterns):
    return sorted({p for pattern in patterns for p in ROOT.glob(pattern) if p.is_file()})
source=listed(["README.md","report.md","AI_DISCLOSURE.md","requirements.txt","main.ipynb","project_metadata.json","docs/*.md","data/**/*.md","data/raw/*.json","pytest.ini","src/*.py","tests/*.py","scripts/reproduce.py","scripts/render_docs.py","scripts/cleanroom_reproduce.py","scripts/build_public_export.py","scripts/run_e4_ansatz_patterns.py","scripts/make_e4_figures.py","processors/*.json","supplementary/e4_path_ring_star/*.json","run_*.py","make_figures.py","make_manifest.py",".github/workflows/*.yml",".gitignore"])
artifacts=listed(["results/raw/*.json","results/tables/*.csv","results/figures/*.png","results/logs/*.txt","results/supplementary/raw/*.json","results/supplementary/tables/*.csv","results/supplementary/figures/*.png","data/processed/*.csv"])
packages=["numpy","scipy","pandas","matplotlib","networkx","qiskit","qiskit-aer","pytest","nbformat","nbconvert","ipykernel"]
versions={}
for name in packages:
    try: versions[name]=version(name)
    except PackageNotFoundError: versions[name]="NOT INSTALLED"
manifest={
    "schema_version":1,
    "status":"PS-S1 simulation artifact snapshot; no external action was performed by this workflow", 
    "problem":{"id":"PS-S1","N":N,"J":J,"fields_g":list(FIELDS),"boundary":"open four-site chain confirmed by October 14 Master Guide p.5 Pauli terms","energy_tolerance":PROJECT_VQE_ABS_ERROR_TOLERANCE,"tolerance_authority":"project reporting convention, not an organizer mandate"},
    "primary_architectures":{"A_branch":{"config":"processors/processor_A.json","qubits":5},"B_ref12":{"config":"processors/processor_B.json","qubits":9}},
    "experiment_settings":{"ansatz":"RY + nearest-neighbor CX; reps=3; 16 parameters","optimizer":"L-BFGS-B with exact parameter-shift gradient","initialization_seeds":[42,7,21],"transpiler":{"optimization_level":1,"layout":"sabre","routing":"sabre","seed":42},"noisy_shots_per_basis":4096,"noise":{"single_qubit_depolarizing_p":0.001,"cx_depolarizing_p":0.005,"symmetric_readout_flip_p":0.01,"single_qubit_noisy_gates":["rz","sx","x"]}},
    "runtime":{"python":platform.python_version(),"packages":versions},
    "hash_semantics":"All paths are repository-relative. main.ipynb is hashed over canonical source and metadata, excluding execution outputs and execution counts; its bytes field is the canonical source representation length. Other files use raw SHA-256 and byte length. results/experiment_manifest.json does not hash itself (self-exclusion); PUBLIC_EXPORT_SHA256SUMS.txt is intentionally excluded to prevent circular hash dependency (the checksum inventory covers the manifest).",
    "notebook_source_sha256":notebook_digest(ROOT/"main.ipynb"),
    "input_files":[{"path":p.relative_to(ROOT).as_posix(),"sha256":notebook_digest(p) if p.name=="main.ipynb" else sha(p),"bytes":len(notebook_source_bytes(p)) if p.name=="main.ipynb" else p.stat().st_size} for p in source],
    "generated_artifacts":[{"path":p.relative_to(ROOT).as_posix(),"sha256":sha(p),"bytes":p.stat().st_size} for p in artifacts],
    "limitations":["No hardware execution; architecture/noise results are local simulation under declared synthetic assumptions.","The guide says magnetization but does not define axis or normalization; the reported observables are explicit project conventions.","The supplied source ZIP and Problem_Statment_Details.pdf were not present, so ZIP extraction and checksum comparison are unavailable.","Portal team/problem selection, AI-policy compliance, contributor approval, and license status were not checked."]
}
(ROOT/"results/experiment_manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
print(f"Wrote results/experiment_manifest.json: {len(source)} source hashes and {len(artifacts)} generated hashes")
