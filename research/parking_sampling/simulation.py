"""Independent event-exact reference simulator with a causal policy interface."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import numpy as np

THRESHOLDS=np.array([0,30,60,120,300],dtype=np.int64)
AGES=np.array([60,300,900,3600,14400],dtype=np.int64)
ACTIONS=np.array([5,15,30,60,120,300],dtype=np.int64)
BASE_ACTIONS=np.array([5,10,15,20,30,45,60,75,90,120,180,240,300],dtype=np.int64)
# raw totals: seconds, calls, F, O, fallback calls, detected vacancies, delay sum,
# vacancy totals at each threshold, missed vacancies at each threshold.
N_STATS=17

@dataclass(frozen=True)
class Observation:
    time:int
    state:int
    observed_run_start:int

def stable_seed(text:str)->int:
    return int.from_bytes(hashlib.sha256(text.encode()).digest()[:8],'little') or 1

def phase_offset(bay:int,window_id:str,rep:int,seed:int=20261018)->int:
    return stable_seed(f'{seed}:{bay}:{window_id}:{rep}')%3600

def random_step(value:int):
    value^=value>>12;value^=(value<<25)&((1<<64)-1);value^=value>>27
    product=(value*2685821657736338717)&((1<<64)-1)
    return value,(product>>11)*(1/(1<<53))

def context(o:Observation,use_time=True,use_run=True):
    tb=(o.time%86400)//21600 if use_time else 0
    ab=int(np.searchsorted(AGES,o.time-o.observed_run_start,side='right')) if use_run else 0
    return int((o.state*4+tb)*6+ab)

def reference_simulate(ends,states,start,choose,*,max_pause=300):
    """`choose` receives only Observation; returns (pause, fallback flag)."""
    ends=np.asarray(ends,dtype=np.int64);states=np.asarray(states,dtype=np.int8)
    if len(ends)!=len(states) or not len(ends) or np.any(np.diff(ends)<=0) or start>=ends[-1]:
        raise ValueError('invalid contiguous trace')
    first=int(np.searchsorted(ends,start,side='right'));t=int(start);held=-1;run=t
    samples=[];sample_states=[];fallback=0;decisions=[]
    while t<int(ends[-1]):
        i=int(np.searchsorted(ends,t,side='right'));s=int(states[i])
        if s!=held:run=t
        held=s;observation=Observation(t,s,run)
        pause,is_fallback=choose(observation)
        if int(pause)!=pause or pause<1 or pause>max_pause:raise ValueError('invalid pause')
        samples.append(t);sample_states.append(s);fallback+=int(is_fallback)
        decisions.append((t,s,int(run),int(pause),bool(is_fallback)))
        t+=int(pause)
    totals=np.zeros(N_STATS,dtype=np.int64);hist=np.zeros(301,dtype=np.int64)
    totals[0]=int(ends[-1])-start;totals[1]=len(samples);totals[4]=fallback
    sample_ends=samples[1:]+[int(ends[-1])]
    # Independent integration by intersecting held-estimate and source intervals.
    for a,b,estimate in zip(samples,sample_ends,sample_states):
        i=int(np.searchsorted(ends,a,side='right'));point=a
        while point<b:
            edge=min(b,int(ends[i]));actual=int(states[i])
            if estimate!=actual:totals[2 if actual==1 else 3]+=edge-point
            point=edge;i+=1
    source_starts=np.r_[start,ends[first:-1]]
    for i in range(first+1,len(ends)-1):
        if states[i]!=0:continue
        a=int(ends[i-1]);b=int(ends[i]);duration=b-a
        j=int(np.searchsorted(samples,a,side='left'))
        found=j<len(samples) and samples[j]<b
        if found:
            delay=samples[j]-a;totals[5]+=1;totals[6]+=delay;hist[delay]+=1
        for k,threshold in enumerate(THRESHOLDS):
            if duration>=threshold:
                totals[7+k]+=1;totals[12+k]+=int(not found)
    return totals,hist,decisions

def summarize(totals,hist=None):
    a=np.asarray(totals,dtype=float);days=a[0]/86400
    result={'bay_days':days,'samples':int(a[1]),'samples_per_bay_day':a[1]/days,
      'false_free_seconds_per_bay_day':a[2]/days,'false_occupied_seconds_per_bay_day':a[3]/days,
      'fallback_measurements':int(a[4]),'detected_vacancies':int(a[5]),
      'mean_detected_vacancy_delay_seconds':a[6]/a[5] if a[5] else None,
      'vacancy_duration_profiles':{str(threshold):{'episodes':int(a[7+k]),'missed':int(a[12+k]),
        'missed_fraction':a[12+k]/a[7+k] if a[7+k] else None} for k,threshold in enumerate(THRESHOLDS)}}
    if hist is not None and np.sum(hist):
        cumulative=np.cumsum(hist)
        result['median_detected_vacancy_delay_seconds']=int(np.searchsorted(cumulative,.5*cumulative[-1],side='left'))
        result['p95_detected_vacancy_delay_seconds']=int(np.searchsorted(cumulative,.95*cumulative[-1],side='left'))
    return result
