"""Four-site open transverse-field Ising chain."""
import numpy as np
from scipy.sparse import csr_matrix, kron, identity

N = 4
J = 1.0
FIELDS = (0.5, 1.0, 1.5)
# Project reporting threshold only; the organizer kit does not specify an energy tolerance.
PROJECT_VQE_ABS_ERROR_TOLERANCE = 1e-6


def _validate_parameters(g: float, n: int, coupling: float = J) -> tuple[float, int, float]:
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or n < 1:
        raise ValueError(f"n must be a positive integer, got {n!r}")
    try:
        field, j = float(g), float(coupling)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"g and J must be finite real numbers, got {g!r}, {coupling!r}") from exc
    if not np.isfinite(field) or not np.isfinite(j):
        raise ValueError("g and J must be finite real numbers")
    return field, int(n), j

def dense_hamiltonian(g: float, n: int = N, coupling: float = J) -> np.ndarray:
    """H=-J sum Zi Zi+1-g sum Xi; site 0 is the least-significant bit."""
    g,n,j=_validate_parameters(g,n,coupling)
    I=np.eye(2, dtype=float); X=np.array([[0.,1.],[1.,0.]])
    Z=np.diag([1.,-1.])
    def op(local):
        # Kronecker factors are ordered most-significant site down to site 0.
        mats=[local.get(q,I) for q in range(n-1,-1,-1)]
        out=mats[0]
        for m in mats[1:]: out=np.kron(out,m)
        return out
    H=np.zeros((2**n,2**n))
    for i in range(n-1): H -= j*op({i:Z,i+1:Z})
    for i in range(n): H -= g*op({i:X})
    return H

def sparse_hamiltonian(g: float, n: int=N, coupling: float = J):
    """Independently built sparse Kronecker Hamiltonian (same explicit site convention)."""
    g,n,j=_validate_parameters(g,n,coupling)
    I=identity(2,format='csr',dtype=float); X=csr_matrix([[0.,1.],[1.,0.]])
    Z=csr_matrix([[1.,0.],[0.,-1.]])
    def op(local):
        mats=[local.get(q,I) for q in range(n-1,-1,-1)]
        out=mats[0]
        for m in mats[1:]: out=kron(out,m,format='csr')
        return out
    H=csr_matrix((2**n,2**n),dtype=float)
    for i in range(n-1): H -= j*op({i:Z,i+1:Z})
    for i in range(n): H -= g*op({i:X})
    return H

def exact_ground_state(g: float, coupling: float = J):
    vals, vecs=np.linalg.eigh(dense_hamiltonian(g, coupling=coupling))
    return float(vals[0]), vecs[:,0]

def sparse_low_energy_eigensystem(g: float, k: int = 1, n: int = N, coupling: float = J):
    """Return the k lowest sparse eigenpairs, sorted by ascending energy."""
    from scipy.sparse.linalg import eigsh
    matrix=sparse_hamiltonian(g, n=n, coupling=coupling)
    if isinstance(k, bool) or not isinstance(k, (int, np.integer)) or not 1<=k<matrix.shape[0]:
        raise ValueError(f"k must be an integer in [1, {matrix.shape[0]-1}]")
    if matrix.nnz == 0:
        return np.zeros(int(k), dtype=float), np.eye(matrix.shape[0], int(k), dtype=float)
    values,vectors=eigsh(matrix,k=int(k),which='SA',tol=1e-13)
    order=np.argsort(values)
    return values[order],vectors[:,order]

def sparse_ground_state(g: float, n: int = N, coupling: float = J):
    """Return the lowest sparse eigenvalue and normalized eigenvector."""
    values,vectors=sparse_low_energy_eigensystem(g,k=1,n=n,coupling=coupling)
    return float(values[0]),vectors[:,0]

def sparse_ground_energy(g: float, n: int = N, coupling: float = J):
    """Lowest eigenvalue from the independently assembled sparse Hamiltonian."""
    return sparse_ground_state(g,n=n,coupling=coupling)[0]

def state_observables(state: np.ndarray, n: int = N) -> dict:
    """Evaluate the requested Pauli observables on a normalized state vector."""
    psi=np.asarray(state,dtype=complex).reshape(-1)
    if psi.size!=2**n or not np.isfinite(psi).all():
        raise ValueError(f"state must be a finite vector of length {2**n}")
    if not np.isclose(np.linalg.norm(psi),1.0,atol=1e-10,rtol=0):
        raise ValueError("state vector must be normalized")
    I=np.eye(2);X=np.array([[0.,1.],[1.,0.]]);Z=np.diag([1.,-1.])
    def op(local):
        mats=[local.get(q,I) for q in range(n-1,-1,-1)]
        out=mats[0]
        for m in mats[1:]:out=np.kron(out,m)
        return out
    def mean(local):return float(np.vdot(psi,op(local)@psi).real)
    z=[mean({i:Z}) for i in range(n)];x=[mean({i:X}) for i in range(n)]
    mz_operator=sum((op({i:Z}) for i in range(n)),start=np.zeros((2**n,2**n)))
    return {"Mz_per_site":sum(z)/n,"Mx_per_site":sum(x)/n,
            "Mz2_normalized":float(np.vdot(psi,(mz_operator@mz_operator)@psi).real)/(n*n),
            "zz_correlators":[mean({i:Z,i+1:Z}) for i in range(n-1)],
            "z_sites":z,"x_sites":x}

def observables(g: float, coupling: float = J):
    e, psi=exact_ground_state(g,coupling=coupling); n=N
    def mean(op): return float(np.vdot(psi,op@psi).real)
    X=np.array([[0.,1.],[1.,0.]]); Z=np.diag([1.,-1.]); I=np.eye(2)
    def siteop(local):
        out=None
        for q in range(n-1,-1,-1):
            m=local.get(q,I); out=m if out is None else np.kron(out,m)
        return out
    z_sites=[mean(siteop({i:Z})) for i in range(n)]
    x_sites=[mean(siteop({i:X})) for i in range(n)]
    mz=sum(z_sites)
    mx=sum(x_sites)
    m2=sum(siteop({i:Z}) for i in range(n))
    return {'energy':e,'magnetization_z_sum':mz,'magnetization_x_sum':mx,
            'z_sites':z_sites,'x_sites':x_sites,
            'mz_squared_over_n2':mean(m2@m2)/n**2,
            'zz_bonds':[mean(siteop({i:Z,i+1:Z})) for i in range(n-1)],
            'state':psi}
