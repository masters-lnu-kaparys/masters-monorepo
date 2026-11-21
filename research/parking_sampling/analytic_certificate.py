"""Offline path certificates using guaranteed resets of the observed free run.

The supplied reference intervals never enter the runtime scheduler. Integer-grid
enumeration is an independent small-example check, not the linear certificate.
"""
from functools import lru_cache
from bisect import bisect_right
import numpy as np
from numba import njit
from episode_certificate import _validated_trace


def validate(ends,states,start,tau,G,A):
    ends,states=_validated_trace(ends,states,start,tau,max(0,G-tau))
    if any(type(v) not in (int,np.int64,np.int32) for v in (start,tau,G,A)) or not 0<tau<=G or A<0:
        raise ValueError('Integer parameters with0<tau<=G and A>=0 required')
    return ends,states


@njit(cache=True)
def reset_counts_window(ends,states,start,tau,G,A):
    """[eligible, adjacent, old_history, end_history, recursive_history]."""
    first=int(np.searchsorted(ends,start,side='right'))
    old=start;end_anchor=start;recursive=start
    values=np.zeros(5,np.int64)
    for i in range(first,len(ends)):
        c=start if i==first else ends[i-1];d=ends[i]
        if states[i]==1:
            if d-c>=G:
                old=max(old,d-tau);end_anchor=max(end_anchor,d)
            # Initial sample sees the current occupied interval, even if short.
            if i==first:end_anchor=max(end_anchor,d)
            if i==first or d-c>=G or (d-c>=tau and c-recursive<=A):
                recursive=max(recursive,d)
        elif i>first and i<len(ends)-1 and d-c>=tau:
            values[0]+=1
            if i==first+1:continue
            p=ends[i-2]
            if d-p<G:
                values[1]+=1
                values[2]+=int(p-old>A)
                values[3]+=int(p-end_anchor>A)
                values[4]+=int(p-recursive>A)
    return values


def reset_certificate(ends,states,start,tau,G,A):
    ends,states=validate(ends,states,start,tau,G,A)
    raw=reset_counts_window(ends,states,start,tau,G,A)
    names=('eligible','adjacent_pair','legacy_history','end_reset','recursive_reset')
    return {name:int(v) for name,v in zip(names,raw)}


@njit(cache=True)
def reset_counts_bundle(ends,states,offsets,starts,bay_indexes,n_bays,tau,G,A):
    by=np.zeros((n_bays,5),np.int64)
    for w in range(len(starts)):
        lo,hi=offsets[w:w+2]
        by[bay_indexes[w]]+=reset_counts_window(ends[lo:hi],states[lo:hi],starts[w],tau,G,A)
    return by


def exact_maximum_misses(ends,states,start,tau,G,A,horizon_limit=128):
    """Exhaust every integer pause of the specified controller class on a trace.

    Each branch may pick a different legal causal policy. State is the current
    clock, previous paid state and observed-run start. Unsampled future is used
    only for offline reward accounting. No randomness or fitted parameters.
    """
    ends,states=validate(ends,states,start,tau,G,A)
    if ends[-1]-start>horizon_limit:raise ValueError('Exact enumeration is limited to small examples')
    edges=list(map(int,ends));source=list(map(int,states))
    first=bisect_right(edges,start);end=edges[-1]
    targets=[(edges[i-1],edges[i]) for i in range(first+1,len(edges)-1)
             if source[i]==0 and edges[i]-edges[i-1]>=tau]
    transitions=0
    @lru_cache(None)
    def best(t,previous,run):
        nonlocal transitions
        if t>=end:return 0,0
        state=source[bisect_right(edges,t)]
        current_run=t if previous!=state else run
        cap=tau if state==1 or t-current_run<A else G
        highest=-1;action=1
        for pause in range(1,cap+1):
            transitions+=1;u=t+pause
            reward=sum(a>t and b<=u for a,b in targets)
            score=reward+(best(u,state,current_run)[0] if u<end else 0)
            if score>highest:highest=score;action=pause
        return highest,action
    maximum=best(start,-1,start)[0]
    witness=[];t=start;previous=-1;run=start
    while t<end:
        state=source[bisect_right(edges,t)];current_run=t if previous!=state else run
        pause=best(t,previous,run)[1]
        witness.append([int(t),int(state),int(current_run),int(pause)])
        previous=state;run=current_run;t+=pause
    return {'maximum_missed':int(maximum),'eligible':len(targets),'witness':witness,
            'reachable_states':best.cache_info().currsize,'transitions_examined':transitions}


def count_witness_misses(ends,states,start,tau,witness):
    """Separate episode-centric accounting, independent of the DAG gap reward."""
    times=[r[0] for r in witness];first=bisect_right(list(ends),start);count=0
    for i in range(first+1,len(ends)-1):
        if states[i]!=0 or ends[i]-ends[i-1]<tau:continue
        if not any(ends[i-1]<=t<ends[i] for t in times):count+=1
    return count
