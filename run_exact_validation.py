"""Recompute and record independent spin, sparse, Pauli, and free-fermion references."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from qiskit.quantum_info import SparsePauliOp

from src.free_fermion import free_fermion_ground_energy, free_fermion_spectrum, free_fermion_x_sum
from src.problem import FIELDS, J, N, dense_hamiltonian, exact_ground_state, observables, sparse_ground_energy, sparse_hamiltonian
from src.qiskit_problem import tfim_operator

ROOT = Path(__file__).resolve().parent
rows=[]
for g in FIELDS:
    h=dense_hamiltonian(g)
    dense_values=np.linalg.eigvalsh(h)
    dense_energy, state=exact_ground_state(g)
    sparse_energy=sparse_ground_energy(g)
    pauli_values=np.linalg.eigvalsh(tfim_operator(g).to_matrix())
    fermion_values=free_fermion_spectrum(g,N,J)
    obs=observables(g)
    rows.append({
        'status':'CURRENT_OCTOBER_14_GUIDE_VERIFIED',
        'N':N,'J':J,'g':float(g),'boundary':'open',
        'dense_ground_energy':dense_energy,
        'sparse_ground_energy':round(sparse_energy,12),
        'qiskit_pauli_ground_energy':float(pauli_values[0]),
        'free_fermion_ground_energy':free_fermion_ground_energy(g,N,J),
        'max_abs_spectrum_diff_dense_sparse':float(np.max(np.abs(dense_values-np.linalg.eigvalsh(sparse_hamiltonian(g).toarray())))),
        'max_abs_spectrum_diff_dense_pauli':float(np.max(np.abs(dense_values-pauli_values))),
        'max_abs_spectrum_diff_dense_free_fermion':float(np.max(np.abs(dense_values-fermion_values))),
        'magnetization_z_sum':obs['magnetization_z_sum'],
        'magnetization_x_sum_dense':obs['magnetization_x_sum'],
        'magnetization_x_sum_free_fermion':free_fermion_x_sum(g,N,J),
        'magnetization_x_per_site':obs['magnetization_x_sum']/N,
        'mz_squared_over_n2':obs['mz_squared_over_n2'],
        'zz_bonds':obs['zz_bonds'],
        'z_sites':obs['z_sites'],'x_sites':obs['x_sites'],
        'ground_state_gap':float(dense_values[1]-dense_values[0]),
        'ground_state_degeneracy_at_numerical_tol':int(np.sum(np.isclose(dense_values,dense_values[0],rtol=0,atol=1e-10))),
    })
    assert np.max(np.abs(dense_values-pauli_values)) < 1e-10
    assert np.max(np.abs(dense_values-fermion_values)) < 1e-10
    assert abs(dense_energy-sparse_energy) < 1e-10
    assert abs(obs['magnetization_x_sum']-free_fermion_x_sum(g,N,J)) < 1e-10

(ROOT/'results/tables').mkdir(parents=True,exist_ok=True)
(ROOT/'results/raw').mkdir(parents=True,exist_ok=True)
pd.DataFrame(rows).to_csv(ROOT/'results/tables/exact_crosscheck.csv',index=False,float_format='%.16g')
(ROOT/'results/raw/exact_crosscheck.json').write_text(json.dumps(rows,indent=2)+'\n')
print('Independent exact checks: dense spin matrix, sparse matrix, Qiskit Pauli matrix, Jordan-Wigner free-fermion spectrum')
print(pd.DataFrame(rows)[['g','dense_ground_energy','sparse_ground_energy','qiskit_pauli_ground_energy','free_fermion_ground_energy','max_abs_spectrum_diff_dense_free_fermion','magnetization_x_sum_dense','magnetization_x_sum_free_fermion','ground_state_gap']].to_string(index=False,float_format=lambda x:f'{x:.15g}'))
