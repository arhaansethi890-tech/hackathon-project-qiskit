"""Export topology descriptors and automorphism-collapsed motif placement counts."""
import json
from pathlib import Path
import pandas as pd
from src.graph_analysis import graph_summary,motif_placements
ROOT=Path(__file__).resolve().parent
rows=[]
for pid in ('processor_A','processor_B'):
    cfg=json.loads((ROOT/'processors'/f'{pid}.json').read_text())
    row={"architecture":cfg['processor_id'],"name":cfg['name'],**graph_summary(cfg['qubit_count'],cfg['edges']),**{f"noninduced_{k}_placements":v for k,v in motif_placements(cfg['qubit_count'],cfg['edges']).items()}}
    row['edge_list']=json.dumps(cfg['edges'],separators=(',',':'))
    rows.append(row)
out=ROOT/'results/tables/graph_descriptors.csv';out.parent.mkdir(parents=True,exist_ok=True)
pd.DataFrame(rows).to_csv(out,index=False,float_format='%.16g')
print(pd.DataFrame(rows)[['architecture','nodes','edges','degree_sequence','diameter','average_shortest_path_length','noninduced_P4_placements','noninduced_C4_placements','noninduced_K1,3_placements']].to_string(index=False))
