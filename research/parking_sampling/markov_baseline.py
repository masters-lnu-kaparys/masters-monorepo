"""S2: finite-state occupation-measure LP from Champati et al., Appendix B.

Matrices here use row-stochastic convention. Costs are per sampling decision,
not time averages. No accuracy/battery-optimality claim is made on parking data.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import linprog

def age_cost(stay:float, action:int)->float:
    if action<1 or not 0<=stay<=1:
        raise ValueError('invalid self-transition probability or action')
    # Eq. (4), evaluated by a stable geometric sum, including p=0 and p=1.
    return float(action-sum(stay**n for n in range(action)))

def solve_occupation_lp(matrix,actions,*,mean_interval_min=None,age_limit=None):
    p=np.asarray(matrix,dtype=float);a=np.asarray(actions,dtype=int)
    if p.shape[0]!=p.shape[1] or np.any(p<0) or not np.allclose(p.sum(axis=1),1):
        raise ValueError('row-stochastic transition matrix required')
    if np.any(a<1) or len(np.unique(a))!=len(a):
        raise ValueError('distinct positive integer actions required')
    n=p.shape[0];k=len(a)
    transitions=np.stack([np.linalg.matrix_power(p,int(d)) for d in a],axis=1)
    costs=np.array([[age_cost(p[s,s],int(d)) for d in a] for s in range(n)])
    periods=np.tile(a,n).astype(float)
    flow=np.zeros((n,n*k))
    for target in range(n):
        for state in range(n):
            flow[target,state*k:(state+1)*k]=(float(state==target)-transitions[state,:,target])
    eq=np.vstack([np.ones(n*k),flow[:-1]])
    rhs=np.r_[1.,np.zeros(n-1)]
    if (mean_interval_min is None)==(age_limit is None):
        raise ValueError('Specify exactly one constraint: P1 or P2')
    if mean_interval_min is not None:
        objective=costs.ravel();ub=-periods[None,:];limit=np.array([-mean_interval_min])
    else:
        objective=-periods;ub=costs.reshape(1,-1);limit=np.array([age_limit])
    result=linprog(objective,A_ub=ub,b_ub=limit,A_eq=eq,b_eq=rhs,bounds=(0,None),method='highs')
    if not result.success:
        raise ValueError(f'Occupation-measure LP failed: {result.message}')
    z=np.maximum(result.x.reshape(n,k),0)
    conditional=np.zeros_like(z)
    for state in range(n):
        if z[state].sum()>1e-12:
            conditional[state]=z[state]/z[state].sum()
        else:
            conditional[state,0]=1.
    mean_interval=float(np.dot(z.sum(axis=0),a))
    expected_age=float(np.sum(z*costs))
    return {'actions':a.tolist(),'probabilities':conditional.tolist(),'occupation':z.tolist(),
      'mean_interval':mean_interval,'sampling_frequency':1/mean_interval,'average_age_per_decision':expected_age,
      'max_flow_residual':float(np.max(np.abs(flow@z.ravel()))),
      'normalization_residual':float(abs(z.sum()-1)),
      'constraint_kind':'P1' if mean_interval_min is not None else 'P2'}

def verify_published_examples():
    ex1=solve_occupation_lp([[.9,.1],[.6,.4]],np.arange(1,41),mean_interval_min=1/(2*.1*.6/(.1+.6)))
    ex2=solve_occupation_lp([[.95,.05],[.95,.05]],np.arange(1,101),age_limit=1.)
    # The text gives rounded numbers. Validate Example 1 and the rounded frequency
    # in Example 2; do not force printed action weights into a valid solution.
    p=np.array(ex1['probabilities'])
    checks={
      'example1_age_matches_1_416':abs(ex1['average_age_per_decision']-1.416)<.002,
      'example1_state0_6_7_only':np.allclose(p[0].sum(),p[0,5]+p[0,6]),
      'example1_state1_2':p[1,1]>.999999,
      'example1_p7_matches_0_535':abs(p[0,6]-.535)<.002,
      'example2_frequency_rounds_to_0_14':round(ex2['sampling_frequency'],2)==.14,
      'example2_age_constraint':ex2['average_age_per_decision']<=1+1e-8,
    }
    checks={key:bool(value) for key,value in checks.items()}
    printed2=np.zeros((2,100));printed2[0,6]=.64;printed2[0,7]=.36;printed2[1,1]=1
    # In Example 2 P has identical rows, so the induced invariant distribution is
    # exactly (.95,.05) regardless of sampled intervals >=1.
    printed_cost=.95*(.64*age_cost(.95,7)+.36*age_cost(.95,8))+.05*age_cost(.05,2)
    return {'all_required_checks_passed':all(checks.values()),'checks':checks,'example1':ex1,'example2':ex2,
      'example2_printed_probabilities_age_recomputed':printed_cost,
      'example2_printed_probabilities_satisfy_d1':printed_cost<=1+1e-8,
      'note':'LP follows Appendix B and Eq. (4). Example 2 printed weights do not satisfy d=1 under those equations; retained as an explicit source inconsistency, not fitted away.'}
