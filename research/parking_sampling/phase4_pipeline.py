"""Frozen estimator, schedule assignment and holdout simulation."""
import hashlib

import numpy as np
from numba import njit

from frozen_local_priors import apply_frozen_priors
from kernels import simulate_window
from prepare_data import DOCS
from simulation import BASE_ACTIONS

CATALOG = DOCS / 'phase4-display-policies.json'
COHORT = DOCS / 'phase4-display-cohort.json'


def frozen_arm(n,cost,state,context,arm):
    """Original arm formula, with source-wide priors held fixed for new Bays."""
    n=np.asarray(n,dtype=float);cost=np.asarray(cost,dtype=float)
    if arm=='pooled_state':return np.broadcast_to(np.repeat(state,24,axis=0),cost.shape).copy()
    if arm=='pooled_clock_age':return np.broadcast_to(context,cost.shape).copy()
    if arm=='bay_full_alpha500':return apply_frozen_priors(n,cost,state,context,500)
    if arm not in ('bay_state_alpha50','bay_full_alpha0'):raise ValueError('Unfrozen arm')
    out=np.empty_like(cost)
    for s in range(2):
        ids=slice(s*24,(s+1)*24);sn=n[:,ids].sum(axis=1)
        bs=(cost[:,ids].sum(axis=1)+50*state[s])/(sn[:,None]+50)
        if arm=='bay_state_alpha50':out[:,ids]=bs[:,None,:]
        else:
            prior=(context[None,ids]+bs[:,None,:])/2
            out[:,ids]=np.divide(cost[:,ids],n[:,ids,None],out=prior.copy(),where=n[:,ids,None]>0)
    return out


def select_component(bay,weights,seed=20261025):
    names=sorted(weights);cdf=np.cumsum([weights[n] for n in names]);cdf[-1]=1.
    u=int.from_bytes(hashlib.sha256(f'local-risk-allocation:{seed}:{int(bay)}'.encode()).digest()[:8],'little')/2**64
    return names[min(int(np.searchsorted(cdf,u,side='right')),len(names)-1)]


def aggregate_components(values,histograms,bays,names,weights,seed=20261025):
    if set(weights)-set(names) or min(weights.values())<0 or abs(sum(weights.values())-1)>1e-9:
        raise ValueError('Invalid frozen policy mixture')
    ix={n:i for i,n in enumerate(names)}
    expected=sum(w*values[ix[n]] for n,w in weights.items());expected[:,0]=values[0,:,0]
    expected_hist=sum(w*histograms[ix[n]] for n,w in weights.items())
    choices=[select_component(b,weights,seed) for b in bays]
    realized=np.stack([values[ix[n],i] for i,n in enumerate(choices)])
    hist=np.stack([histograms[ix[n],i] for i,n in enumerate(choices)])
    return expected,expected_hist,realized,hist,choices


@njit(cache=True)
def evaluate_component(ends,states,offsets,starts,bay_indexes,initial,seeds,tables,cdfs,kind,n_bays):
    by=np.zeros((n_bays,initial.shape[1],17),np.int64);hist=np.zeros((n_bays,301),np.int64)
    delays=np.array([60,60],np.int64);fallback=np.zeros(48,np.int64)
    for w in range(len(starts)):
        lo,hi=offsets[w:w+2];b=bay_indexes[w]
        for rep in range(initial.shape[1]):
            raw,h=simulate_window(ends[lo:hi],states[lo:hi],starts[w]+initial[w,rep],kind,delays,tables[b],
                fallback,True,True,cdfs[b],BASE_ACTIONS,seeds[w,rep])
            by[b,rep]+=raw;hist[b]+=h
    return by,hist
