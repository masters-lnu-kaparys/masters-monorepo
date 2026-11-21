"""Attribute old C2 errors to the sampled context that scheduled each gap."""
import numpy as np
from numba import njit
from data_access import load_bundle,tuning_bays
from simulation import AGES,BASE_ACTIONS
from prepare_data import ROOT
from run_phase3 import write_json

@njit(cache=True)
def attribute_window(ends,states,start,table):
    errors=np.zeros((48,2),np.int64);misses=np.zeros((48,13),np.int64)
    first=np.searchsorted(ends,start,side='right');sample=start;held=-1;run=start;lastctx=0;lastpause=60
    for i in range(first,len(ends)):
        a=start if i==first else ends[i-1];b=ends[i];state=states[i]
        wrong=max(0,min(sample,b)-a)
        if held!=state:errors[lastctx,0 if state==1 else 1]+=wrong
        seen=False
        while sample<b:
            seen=True
            if state!=held:run=sample
            held=state;tb=int(sample%86400//21600);ab=np.searchsorted(AGES,sample-run,side='right')
            ctx=(int(state)*4+tb)*6+ab;pause=table[ctx]
            bound=min(b,(sample//21600+1)*21600)
            if ab<5:bound=min(bound,run+AGES[ab])
            count=max(1,(bound-sample+pause-1)//pause)
            lastctx=ctx;lastpause=pause;sample+=count*pause
        if state==0 and i>first and i<len(ends)-1 and b-a>=60 and not seen:
            for j in range(13):
                if BASE_ACTIONS[j]==lastpause:misses[lastctx,j]+=1
    return errors,misses

def main():
    data=load_bundle(('validation_development',),bay_filter=tuning_bays());initial,_=data.phases(10)
    old=ROOT/'.codex-work/parking-research-phase3-20261018'
    table=np.load(old/'frozen-policies/C2_0.006_0.024_0.0001.npz')['lookup']
    errors=np.zeros((48,2),np.int64);misses=np.zeros((48,13),np.int64)
    for w,start in enumerate(data.starts):
        lo=data.offsets[w];hi=data.offsets[w+1]
        for rep in range(10):
            e,m=attribute_window(data.ends[lo:hi],data.states[lo:hi],start+initial[w,rep],table)
            errors+=e;misses+=m
    result={'policy':'C2_0.006_0.024_0.0001','scope':'original_128_development_bays',
      'false_free_seconds':int(errors[:,0].sum()),'false_occupied_seconds':int(errors[:,1].sum()),
      'M60_by_last_sample_state':{'free':int(misses[:24].sum()),'occupied':int(misses[24:].sum())},
      'M60_by_gap_seconds':{str(d):int(misses[:,j].sum()) for j,d in enumerate(BASE_ACTIONS)},
      'M60_by_context_and_action':misses.tolist(),'error_seconds_by_context':errors.tolist(),
      'explanation':'Recorded source state is used only by offline error accounting, never by the controller.'}
    write_json(ROOT/'.codex-work/parking-research-refinement-20261018/old-C2-diagnostic.json',result)
    print({k:v for k,v in result.items() if k not in ('M60_by_context_and_action','error_seconds_by_context')})

if __name__=='__main__':main()
