"""Export analysis-ready processed CSVs from the generated result tables."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parent
source=ROOT/'results/tables'; target=ROOT/'data/processed';target.mkdir(parents=True,exist_ok=True)
for name in ('AB_comparison.csv','graph_descriptors.csv','noisy_error_decomposition.csv'):
    p=source/name
    if not p.is_file(): raise FileNotFoundError(p.name)
    shutil.copyfile(p,target/name)
e4=ROOT/'results/supplementary/tables'
for name in ('E4_ansatz_patterns.csv','E4_pattern_summary.csv','E4_paired_differences.csv'):
    p=e4/name
    if p.is_file():shutil.copyfile(p,target/name)
print('Exported core processed tables and any already-generated supplementary E4 tables.')
