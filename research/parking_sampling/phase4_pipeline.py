"""Locked final experiment. Import/freeze never reads final occupancy states."""
import argparse
import hashlib
import importlib.metadata
from pathlib import Path
import duckdb
import numpy as np
from numba import njit
from prepare_data import ROOT,DOCS,sha256,quote
from run_phase3 import write_json
from assess_analytic_contribution import read
from data_access import Bundle,DEFAULT_WORK,load_bundle
from local_risk import ACTIONS,collect_bundle,make_tables
from frozen_local_priors import apply_frozen_priors
from kernels import simulate_window
from simulation import BASE_ACTIONS

WORK=ROOT/'.codex-work/parking-final-display-v02-20261025'
LOCK=DOCS/'phase4-display-entry-lock.json'
PROTOCOL=DOCS/'phase4-display-protocol.json'
CATALOG=DOCS/'phase4-display-policies.json'
COHORT=DOCS/'phase4-display-cohort.json'
BASE=ROOT/'.codex-work/parking-local-risk-20261025'
CAL=BASE/'calibration-v3'


def validate_frozen(lock,root=ROOT):
    if lock.get('phase3_complete') is not True or lock.get('phase4_may_start') is not True:
        raise PermissionError('Final experiment requires a completed phase3 and an entry lock')
    for relative,expected in lock['files'].items():
        path=Path(root)/relative
        if not path.is_file() or sha256(path)!=expected:raise PermissionError('Frozen artifact changed: '+relative)
    for name,version in lock['package_versions'].items():
        if importlib.metadata.version(name)!=version:raise PermissionError('Frozen package version changed: '+name)
    if set(lock['allowed_roles'])!={'quarantine_train_reserved','quarantine_final_test'}:
        raise PermissionError('Unexpected partition permission')
    return lock


def frozen_lock():return validate_frozen(read(LOCK))


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


def load_final_bundle(lock,*,primary_only):
    """Only final partition; cohort and window IDs come from pre-evaluation metadata."""
    validate_frozen(lock);role='quarantine_final_test'
    if role not in lock['allowed_roles']:raise PermissionError('Final role not allowed')
    if not (WORK/'training-receipt.json').is_file():raise PermissionError('Train and freeze local models first')
    receipt=read(WORK/'training-receipt.json')
    for rel,h in receipt['model_files'].items():
        if sha256(ROOT/rel)!=h:raise PermissionError('Appended training model changed')
    manifest=read(DEFAULT_WORK/'prepared/data-manifest.json');p=ROOT/manifest['files'][role]['path']
    if sha256(p)!=manifest['files'][role]['sha256']:raise PermissionError('Final source checksum mismatch')
    cohort=read(COHORT);bays=cohort['bay_ids'];where='is_primary AND ' if primary_only else ''
    where+='bay IN ('+','.join(map(str,bays))+')';c=duckdb.connect()
    c.execute("SET memory_limit='1GB'");c.execute('SET threads=2')
    v=c.execute(f'''SELECT bay,window_start,window_end,start_local_seconds,end_local_seconds,state
      FROM read_parquet({quote(p.as_posix())}) WHERE {where} ORDER BY bay,window_start,start_local_seconds''').fetchnumpy();c.close()
    changes=np.r_[True,(v['bay'][1:]!=v['bay'][:-1])|(v['window_start'][1:]!=v['window_start'][:-1])]
    offsets=np.r_[np.flatnonzero(changes),len(v['bay'])].astype(np.int64);first=offsets[:-1]
    bb=np.unique(v['bay']).astype(np.int64);np.testing.assert_array_equal(bb,bays)
    indexes=np.searchsorted(bb,v['bay'][first]).astype(np.int64)
    ids=tuple(hashlib.sha256(f'{int(b)}:{int(a)}:{int(z)}:late'.encode()).hexdigest()[:24]
      for b,a,z in zip(v['bay'][first],v['window_start'][first],v['window_end'][first]))
    key='primary_window_ids' if primary_only else 'sensitivity_window_ids'
    if set(ids)!=set(cohort[key]):raise PermissionError('Final windows differ from locked metadata')
    return Bundle(np.asarray(v['end_local_seconds'],dtype=np.int64),np.asarray(v['state'],dtype=np.int8),offsets,
      np.asarray(v['window_start'][first],dtype=np.int64),indexes,bb,ids,{role:manifest['files'][role]['sha256']})


def train():
    lock=frozen_lock();WORK.mkdir(parents=True,exist_ok=True);(WORK/'models').mkdir(exist_ok=True)
    receiptpath=WORK/'training-receipt.json'
    if receiptpath.exists():
        r=read(receiptpath)
        for p,h in r['model_files'].items():assert sha256(ROOT/p)==h
        return r
    # Entry lock is written before this is called, including all training dependencies.
    cohort=read(COHORT);d=load_bundle(('quarantine_train_reserved',),bay_filter=cohort['bay_ids'],
      training_lock=LOCK,primary_only=False)
    n,cost=collect_bundle(d.ends,d.states,d.offsets,d.starts,d.bay_indexes,len(d.bays))
    np.savez_compressed(WORK/'local-training-statistics.npz',bays=d.bays,n=n,cost=cost)
    priors=np.load(CAL/'shared-priors.npz');state=priors['state'];context=priors['context']
    catalog=read(CATALOG);risk={};paths=[WORK/'local-training-statistics.npz']
    for name,definition in catalog['components'].items():
        p=WORK/'models'/(name+'.npz');kind=definition['kind']
        if kind=='local':
            arm=definition['arm']
            if arm not in risk:risk[arm]=frozen_arm(n,cost,state,context,arm)
            tables=make_tables(risk[arm],definition['lambda_F'],definition['lambda_O'])
            fallback=make_tables((np.repeat(state,24,axis=0) if arm=='pooled_state' else context)[None],definition['lambda_F'],definition['lambda_O'])[0]
            lookup={int(b):i for i,b in enumerate(d.bays)}
            aligned=np.stack([tables[lookup[b]] if b in lookup else fallback for b in cohort['bay_ids']])
            cdfs=np.zeros((len(aligned),2,len(BASE_ACTIONS)));runtime_kind=1
        elif kind=='table':
            aligned=np.tile(np.asarray(definition['table'],dtype=np.int64),(len(cohort['bay_ids']),1))
            cdfs=np.zeros((len(aligned),2,len(BASE_ACTIONS)));runtime_kind=1
        else:
            # This already-frozen S2 training uses only Jan-Jun histories; no refit to final.
            from policies import s2_cdfs
            counts=np.load(ROOT/catalog['S2_training_file'])
            cdfs,_=s2_cdfs(counts['bays'],counts['counts'],np.array(cohort['bay_ids']),definition['budget'])
            aligned=np.full((len(cdfs),48),60,np.int64);runtime_kind=2
        np.savez_compressed(p,bays=np.array(cohort['bay_ids']),tables=aligned,cdfs=cdfs,kind=runtime_kind);paths.append(p)
    r={'created_on':'2026-10-25','entry_lock_sha256':sha256(LOCK),'source_files':d.source_files,'training_bays':len(d.bays),
      'target_bays':len(cohort['bay_ids']),'missing_history_bays':sorted(set(cohort['bay_ids'])-set(map(int,d.bays))),
      'windows':len(d.starts),'anchors':int(n.sum()),'shared_priors_changed':False,'final_states_read':False,
      'model_files':{p.relative_to(ROOT).as_posix():sha256(p) for p in paths}}
    write_json(receiptpath,r);print('Frozen local training ready: '+str((len(d.bays),len(paths)-1)),flush=True);return r


def evaluate():
    lock=frozen_lock();train()
    marker=WORK/'final-evaluation-started.json'
    if not marker.exists():write_json(marker,{'created_on':'2026-10-25','entry_lock_sha256':sha256(LOCK),
      'training_receipt_sha256':sha256(WORK/'training-receipt.json'),'all_final_outcomes_must_be_retained':True})
    else:assert read(marker)['entry_lock_sha256']==sha256(LOCK)
    catalog=read(CATALOG)
    for primary,label in ((True,'primary_7_days'),(False,'sensitivity_1_day')):
        d=load_final_bundle(lock,primary_only=primary);folder=WORK/label;folder.mkdir(exist_ok=True)
        for name,definition in catalog['components'].items():
            p=folder/(name+'.npz');meta=p.with_suffix('.json')
            if p.exists():assert meta.exists() and sha256(p)==read(meta)['arrays_sha256'];continue
            m=np.load(WORK/'models'/(name+'.npz'));np.testing.assert_array_equal(m['bays'],d.bays)
            initial,seeds=d.phases(10,policy_id=name if definition['kind']=='S2' else 'deterministic')
            by,hist=evaluate_component(d.ends,d.states,d.offsets,d.starts,d.bay_indexes,initial,seeds,m['tables'],m['cdfs'],int(m['kind']),len(d.bays))
            np.savez_compressed(p,by_bay_phase=by,histograms=hist,bays=d.bays)
            write_json(meta,{'entry_lock_sha256':sha256(LOCK),'training_receipt_sha256':sha256(WORK/'training-receipt.json'),
              'arrays_sha256':sha256(p),'source_files':d.source_files,'windows':len(d.starts),'phases':10})
            print('FINAL '+label+' '+name,flush=True)
    print('All frozen final components evaluated; no selection or retuning performed',flush=True)


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('stage',choices=('train','evaluate','analyze'));args=a.parse_args()
    if args.stage=='train':train()
    elif args.stage=='evaluate':evaluate()
    else:
        from phase4_analysis import main
        main()
