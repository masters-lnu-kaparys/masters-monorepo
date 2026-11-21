"""Append new TRAINING histories while keeping shared priors and weights frozen."""
import numpy as np
from local_risk import ACTIONS


def shared_priors(n,cost):
    n=np.asarray(n,dtype=float);cost=np.asarray(cost,dtype=float);gn=n.sum(axis=0);gc=cost.sum(axis=0)
    state=np.empty((2,len(ACTIONS)));context=np.empty((48,len(ACTIONS)))
    for s in range(2):
        ids=slice(24*s,24*(s+1));total=gn[ids].sum()
        if total<=0:raise ValueError('Both source states need training support')
        state[s]=gc[ids].sum(axis=0)/total
        context[ids]=(gc[ids]+50*state[s])/(gn[ids,None]+50)
    return state,context


def apply_frozen_priors(n,cost,state,context,alpha=500):
    n=np.asarray(n,dtype=float);cost=np.asarray(cost,dtype=float)
    if n.ndim!=2 or n.shape[1]!=48 or cost.shape!=(*n.shape,len(ACTIONS)) or alpha<=0:
        raise ValueError('Invalid appended training statistics')
    result=np.empty_like(cost)
    for s in range(2):
        ids=slice(24*s,24*(s+1));sn=n[:,ids].sum(axis=1)
        bs=(cost[:,ids].sum(axis=1)+alpha*state[s])/(sn[:,None]+alpha)
        prior=(context[None,ids,:]+bs[:,None,:])/2
        result[:,ids]=(cost[:,ids]+alpha*prior)/(n[:,ids,None]+alpha)
    # Missing an entire history follows the original unseen-bay fallback.
    result[n.sum(axis=1)==0]=context
    return result
