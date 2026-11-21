"""Offline certificates for completely missed free episodes under causal gap caps.

No reference-state information is exposed to the runtime scheduler. These
functions validate a complete recorded trace after replay.
"""
from __future__ import annotations
import numpy as np
from numba import njit
from simulation import reference_simulate,THRESHOLDS

def _validated_trace(ends,states,start,tau,extension):
    ends=np.asarray(ends);states=np.asarray(states)
    if (ends.ndim!=1 or states.ndim!=1 or len(ends)!=len(states) or not len(ends)
        or np.any(ends!=ends.astype(np.int64)) or np.any(np.diff(ends)<=0)
        or np.any((states!=0)&(states!=1)) or np.any(states[1:]==states[:-1])
        or int(start)!=start or start>=ends[-1] or tau<=0 or extension<0):
        raise ValueError('Invalid merged binary trace or bounds')
    return ends.astype(np.int64),states.astype(np.int8)

@njit(cache=True)
def count_bound_window(ends,states,start,tau,extension):
    first=int(np.searchsorted(ends,start,side='right'));count=0;eligible=0
    for i in range(first+1,len(ends)-1):
        if states[i]!=0:continue
        a=ends[i-1];b=ends[i]
        if b-a<tau:continue
        p=ends[i-2] if i>=2 else start
        eligible+=1;count+=int(a-p<extension)
    return eligible,count

def short_cycle_bound(ends,states,start,tau,extension):
    """Count eligible free episodes whose immediately preceding occupied run < L.

    If occupied-state pauses <= tau and free-state pauses <= tau+L, every missed
    free episode of duration >=tau has a unique preceding occupied run <L.
    The bound is deterministic on the supplied trace; it predicts no unknown
    lower bound on future real vehicle dwell times.
    """
    ends,states=_validated_trace(ends,states,start,tau,extension)
    eligible,count=count_bound_window(ends,states,start,tau,extension)
    return {'eligible_free_episodes':int(eligible),'short_preceding_occupied_episodes':int(count)}

def verify_policy_certificate(ends,states,start,choose,tau,extension):
    ends,states=_validated_trace(ends,states,start,tau,extension)
    raw,hist,decisions=reference_simulate(ends,states,start,choose)
    if any(d>(tau if state==1 else tau+extension) for t,state,run,d,fb in decisions):
        raise ValueError('Policy violates the state-conditioned gap envelope')
    if tau not in THRESHOLDS:raise ValueError('Use a recorded threshold')
    slot=int(np.flatnonzero(THRESHOLDS==tau)[0]);bound=short_cycle_bound(ends,states,start,tau,extension)
    missed=int(raw[12+slot])
    return {**bound,'missed':missed,'bound_holds':missed<=bound['short_preceding_occupied_episodes']}

@njit(cache=True)
def count_bound_bundle(ends,states,offsets,starts,initial,bay_indexes,bay_count,tau,extension):
    """By-bay/phase [eligible, bound]; shares censoring with reference_simulate."""
    result=np.zeros((bay_count,initial.shape[1],2),np.int64)
    for w in range(len(starts)):
        a=offsets[w];b=offsets[w+1]
        for rep in range(initial.shape[1]):
            eligible,bound=count_bound_window(ends[a:b],states[a:b],starts[w]+initial[w,rep],tau,extension)
            result[bay_indexes[w],rep,0]+=eligible;result[bay_indexes[w],rep,1]+=bound
    return result

def duration_counterexample():
    """Same paid observations, F/O, transition count and total misses; different M60."""
    a_ends=[10,50,60,100,121];b_ends=[10,30,40,100,121];states=[1,0,1,0,1]
    result=[]
    for ends in (a_ends,b_ends):
        raw,h,decisions=reference_simulate(ends,states,0,lambda o:(120,False))
        result.append({'ends':ends,'states':states,'samples':[x[0] for x in decisions],
          'sampled_states':[x[1] for x in decisions],'F_seconds':int(raw[2]),'O_seconds':int(raw[3]),
          'transitions':len(ends)-1,'M0':int(raw[12]),'M60':int(raw[14])})
    return result
