"""Compiled evaluation. Hidden interval bounds accelerate replay, never decisions.

Policy inputs are only sampled state, local clock, observed run, and fixed random
seed. Equivalence to the independent reference simulator is tested explicitly.
"""
import numpy as np
from numba import njit
from simulation import AGES,THRESHOLDS,N_STATS

@njit(cache=True)
def rng_next(value):
    value^=value>>np.uint64(12);value^=value<<np.uint64(25);value^=value>>np.uint64(27)
    product=value*np.uint64(2685821657736338717)
    return value,float(product>>np.uint64(11))*(1./9007199254740992.)

@njit(cache=True)
def simulate_window(ends,states,start,kind,delays,lookup,fallback,use_time,use_run,cdf,random_actions,seed):
    totals=np.zeros(N_STATS,np.int64);hist=np.zeros(301,np.int64)
    first=np.searchsorted(ends,start,side='right');sample=start;held=-1;run=start
    totals[0]=ends[-1]-start;random_state=np.uint64(seed)
    for i in range(first,len(ends)):
        a=start if i==first else ends[i-1];b=ends[i];state=states[i]
        wrong=max(0,min(sample,b)-a)
        if held!=state:totals[2 if state==1 else 3]+=wrong
        seen=False;delay=0
        while sample<b:
            if not seen:delay=sample-a
            seen=True
            if state!=held:run=sample
            held=state;bound=b;is_fallback=0
            if kind==0:
                pause=delays[state]
            elif kind==1:
                tb=int(sample%86400//21600) if use_time else 0
                ab=0
                if use_run:
                    while ab<5 and sample-run>=AGES[ab]:ab+=1
                ctx=(int(state)*4+tb)*6+ab
                pause=lookup[ctx];is_fallback=fallback[ctx]
                if use_time:bound=min(bound,(sample//21600+1)*21600)
                if use_run and ab<5:bound=min(bound,run+AGES[ab])
            else:
                # Randomized occupation-measure policy draws at each measurement.
                random_state,u=rng_next(random_state);j=0
                while j<len(random_actions)-1 and u>=cdf[state,j]:j+=1
                pause=random_actions[j]
                bound=min(bound,sample+pause)
            count=max(1,(bound-sample+pause-1)//pause)
            totals[1]+=count;totals[4]+=count*is_fallback;sample+=count*pause
        if state==0 and i>first and i<len(ends)-1:
            if seen:
                totals[5]+=1;totals[6]+=delay;hist[delay]+=1
            duration=b-a
            for k in range(5):
                if duration>=THRESHOLDS[k]:
                    totals[7+k]+=1;totals[12+k]+=int(not seen)
    return totals,hist

@njit(cache=True)
def evaluate_bundle(ends,states,offsets,starts,bay_indexes,initial_offsets,seeds,kind,delays,lookup,fallback,use_time,use_run,cdfs,random_actions,n_bays):
    reps=initial_offsets.shape[1]
    by_bay_phase=np.zeros((n_bays,reps,N_STATS),np.int64);hist=np.zeros(301,np.int64)
    for w in range(len(starts)):
        lo=offsets[w];hi=offsets[w+1];bay=bay_indexes[w]
        for rep in range(reps):
            t=starts[w]+initial_offsets[w,rep]
            values,h=simulate_window(ends[lo:hi],states[lo:hi],t,kind,delays,lookup,fallback,use_time,use_run,cdfs[bay],random_actions,seeds[w,rep])
            by_bay_phase[bay,rep]+=values;hist+=h
    return by_bay_phase,hist

@njit(cache=True)
def grid_transition_counts(ends,states,start,step=5):
    counts=np.zeros((2,2),np.int64);sample=start;held=-1
    for i in range(len(ends)):
        b=ends[i];state=states[i]
        if sample>=b:continue
        n=(b-sample+step-1)//step
        if held>=0:counts[held,state]+=1
        counts[state,state]+=n-1
        held=state;sample+=n*step
    return counts

@njit(cache=True)
def risk_training_window(ends,states,start,cadence,anchor_period,use_time,use_run):
    # Reconstruct complete teacher observation history. Labels may inspect future
    # training data only, and never extend beyond the training window.
    n=np.zeros((48,6),np.int64);f=np.zeros((48,6));o=np.zeros((48,6));m=np.zeros((48,6,5))
    occupied=np.zeros(len(ends)+1)
    a=start
    for i in range(len(ends)):
        occupied[i+1]=occupied[i]+(ends[i]-a)*states[i];a=ends[i]
    free=np.empty(len(ends),np.int64);free_end=np.empty(len(ends),np.int64);nf=0
    for i in range(len(ends)):
        if states[i]==0:
            free[nf]=start if i==0 else ends[i-1];free_end[nf]=ends[i];nf+=1
    sample=start;held=-1;run=start;i=0
    actions=np.array([5,15,30,60,120,300],np.int64)
    # Step across observation runs using source intervals, exactly as the fast
    # simulator. Anchor period is a multiple of each teacher cadence.
    while sample+300<ends[-1]:
        while ends[i]<=sample:i+=1
        s=states[i]
        if s!=held:run=sample
        held=s
        bound=min(ends[i],ends[-1]-300)
        count=max(1,(bound-sample+cadence-1)//cadence)
        first_anchor=sample+((-((sample-start)//cadence))%(anchor_period//cadence))*cadence
        for t in range(first_anchor,min(sample+count*cadence,ends[-1]-300),anchor_period):
            tb=int(t%86400//21600) if use_time else 0
            ab=0
            if use_run:
                while ab<5 and t-run>=AGES[ab]:ab+=1
            ctx=(int(s)*4+tb)*6+ab
            for k in range(6):n[ctx,k]+=1
            # All labels are zero if the complete target horizon stays inside
            # this recorded state. This changes no teacher observations.
            if t+300<=ends[i]:continue
            j0=np.searchsorted(ends,t,side='right');a0=start if j0==0 else ends[j0-1]
            integral0=occupied[j0]+(t-a0)*states[j0]
            for k in range(6):
                d=actions[k];j1=np.searchsorted(ends,t+d,side='right');a1=start if j1==0 else ends[j1-1]
                integral1=occupied[j1]+(t+d-a1)*states[j1]
                occ=integral1-integral0
                if s==0:f[ctx,k]+=occ/d
                else:o[ctx,k]+=(d-occ)/d
                left=np.searchsorted(free[:nf],t,side='right')
                right=np.searchsorted(free_end[:nf],t+d,side='right')
                for z in range(left,right):
                    duration=free_end[z]-free[z]
                    for q in range(5):
                        if duration>=THRESHOLDS[q]:m[ctx,k,q]+=1
        sample+=count*cadence
    return n,f,o,m
