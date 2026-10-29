"""Generate release figures only from the saved primary A/B result tables."""
from pathlib import Path
import json
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/figures';OUT.mkdir(parents=True,exist_ok=True)
COLORS={'A_branch':'#2563eb','B_ref12':'#e87924','ideal logical':'#64748b'}
def save(fig,name):fig.tight_layout();fig.savefig(OUT/name,dpi=180);plt.close(fig)
for pid in ('processor_A','processor_B'):
    cfg=json.loads((ROOT/'processors'/f'{pid}.json').read_text());g=nx.Graph();g.add_nodes_from(range(cfg['qubit_count']));g.add_edges_from(cfg['edges'])
    pos=nx.spring_layout(g,seed=42);fig,ax=plt.subplots(figsize=(6,4))
    nx.draw_networkx(g,pos,node_color=COLORS[cfg['processor_id']],node_size=700,font_color='white',edge_color='#64748b',width=2,ax=ax)
    ax.set_title(f"{cfg['name']} · {cfg['qubit_count']} nodes · {g.number_of_edges()} links\nGuide reference graph (not hardware calibration)");ax.axis('off')
    save(fig,f"{cfg['processor_id']}_coupling.png")
ideal=pd.read_csv(ROOT/'results/tables/ideal_architecture_results.csv');v=ideal[ideal.architecture=='ideal logical']
fig,ax=plt.subplots(figsize=(7,4.5))
for seed,rows in v.groupby('seed'):
    ax.plot(rows.g,rows.approximation_or_error,marker='o',label=f"init seed {seed}")
failed=v[(v.g==1.5)&(v.seed==42)]
if len(failed):ax.scatter(failed.g,failed.approximation_or_error,marker='X',s=110,color='red',label='preserved seed-42 failure')
ax.set_yscale('log');ax.set(xlabel='Field g (J=1)',ylabel='Absolute energy error',title='Ideal VQE error · 16 parameters · L-BFGS-B');ax.grid(True,which='both',alpha=.2);ax.legend(fontsize=8)
save(fig,'ideal_vqe_energy_error.png')
phys=ideal[(ideal.g==1.)&(ideal.seed==42)&ideal.architecture.isin(['Processor A_branch','Processor B_ref12'])].set_index('architecture')
fig,axes=plt.subplots(1,2,figsize=(8,4))
for ax,col,title in zip(axes,['cx_count','depth'],['Transpiled CX gates','Transpiled depth']):
    names=['Processor A_branch','Processor B_ref12'];ax.bar(names,[phys.loc[n,col] for n in names],color=[COLORS['A_branch'],COLORS['B_ref12']]);ax.set_title(title);ax.tick_params(axis='x',rotation=18);ax.grid(axis='y',alpha=.2)
fig.suptitle('Ideal circuit resource evidence · g=1, initialization 42, transpiler seed 42')
save(fig,'ideal_ab_resources.png')
noisy=pd.read_csv(ROOT/'results/tables/noisy_results.csv');case=noisy[(noisy.g==1.)&(noisy.seed==42)].set_index('architecture')
fig,ax=plt.subplots(figsize=(7,4.5));names=['Processor A_branch','Processor B_ref12']
ax.bar(names,[case.loc[n,'objective_or_accuracy'] for n in names],yerr=[case.loc[n,'standard_error'] for n in names],capsize=5,color=[COLORS['A_branch'],COLORS['B_ref12']])
ref=float(case.classical_reference.iloc[0]);ax.axhline(ref,color='black',ls='--',label='exact ground energy')
ax.set(ylabel='Sampled energy (J units)',title='Noisy A/B sample · g=1, VQE seed 42 · ±1 shot SEM (not a CI)');ax.legend();ax.grid(axis='y',alpha=.2)
save(fig,'noisy_ab_energy.png')
print('Generated primary figures:',', '.join(p.name for p in sorted(OUT.glob('*.png'))))

paired=pd.read_csv(ROOT/'results/tables/AB_comparison.csv')
paired=paired[paired.row_type=='per_run'].copy()
paired['g']=pd.to_numeric(paired.g)
wide=paired.pivot(index=['g','seed'],columns='architecture',values='noisy_energy')
diff=(wide['Processor A_branch']-wide['Processor B_ref12']).reset_index()
fig,ax=plt.subplots(figsize=(7,4.5))
for g,group in diff.groupby('g'):
    ax.scatter([g]*len(group),group.iloc[:,2],alpha=.75,label=f'g={g:g}')
ax.axhline(0,color='black',ls='--');ax.set(xlabel='Field g (J=1)',ylabel='Paired sampled energy A − B',title='Matched-seed A/B energy differences')
ax.grid(axis='y',alpha=.2);save(fig,'paired_noisy_energy_difference.png')
