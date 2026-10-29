"""Create separate E4 figures from its saved supplementary result tables."""
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
TABLES=ROOT/'results/supplementary/tables';OUT=ROOT/'results/supplementary/figures';OUT.mkdir(parents=True,exist_ok=True)
summary=pd.read_csv(TABLES/'E4_pattern_summary.csv')
colors={'Processor A_branch':'#2563eb','Processor B_ref12':'#e87924'}
patterns=['path','ring','star']
fig,axes=plt.subplots(1,2,figsize=(10,4.5))
for ax,metric,title,ylabel in zip(axes,['compiled_cx_count','compiled_depth'],['Mean compiled CX count','Mean compiled circuit depth'],['CX gates','depth in circuit layers']):
    for arch in colors:
        d=summary[summary.architecture==arch].set_index('pattern').loc[patterns]
        ax.errorbar(patterns,d[f'{metric}_mean'],yerr=d[f'{metric}_sample_sd'],marker='o',capsize=4,label=arch,color=colors[arch])
    ax.set_title(title);ax.set_ylabel(ylabel);ax.set_xlabel('logical entangler pattern');ax.grid(axis='y',alpha=.25)
axes[0].legend(fontsize=8)
fig.suptitle('E4 mapped-circuit resources · bars show mean ± sample SD over nine starts')
fig.tight_layout();fig.savefig(OUT/'E4_resources_by_pattern.png',dpi=180);plt.close(fig)
full=pd.read_csv(TABLES/'E4_ansatz_patterns.csv')
fig,axes=plt.subplots(1,3,figsize=(12,4),sharey=True)
for ax,g in zip(axes,[.5,1.,1.5]):
    for arch in colors:
        d=full[(full.g==g)&(full.architecture==arch)].groupby('pattern').noisy_absolute_error.agg(['mean','std']).reindex(patterns)
        ax.errorbar(patterns,d['mean'],yerr=d['std'],marker='o',capsize=4,label=arch,color=colors[arch])
    ax.set_title(f'g = {g:g}');ax.set_xlabel('logical entangler pattern');ax.grid(axis='y',alpha=.25)
axes[0].set_ylabel('absolute sampled energy error (J units; mean ± sample SD)')
axes[-1].legend(fontsize=8)
fig.suptitle('E4 noisy energy error · between-start sample SD, not shot SEM')
fig.tight_layout();fig.savefig(OUT/'E4_noisy_error_by_pattern.png',dpi=180);plt.close(fig)
print('Generated E4 figures: E4_resources_by_pattern.png, E4_noisy_error_by_pattern.png')
