from qiskit.quantum_info import SparsePauliOp
from .problem import N,J

def tfim_operator(g):
    terms=[]
    for i in range(N-1):
        chars=['I']*N
        chars[N-1-i]='Z'; chars[N-2-i]='Z'
        terms.append((''.join(chars),-J))
    for i in range(N):
        chars=['I']*N; chars[N-1-i]='X'
        terms.append((''.join(chars),-float(g)))
    return SparsePauliOp.from_list(terms).simplify()
