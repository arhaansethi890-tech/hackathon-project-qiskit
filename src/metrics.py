"""Small, explicit metric helpers used by generated analysis tables."""
from __future__ import annotations
import math
import numpy as np

def mean_sd_sem(values):
    """Return n, mean, sample SD (ddof=1), and SEM; SD/SEM are NaN when n<2."""
    x=np.asarray(list(values),dtype=float)
    x=x[np.isfinite(x)]
    n=int(x.size)
    if n == 0:
        return {"n":0,"mean":math.nan,"sample_sd":math.nan,"sem":math.nan}
    return {"n":n,"mean":float(np.mean(x)),
            "sample_sd":float(np.std(x,ddof=1)) if n>1 else math.nan,
            "sem":float(np.std(x,ddof=1)/math.sqrt(n)) if n>1 else math.nan}

def signed_and_absolute_error(estimate, reference):
    signed=float(estimate)-float(reference)
    return {"signed_error":signed,"absolute_error":abs(signed),
            "relative_absolute_error":abs(signed)/abs(float(reference)) if reference else math.nan}

def shot_sem(variances, shots):
    """Combine independent Pauli-group sampling SEMs in quadrature."""
    v=np.asarray(list(variances),dtype=float)
    s=np.asarray(list(shots),dtype=float)
    if v.shape != s.shape or np.any(s<=0) or np.any(v<0):
        raise ValueError("variances and positive shot counts must have matching shapes")
    return float(math.sqrt(np.sum(v/s)))
