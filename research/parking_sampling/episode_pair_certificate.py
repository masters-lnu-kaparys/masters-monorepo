"""Sharper deterministic certificate using two consecutive recorded durations."""
import numpy as np
from numba import njit
from episode_certificate import _validated_trace

@njit(cache=True)
def count_pair_bound_window(ends,states,start,tau,free_cap):
    first=int(np.searchsorted(ends,start,side='right'));count=0;eligible=0
    for i in range(first+1,len(ends)-1):
        if states[i]!=0:continue
        a=ends[i-1];b=ends[i];duration=b-a
        if duration<tau:continue
        eligible+=1
        # If the preceding occupied run is the first observed run, no earlier
        # free sample exists in the replay window; an occupied pause <=tau
        # must observe this eligible free episode. It contributes no risk.
        if i==first+1:continue
        preceding_occupied=a-ends[i-2]
        count+=int(preceding_occupied+duration<free_cap)
    return eligible,count

def pair_bound(ends,states,start,tau,free_cap):
    ends,states=_validated_trace(ends,states,start,tau,max(0,free_cap-tau))
    if free_cap<=0:raise ValueError('Positive free-state cap required')
    eligible,bound=count_pair_bound_window(ends,states,start,tau,free_cap)
    return {'eligible_free_episodes':int(eligible),'risky_adjacent_pairs':int(bound)}

@njit(cache=True)
def count_pair_bound_bundle(ends,states,offsets,starts,initial,bay_indexes,bay_count,tau,free_cap):
    result=np.zeros((bay_count,initial.shape[1],2),np.int64)
    for w in range(len(starts)):
        a=offsets[w];b=offsets[w+1]
        for rep in range(initial.shape[1]):
            eligible,bound=count_pair_bound_window(ends[a:b],states[a:b],starts[w]+initial[w,rep],tau,free_cap)
            result[bay_indexes[w],rep,0]+=eligible;result[bay_indexes[w],rep,1]+=bound
    return result

def calibrated_free_cap(pair_sums,grid,budget):
    """Largest training-only cap with a chosen empirical pair-risk fraction.

    This is an empirical trace certificate, not a confidence bound for unseen
    histories. `pair_sums` must include every eligible free episode's preceding
    occupied duration plus its own duration, rather than only short pairs.
    """
    values=np.asarray(pair_sums,dtype=np.int64);grid=np.asarray(grid,dtype=np.int64)
    if values.ndim!=1 or not len(values) or np.any(values<=0) or grid.ndim!=1 or not len(grid) or np.any(grid<=0) or not 0<=budget<=1:
        raise ValueError('Positive durations, nonempty grid and budget in [0,1] required')
    choices=[int(g) for g in grid if np.mean(values<g)<=budget]
    if not choices:raise ValueError('No cap meets the empirical risk budget')
    return max(choices)
