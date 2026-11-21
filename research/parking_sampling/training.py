"""Train empirical response tables using only permitted training histories."""
from pathlib import Path
import json
import time
import numpy as np
from data_access import load_bundle,DEFAULT_WORK
from kernels import risk_training_window,grid_transition_counts

def smooth_tables(n,f,o,m,use_time=True,use_run=True,pseudo=50):
    n=np.asarray(n);f=np.asarray(f);o=np.asarray(o);m=np.asarray(m)
    counts=np.zeros_like(n);ff=np.zeros_like(f);oo=np.zeros_like(o);mm=np.zeros_like(m)
    for ctx in range(48):
        state=ctx//24;tb=(ctx%24)//6;ab=ctx%6
        ids=[(state*4+t)*6+a for t in range(4) for a in range(6)
             if (not use_time or t==tb) and (not use_run or a==ab)]
        counts[ctx]=n[ids].sum(axis=0);ff[ctx]=f[ids].sum(axis=0);oo[ctx]=o[ids].sum(axis=0);mm[ctx]=m[ids].sum(axis=0)
    for state in range(2):
        ids=slice(state*24,(state+1)*24)
        base_n=n[ids].sum(axis=0)
        if np.any(base_n==0):raise ValueError('Training data do not support both states')
        basef=f[ids].sum(axis=0)/base_n;baseo=o[ids].sum(axis=0)/base_n
        basem=m[ids].sum(axis=0)/base_n[:,None]
        ff[ids]=(ff[ids]+pseudo*basef)/(counts[ids]+pseudo)
        oo[ids]=(oo[ids]+pseudo*baseo)/(counts[ids]+pseudo)
        mm[ids]=(mm[ids]+pseudo*basem)/(counts[ids,:,None]+pseudo)
    return {'n':counts,'pf':ff,'po':oo,'pm':mm,'use_time':use_time,'use_run':use_run}

def fit_models(out:Path,lock:Path,*,work=DEFAULT_WORK,cadences=(30,60,300),anchor_period=900):
    out.mkdir(parents=True,exist_ok=True)
    data=load_bundle(('train_development','quarantine_train_reserved'),work=work,training_lock=lock)
    n=np.zeros((48,6),np.int64);f=np.zeros((48,6));o=np.zeros((48,6));m=np.zeros((48,6,5))
    transition_counts=np.zeros((len(data.bays),2,2),np.int64)
    started=time.monotonic()
    for w,start in enumerate(data.starts):
        lo=data.offsets[w];hi=data.offsets[w+1];ends=data.ends[lo:hi];states=data.states[lo:hi]
        transition_counts[data.bay_indexes[w]]+=grid_transition_counts(ends,states,int(start),5)
        for cadence in cadences:
            nn,ff,oo,mm=risk_training_window(ends,states,int(start),cadence,anchor_period,True,True)
            n+=nn;f+=ff;o+=oo;m+=mm
        if w%2000==0 or w+1==len(data.starts):
            print(f'train windows {w+1}/{len(data.starts)}, anchors={n[:,0].sum()}, elapsed={time.monotonic()-started:.1f}s',flush=True)
    variants={}
    for name,t,a in [('full',True,True),('without_time',False,True),('without_run',True,False)]:
        model=smooth_tables(n,f,o,m,t,a)
        np.savez_compressed(out/f'risk-{name}.npz',**model)
        variants[name]=f'risk-{name}.npz'
    np.savez_compressed(out/'training-sufficient-statistics.npz',n=n,sum_pf=f,sum_po=o,sum_pm=m)
    np.savez_compressed(out/'markov-counts.npz',bays=data.bays,counts=transition_counts)
    meta={'windows':len(data.starts),'bays':len(data.bays),'source_files':data.source_files,
      'cadences_seconds':list(cadences),'anchor_period_seconds':anchor_period,
      'anchors_per_action':int(n[:,0].sum()),'labels_end_inclusive_for_missed_episode':True,
      'training_targets_cross_window_boundary':False,'observed_run_is_oracle_age':False,
      'model_files':variants,'elapsed_seconds':time.monotonic()-started,
      'support_note':'Adjacent teachers and anchors are correlated; support is not a count of independent observations.'}
    (out/'training-metadata.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    return meta
