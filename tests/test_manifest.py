import hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def test_manifest_is_byte_reproducible():
    subprocess.run([sys.executable,str(ROOT/'make_manifest.py')],cwd=ROOT,check=True,capture_output=True)
    first=(ROOT/'results/experiment_manifest.json').read_bytes()
    subprocess.run([sys.executable,str(ROOT/'make_manifest.py')],cwd=ROOT,check=True,capture_output=True)
    assert first==(ROOT/'results/experiment_manifest.json').read_bytes()
def test_manifest_paths_and_hashes_are_valid():
    m=json.loads((ROOT/'results/experiment_manifest.json').read_text())
    assert m['schema_version']==1 and 'PS-S1' in m['status']
    assert m['problem']['fields_g']==[.5,1.,1.5]
    assert m['problem']['energy_tolerance']==1e-6
    assert m['primary_architectures']['A_branch']['qubits']==5
    assert m['primary_architectures']['B_ref12']['qubits']==9
    assert m['input_files'] and m['generated_artifacts']
    assert 'legacy_artifacts' not in m
    for item in m['input_files']+m['generated_artifacts']:
        path=Path(item['path'])
        assert not path.is_absolute() and '..' not in path.parts
        target=ROOT/path
        if item['path']=='main.ipynb':
            import nbformat
            nb=nbformat.read(target,as_version=4)
            stable={'metadata':nb.metadata,'cells':[{'cell_type':c.cell_type,'metadata':{k:v for k,v in c.metadata.items() if k!='execution'},'source':c.source} for c in nb.cells]}
            actual=hashlib.sha256(json.dumps(stable,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            assert actual==item['sha256']
        else:
            assert target.is_file() and sha(target)==item['sha256']
    paths=[x['path'] for x in m['input_files']+m['generated_artifacts']]
    assert not any('uploads' in p or 'website' in p or 'extras/legacy' in p for p in paths)
def test_manifest_regenerates_in_a_clean_filesystem_copy(tmp_path):
    copy=tmp_path/'project-copy';shutil.copytree(ROOT,copy,ignore=shutil.ignore_patterns('.venv','__pycache__','.pytest_cache','*.pyc'))
    subprocess.run([sys.executable,str(copy/'make_manifest.py')],cwd=copy,check=True,capture_output=True,text=True)
    assert (copy/'results/experiment_manifest.json').read_bytes()==(ROOT/'results/experiment_manifest.json').read_bytes()

def test_manifest_coverage_and_intentional_exclusions():
    m = json.loads((ROOT / 'results/experiment_manifest.json').read_text(encoding='utf-8'))
    manifest_paths = {item['path'] for item in m['input_files'] + m['generated_artifacts']}
    
    # 1. Self-exclusion policy: manifest does not hash itself
    assert 'results/experiment_manifest.json' not in manifest_paths
    
    # 2. Circular dependency exclusion policy: PUBLIC_EXPORT_SHA256SUMS.txt is excluded from manifest
    assert 'PUBLIC_EXPORT_SHA256SUMS.txt' not in manifest_paths
    
    # 3. Read the intended public checksum list
    checksum_file = ROOT / 'PUBLIC_EXPORT_SHA256SUMS.txt'
    assert checksum_file.is_file()
    checksum_lines = [line.strip().split(None, 1) for line in checksum_file.read_text(encoding='utf-8').splitlines() if line.strip()]
    checksum_paths = {parts[1] for parts in checksum_lines}
    
    # Checksum file must cover manifest
    assert 'results/experiment_manifest.json' in checksum_paths
    # Checksum file must exclude only itself
    assert 'PUBLIC_EXPORT_SHA256SUMS.txt' not in checksum_paths
    
    # 4. Complete coverage assertion: every file in checksum list (except manifest itself) must be in manifest
    uncovered_in_manifest = (checksum_paths - {'results/experiment_manifest.json'}) - manifest_paths
    assert not uncovered_in_manifest, f"Public files missing from manifest: {uncovered_in_manifest}"
    
    # Manifest must not list files outside the checksum list
    extra_in_manifest = manifest_paths - checksum_paths
    assert not extra_in_manifest, f"Manifest files missing from public checksums: {extra_in_manifest}"
    
    # 5. Verify the 3 supplementary topology definitions are in input_files
    input_paths = {item['path'] for item in m['input_files']}
    for name in ('path4.json', 'ring4.json', 'star4.json'):
        expected = f'supplementary/e4_path_ring_star/{name}'
        assert expected in input_paths, f"Missing {expected} from input_files"
