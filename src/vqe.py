"""Ideal statevector VQE; uses exact parameter-shift derivatives for the RY ansatz."""
import numpy as np
from scipy.optimize import minimize
from qiskit.quantum_info import Statevector
from .ansatz import make_ansatz, make_pattern_ansatz, parameter_count
from .qiskit_problem import tfim_operator


def parameter_shift_gradient(objective, parameters):
    """Exact gradient for parameters entering once as Pauli-generated rotations."""
    x=np.asarray(parameters,dtype=float)
    grad=np.empty_like(x)
    shift=np.pi/2
    for i in range(x.size):
        plus=x.copy(); minus=x.copy(); plus[i]+=shift; minus[i]-=shift
        grad[i]=(objective(plus)-objective(minus))/2
    return grad

def run_vqe(g, seed=42, reps=3, maxiter=500, initial_parameters=None, pattern="path"):
    """Optimize one controlled initialization. Exact references are not used by the solver.

    Each RY parameter appears once, so d<E>/dtheta = [E(theta+pi/2)-E(theta-pi/2)]/2.
    An explicit `initial_parameters` value is reserved for separately labelled restart diagnostics.
    """
    if pattern not in ("path", "ring", "star"):
        raise ValueError(f"unknown ansatz pattern: {pattern}")
    builder = (lambda x: make_ansatz(x, reps=reps)) if pattern == "path" else (lambda x: make_pattern_ansatz(x, pattern=pattern, reps=reps))
    rng=np.random.default_rng(seed)
    if initial_parameters is None:
        initial=rng.uniform(-0.15,0.15,parameter_count(reps=reps))
        initialization='numpy.default_rng(PCG64), uniform[-0.15,0.15]'
    else:
        initial=np.asarray(initial_parameters,dtype=float).reshape(-1)
        if initial.size!=parameter_count(reps=reps) or not np.isfinite(initial).all():
            raise ValueError(f'initial_parameters must contain {parameter_count(reps=reps)} finite values')
        initial=initial.copy()
        initialization='explicit saved starting parameters; supplemental restart'

    H=tfim_operator(g); eval_count=0; history=[]
    def objective(x):
        nonlocal eval_count
        eval_count+=1
        return float(Statevector.from_instruction(builder(x)).expectation_value(H).real)
    initial_energy=objective(initial.copy())
    def gradient(x):
        return parameter_shift_gradient(objective,x)
    def callback(xk):
        history.append(objective(xk))
    result=minimize(objective,initial,jac=gradient,method='L-BFGS-B',callback=callback,
                    options={'maxiter':maxiter,'ftol':1e-13,'gtol':1e-9,'maxls':30})
    state=Statevector.from_instruction(builder(result.x))
    final=float(state.expectation_value(H).real)
    if not history or history[-1]!=final: history.append(final)
    def diagnostic_objective(x):
        return float(Statevector.from_instruction(builder(x)).expectation_value(H).real)
    final_gradient=parameter_shift_gradient(diagnostic_objective,result.x)
    return {'initial_energy':initial_energy,'energy':final,'parameters':result.x.tolist(),'seed':seed,'reps':reps,
            'success':bool(result.success),'message':str(result.message),'nfev':int(eval_count),
            'nit':int(result.nit),'history':history,'initial_parameters':initial.tolist(),
            'final_gradient_inf_norm':float(np.linalg.norm(final_gradient,np.inf)),
            'final_gradient_l2_norm':float(np.linalg.norm(final_gradient)),
            'final_gradient_method':'exact parameter-shift; diagnostic evaluations are not included in optimizer nfev',
            'optimizer':'L-BFGS-B','gradient_method':'exact parameter-shift','maxiter':int(maxiter),'ftol':1e-13,'gtol':1e-9,'maxls':30,'initialization':initialization,'state':state,'pattern':pattern}
