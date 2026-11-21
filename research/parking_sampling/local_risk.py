"""Empirical wrong-display integrals with pooled and bay/context shrinkage.

Only the offline training labels query future training intervals. Runtime tables
receive sampled state, clock and the start of the observed equal-state run.
"""
import numpy as np
from numba import njit
from simulation import AGES,BASE_ACTIONS
from kernels import simulate_window

ACTIONS=np.array([15,30,45,60,72,75,90,120,180,240,300],np.int64)
ARMS=('pooled_state','pooled_clock_age','bay_state_alpha50','bay_full_alpha0','bay_full_alpha50','bay_full_alpha500')


@njit(cache=True)
def collect_window(ends,states,start,cadence,anchor_period=900):
    n=np.zeros(48,np.int64);cost=np.zeros((48,len(ACTIONS)))
    occupied=np.zeros(len(ends)+1);a=start
    for i in range(len(ends)):
        occupied[i+1]=occupied[i]+(ends[i]-a)*states[i];a=ends[i]
    sample=start;held=-1;run=start;i=0
    while sample+300<ends[-1]:
        while ends[i]<=sample:i+=1
        s=states[i]
        if s!=held:run=sample
        held=s;bound=min(ends[i],ends[-1]-300)
        count=max(1,(bound-sample+cadence-1)//cadence)
        first_anchor=sample+((-((sample-start)//cadence))%(anchor_period//cadence))*cadence
        for t in range(first_anchor,min(sample+count*cadence,ends[-1]-300),anchor_period):
            tb=int(t%86400//21600);ab=0
            while ab<5 and t-run>=AGES[ab]:ab+=1
            ctx=(int(s)*4+tb)*6+ab;n[ctx]+=1
            if t+300<=ends[i]:continue
            j0=np.searchsorted(ends,t,side='right');a0=start if j0==0 else ends[j0-1]
            integral0=occupied[j0]+(t-a0)*states[j0]
            for k in range(len(ACTIONS)):
                d=ACTIONS[k];j1=np.searchsorted(ends,t+d,side='right');a1=start if j1==0 else ends[j1-1]
                occ=occupied[j1]+(t+d-a1)*states[j1]-integral0
                cost[ctx,k]+=occ if s==0 else d-occ
        sample+=count*cadence
    return n,cost


@njit(cache=True)
def collect_bundle(ends,states,offsets,starts,bay_indexes,n_bays):
    n=np.zeros((n_bays,48),np.int64);cost=np.zeros((n_bays,48,len(ACTIONS)))
    for w in range(len(starts)):
        lo,hi=offsets[w:w+2];bay=bay_indexes[w]
        for cadence in (30,60,300):
            nn,cc=collect_window(ends[lo:hi],states[lo:hi],starts[w],cadence)
            n[bay]+=nn;cost[bay]+=cc
    return n,cost


def estimates(n,cost,arm):
    n=np.asarray(n,dtype=float);cost=np.asarray(cost,dtype=float)
    if arm not in ARMS or n.ndim!=2 or n.shape[1]!=48 or cost.shape!=(*n.shape,len(ACTIONS)):
        raise ValueError('Invalid model dimensions or arm')
    if np.any(n<0) or np.any(cost<0) or not np.all(np.isfinite(cost)):
        raise ValueError('Nonnegative finite statistics required')
    gn=n.sum(axis=0);gc=cost.sum(axis=0);state_prior=np.zeros((2,len(ACTIONS)))
    pooled=np.empty((48,len(ACTIONS)))
    for s in range(2):
        ids=slice(24*s,24*(s+1));nn=gn[ids].sum()
        if nn<=0:raise ValueError('Training must support both states')
        state_prior[s]=gc[ids].sum(axis=0)/nn
        pooled[ids]=(gc[ids]+50*state_prior[s])/(gn[ids,None]+50)
    if arm=='pooled_state':
        table=np.repeat(state_prior,24,axis=0)
        return np.broadcast_to(table,cost.shape).copy(),table
    if arm=='pooled_clock_age':return np.broadcast_to(pooled,cost.shape).copy(),pooled
    alpha=0 if arm.endswith('alpha0') else 500 if arm.endswith('alpha500') else 50
    result=np.empty_like(cost)
    for s in range(2):
        ids=slice(24*s,24*(s+1));sn=n[:,ids].sum(axis=1)
        # State-level prior always regularized, including the alpha0 ablation.
        bs=(cost[:,ids].sum(axis=1)+max(alpha,50)*state_prior[s])/(sn[:,None]+max(alpha,50))
        if arm.startswith('bay_state'):
            result[:,ids]=bs[:,None,:]
        else:
            prior=(pooled[None,ids,:]+bs[:,None,:])/2
            if alpha:
                result[:,ids]=(cost[:,ids]+alpha*prior)/(n[:,ids,None]+alpha)
            else:
                result[:,ids]=np.divide(cost[:,ids],n[:,ids,None],out=prior.copy(),where=n[:,ids,None]>0)
    if not np.all(result>=0) or np.any(result>ACTIONS[None,None,:]+1e-8):raise ArithmeticError('Cost outside interval')
    return result,pooled


def make_tables(expected,lambda_F,lambda_O):
    risk=np.asarray(expected,dtype=float)
    if risk.shape[-2:]!=(48,len(ACTIONS)) or lambda_F<=0 or lambda_O<=0:raise ValueError('Invalid expected costs/penalties')
    penalties=np.r_[np.full(24,lambda_F),np.full(24,lambda_O)]
    score=(1+penalties[None,:,None]*risk)/ACTIONS
    return ACTIONS[np.argmin(score,axis=-1)].astype(np.int64)


def align_tables(training_bays,tables,target_bays,pooled_table):
    index={int(b):i for i,b in enumerate(training_bays)}
    result=np.empty((len(target_bays),48),np.int64);fallback=[]
    for i,b in enumerate(target_bays):
        if int(b) in index:result[i]=tables[index[int(b)]]
        else:result[i]=pooled_table;fallback.append(int(b))
    return result,fallback


@njit(cache=True)
def evaluate_local(ends,states,offsets,starts,bay_indexes,initial,seeds,tables,n_bays):
    by=np.zeros((n_bays,initial.shape[1],17),np.int64);hist=np.zeros(301,np.int64)
    cdf=np.zeros((2,len(BASE_ACTIONS)));delays=np.array([60,60],np.int64);fallback=np.zeros(48,np.int64)
    for w in range(len(starts)):
        lo,hi=offsets[w:w+2];bay=bay_indexes[w]
        for rep in range(initial.shape[1]):
            values,h=simulate_window(ends[lo:hi],states[lo:hi],starts[w]+initial[w,rep],1,delays,tables[bay],
              fallback,True,True,cdf,BASE_ACTIONS,seeds[w,rep])
            by[bay,rep]+=values;hist+=h
    return by,hist
