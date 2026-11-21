"""History-conditioned path bound; no reference-state inputs enter the policy."""
import numpy as np
from numba import njit
from episode_certificate import _validated_trace

@njit(cache=True)
def history_bound_window(ends,states,start,tau,free_cap,age_threshold):
    first=int(np.searchsorted(ends,start,side='right'));anchor=start
    eligible=0;generic=0;conditioned=0
    for i in range(first,len(ends)):
        a=start if i==first else ends[i-1];b=ends[i]
        if states[i]==1:
            if b-a>=free_cap:anchor=max(anchor,b-tau)
            continue
        if i<=first or i>=len(ends)-1 or b-a<tau:continue
        eligible+=1
        if i==first+1:continue
        p=ends[i-2]
        if b-p<free_cap:
            generic+=1
            if p-anchor>age_threshold:conditioned+=1
    return eligible,generic,conditioned

def history_bound(ends,states,start,tau=60,free_cap=75,age_threshold=900):
    ends,states=_validated_trace(ends,states,start,tau,max(0,free_cap-tau))
    if free_cap<tau or age_threshold<0:raise ValueError('Require free_cap>=tau and nonnegative age threshold')
    eligible,generic,conditioned=history_bound_window(ends,states,start,tau,free_cap,age_threshold)
    return {'eligible':int(eligible),'generic_pair_bound':int(generic),'history_conditioned_bound':int(conditioned)}

@njit(cache=True)
def history_bound_bundle(ends,states,offsets,starts,initial,bay_indexes,bay_count,tau,free_cap,age_threshold):
    result=np.zeros((bay_count,initial.shape[1],3),np.int64)
    for w in range(len(starts)):
        a,b=offsets[w:w+2]
        for rep in range(initial.shape[1]):
            values=history_bound_window(ends[a:b],states[a:b],starts[w]+initial[w,rep],tau,free_cap,age_threshold)
            for j in range(3):result[bay_indexes[w],rep,j]+=values[j]
    return result
