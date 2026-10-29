"""Generate per-run, pooled, paired, and sampled-energy error-decomposition tables."""
import ast
from pathlib import Path
import numpy as np
import pandas as pd
from src.metrics import mean_sd_sem

ROOT=Path(__file__).resolve().parent

def summary_row(row_type, g, architecture, values, extra=None):
    out={"row_type":row_type,"g":g,"architecture":architecture}
    for key, vals in values.items():
        stats=mean_sd_sem(vals)
        out[f"{key}_n"]=stats['n'];out[f"{key}_mean"]=stats['mean'];out[f"{key}_sample_sd"]=stats['sample_sd'];out[f"{key}_sem"]=stats['sem']
    out.update(extra or {})
    return out

def main():
    ideal=pd.read_csv(ROOT/'results/tables/ideal_architecture_results.csv')
    logical=ideal[ideal.architecture=='ideal logical']
    noisy=pd.read_csv(ROOT/'results/tables/noisy_results.csv')
    rows=[];decomp=[]
    for _,n in noisy.iterrows():
        v=logical[(logical.g==n.g)&(logical.seed==n.seed)].iloc[0]
        rows.append({"row_type":"per_run","g":float(n.g),"seed":int(n.seed),"architecture":n.architecture,
            "optimizer_success":bool(v.optimizer_success),"optimizer_outcome":v.optimizer_outcome_classification,
            "meets_project_energy_tolerance":bool(v.meets_project_energy_tolerance),
            "ideal_energy":float(v.objective_or_accuracy),"exact_energy":float(v.classical_reference),
            "ideal_signed_error":float(v.objective_or_accuracy-v.classical_reference),
            "ideal_absolute_error":float(v.approximation_or_error),"ideal_relative_absolute_error":float(v.relative_energy_error),
            "noisy_energy":float(n.objective_or_accuracy),"sampled_energy_z":float(n.sampled_energy_z),"sampled_energy_x":float(n.sampled_energy_x),
            "total_noisy_signed_error":float(n.total_noisy_error_signed),"total_noisy_absolute_error":float(n.total_noisy_error_absolute),
            "relative_absolute_error":float(n.relative_energy_error),"shot_sem":float(n.standard_error),"shot_sem_z":float(n.standard_error_z),"shot_sem_x":float(n.standard_error_x),
            "shots_per_basis":int(n.shots),"total_shots_per_energy":2*int(n.shots),"noise_variant":n.noise_variant})
        exact_zz=-sum(float(n[f'exact_ZZ_{i}_{i+1}']) for i in range(3))
        noisy_zz=float(n.sampled_energy_z)
        exact_x=-float(n.g)*4*float(n.exact_Mx_per_site)
        noisy_x=float(n.sampled_energy_x)
        decomp.append({"g":float(n.g),"seed":int(n.seed),"architecture":n.architecture,
            "exact_zz_energy":exact_zz,"sampled_zz_energy":noisy_zz,"zz_error_contribution":noisy_zz-exact_zz,
            "exact_x_energy":exact_x,"sampled_x_energy":noisy_x,"x_error_contribution":noisy_x-exact_x,
            "decomposed_total_error":(noisy_zz-exact_zz)+(noisy_x-exact_x),
            "observed_total_error":float(n.total_noisy_error_signed),"closure_residual":float(n.total_noisy_error_signed-((noisy_zz-exact_zz)+(noisy_x-exact_x))),
            "shot_sem_z":float(n.standard_error_z),"shot_sem_x":float(n.standard_error_x),"shot_sem_total":float(n.standard_error)})
    run_df=pd.DataFrame(rows)
    agg=[]
    metric_cols=["ideal_signed_error","ideal_absolute_error","ideal_relative_absolute_error","noisy_energy","sampled_energy_z","sampled_energy_x","total_noisy_signed_error","total_noisy_absolute_error","relative_absolute_error","shot_sem"]
    for (g,arch),group in run_df.groupby(["g","architecture"],sort=True):
        out={"row_type":"summary_by_g_arch","g":g,"architecture":arch,"n_runs":len(group),
             "optimizer_converged_starts":int(group.optimizer_success.sum()),"optimizer_failed_starts":int((~group.optimizer_success).sum()),
             "project_tolerance_met_starts":int(group.meets_project_energy_tolerance.sum())}
        for col in metric_cols:
            stats=mean_sd_sem(group[col]);out.update({f"{col}_mean":stats['mean'],f"{col}_sample_sd":stats['sample_sd'],f"{col}_sem":stats['sem']})
        agg.append(out)
    paired=[]
    for g,group in run_df.groupby('g',sort=True):
        wide=group.pivot(index='seed',columns='architecture',values='noisy_energy')
        diff=wide['Processor A_branch']-wide['Processor B_ref12']
        st=mean_sd_sem(diff)
        paired.append({"row_type":"paired_difference","g":float(g),"architecture":"A_minus_B","n_pairs":st['n'],"mean":st['mean'],"sample_sd":st['sample_sd'],"sem":st['sem'],"difference_definition":"sampled A energy minus sampled B energy; matched by g and VQE initialization seed"})
    allwide=run_df.pivot(index=['g','seed'],columns='architecture',values='noisy_energy')
    diff=allwide['Processor A_branch']-allwide['Processor B_ref12'];st=mean_sd_sem(diff)
    paired.append({"row_type":"paired_difference","g":"all","architecture":"A_minus_B","n_pairs":st['n'],"mean":st['mean'],"sample_sd":st['sample_sd'],"sem":st['sem'],"difference_definition":"sampled A energy minus sampled B energy; matched by g and VQE initialization seed"})
    out=ROOT/'results/tables/AB_comparison.csv'
    pd.concat([run_df,pd.DataFrame(agg),pd.DataFrame(paired)],ignore_index=True,sort=False).to_csv(out,index=False,float_format='%.16g')
    pd.DataFrame(decomp).to_csv(ROOT/'results/tables/noisy_error_decomposition.csv',index=False,float_format='%.16g')
    print('Generated AB comparison: per_run=18, summary_by_g_arch=6, paired_difference=4 rows.')
    print(pd.DataFrame(agg)[['g','architecture','n_runs','optimizer_converged_starts','optimizer_failed_starts','noisy_energy_mean','total_noisy_absolute_error_mean','relative_absolute_error_mean','shot_sem_mean']].to_string(index=False,float_format=lambda x:f'{x:.9g}'))
    print('Paired A-B energy differences by field and pooled:')
    print(pd.DataFrame(paired).to_string(index=False,float_format=lambda x:f'{x:.9g}'))
    print('Maximum error-decomposition closure residual:',float(np.max(np.abs(pd.DataFrame(decomp).closure_residual))))

if __name__=='__main__': main()
