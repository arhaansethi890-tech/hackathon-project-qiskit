"""Build a whitelisted, path-safe public export and deterministic public ZIP.

No publication, push, submission, or external action is performed.
"""
from __future__ import annotations
import hashlib, os, shutil, zipfile
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public'/'PS-S1_public_export'
FIXED=['README.md','report.md','AI_DISCLOSURE.md','requirements.txt','main.ipynb','project_metadata.json','.gitignore','pytest.ini','make_manifest.py','make_figures.py']

def selected_files():
    paths={ROOT/p for p in FIXED}
    for pattern in ('docs/*.md','src/*.py','tests/*.py','scripts/reproduce.py','scripts/render_docs.py','scripts/cleanroom_reproduce.py','scripts/build_public_export.py','scripts/run_e4_ansatz_patterns.py','scripts/make_e4_figures.py','processors/*.json','data/raw/*.json','data/raw/*.md','data/processed/*.csv','data/processed/*.md','run_*.py','.github/workflows/*.yml','results/raw/*.json','results/tables/*.csv','results/figures/*.png','results/supplementary/raw/*.json','results/supplementary/tables/*.csv','results/supplementary/figures/*.png'):
        paths.update(ROOT.glob(pattern))
    # Historical E4 inputs are included only as the three tiny topology definitions.
    paths.update((ROOT/'supplementary/e4_path_ring_star'/f'{n}.json') for n in ('path4','ring4','star4'))
    paths.add(ROOT/'results/logs/circuit_comparison.txt')
    paths.add(ROOT/'results/experiment_manifest.json')
    return sorted((p for p in paths if p.is_file()),key=lambda p:p.relative_to(ROOT).as_posix())

def main():
    if OUT.exists():shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for path in selected_files():
        rel=path.relative_to(ROOT)
        dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,dest)
    sums=[]
    for path in sorted((p for p in OUT.rglob('*') if p.is_file()),key=lambda p:p.relative_to(OUT).as_posix()):
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        sums.append(f'{digest}  {path.relative_to(OUT).as_posix()}')
    sums_text = '\n'.join(sums) + '\n'
    (ROOT/'PUBLIC_EXPORT_SHA256SUMS.txt').write_text(sums_text,encoding='utf-8',newline='\n')
    (OUT/'PUBLIC_EXPORT_SHA256SUMS.txt').write_text(sums_text,encoding='utf-8',newline='\n')
    archive=ROOT/'public'/'PS-S1_public.zip'
    archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in sorted((p for p in OUT.rglob('*') if p.is_file()),key=lambda p:p.relative_to(OUT).as_posix()):
            rel=path.relative_to(OUT).as_posix()
            info=zipfile.ZipInfo(rel,date_time=(2026,10,15,12,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,path.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    print(f'Public export tree: {len(sums)} files; ZIP: public/PS-S1_public.zip ({archive.stat().st_size} bytes).')
    print('The export is not pushed, published, or submitted.')
if __name__=='__main__':main()
