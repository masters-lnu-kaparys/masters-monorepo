"""C3: train the complete causal schedule by replay; preserve the phase-3 v1 audit."""
from __future__ import annotations
import hashlib
import itertools
import json
import time
from pathlib import Path
import duckdb
import numpy as np
from numba import njit
from prepare_data import ROOT,DOCS,sha256
from data_access import DEFAULT_WORK,load_bundle,tuning_bays
from simulation import BASE_ACTIONS,summarize
from kernels import simulate_window,evaluate_bundle
from policies import constant_policy,s2_cdfs
from run_phase3 import write_json

WORK=ROOT/'.codex-work/parking-research-refinement-20261018'
PLAN=DOCS/'phase3-refinement-plan.json'

@njit(cache=True)
def total_replay(ends,states,offsets,starts,initial,seeds,lookup,use_time,use_run):
    totals=np.zeros(17,np.int64);fallback=np.zeros(48,np.int64)
    cdf=np.zeros((2,13));delays=np.array([60,60],np.int64)
    for w in range(len(starts)):
        for rep in range(initial.shape[1]):
            a,_=simulate_window(ends[offsets[w]:offsets[w+1]],states[offsets[w]:offsets[w+1]],
              starts[w]+initial[w,rep],1,delays,lookup,fallback,use_time,use_run,cdf,BASE_ACTIONS,seeds[w,rep])
            totals+=a
    return totals

def groups_for(variant):
    groups=[]
    for state in range(2):
        for tb in (range(4) if variant!='without_time' else [0]):
            for ab in (range(6) if variant!='without_run' else [0]):
                groups.append([(state*4+t)*6+a for t in range(4) for a in range(6)
                  if (variant=='without_time' or t==tb) and (variant=='without_run' or a==ab)])
    return groups

def objective(raw,reference,lf,lo):
    if raw[14]>reference[14]:return float('inf')
    return float(raw[1]/reference[1]+lf*raw[2]/max(1,reference[2])+lo*raw[3]/max(1,reference[3]))

def feasible(raw,ref):return bool(all(raw[k]<=ref[k] for k in (2,3,14)))

class Replay:
    def __init__(self,data,reps):
        self.data=data;self.initial,self.seeds=data.phases(reps);self.cache={};self.calls=0
    def __call__(self,lookup,variant):
        key=(variant,lookup.tobytes())
        if key not in self.cache:
            d=self.data
            self.cache[key]=total_replay(d.ends,d.states,d.offsets,d.starts,self.initial,self.seeds,lookup,
              variant!='without_time',variant!='without_run')
            self.calls+=1
        return self.cache[key]

def fit_table(replay,variant,lf,lo,config):
    lookup=np.full(48,60,np.int64);ref=replay(lookup,variant);groups=groups_for(variant)
    for sweep in range(2):
        changed=False
        for ids in groups:
            state=ids[0]//24;actions=config['free_actions_seconds'] if state==0 else config['occupied_actions_seconds']
            best=lookup.copy();raw=replay(best,variant)
            best_key=(objective(raw,ref,lf,lo),int(np.abs(best-60).sum()),tuple(best))
            for pause in actions:
                trial=lookup.copy();trial[ids]=pause
                if np.array_equal(trial,lookup):continue
                values=replay(trial,variant)
                key=(objective(values,ref,lf,lo),int(np.abs(trial-60).sum()),tuple(trial))
                if key<best_key:best=trial;best_key=key
            if not np.array_equal(lookup,best):lookup=best;changed=True
        if not changed:break
    return lookup

def cohort_ids(config):
    c=duckdb.connect()
    windows=str(DEFAULT_WORK/'prepared/windows.parquet')
    ids=[int(x[0]) for x in c.execute('SELECT DISTINCT bay FROM read_parquet(?) WHERE split_role=? AND is_primary',[windows,'train_development']).fetchall()]
    validation=[int(x[0]) for x in c.execute('SELECT DISTINCT bay FROM read_parquet(?) WHERE split_role=? AND is_primary',[windows,'validation_development']).fetchall()]
    c.close()
    train=sorted(ids,key=lambda b:hashlib.sha256(f'masters-parking-C3-training-v1:{b}'.encode()).hexdigest())[:256]
    old=[int(b) for b in tuning_bays()]
    prefix=json.loads((DOCS/'phase1-evidence.json').read_text(encoding='utf-8'))
    excluded=set(old)|set(map(int,prefix['pilot_prefix']['all_inspected_bay_ids']))
    fresh=sorted((b for b in validation if b not in excluded),key=lambda b:hashlib.sha256(f'masters-parking-C3-check-v1:{b}'.encode()).hexdigest())[:512]
    return train,old,fresh

def lock_work(config,train,old,fresh):
    WORK.mkdir(parents=True,exist_ok=True);(WORK/'.gitignore').write_text('*\n!.gitignore\n',encoding='utf-8')
    code={name:sha256(ROOT/'research/parking_sampling'/name) for name in ('refine_policy.py','kernels.py','simulation.py','data_access.py','policies.py')}
    lock={'plan_sha256':sha256(PLAN),'code_sha256':code,'training_bays':train,'tuning_bays':old,'fresh_check_bays':fresh,
      'source_manifest_sha256':sha256(DEFAULT_WORK/'prepared/data-manifest.json'),'prior_phase3_results_known':True,
      'fresh_check_outcomes_seen_at_lock':False,'final_test_evaluated':False}
    path=WORK/'pre-fit-lock.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=lock:raise ValueError('Versioned lock changed; create an explicitly new research version')
    write_json(path,lock)

def full_replay(data,lookup,variant,reps=10,kind=1,cdfs=None):
    initial,seeds=data.phases(reps);d=data
    if cdfs is None:cdfs=np.zeros((len(d.bays),2,13))
    return evaluate_bundle(d.ends,d.states,d.offsets,d.starts,d.bay_indexes,initial,seeds,
      kind,np.array([60,60],np.int64),lookup,np.zeros(48,np.int64),variant!='without_time',variant!='without_run',cdfs,BASE_ACTIONS,len(d.bays))

def main():
    config=json.loads(PLAN.read_text(encoding='utf-8'));train,old,fresh=cohort_ids(config);lock_work(config,train,old,fresh)
    models=WORK/'models';models.mkdir(exist_ok=True)
    if not (models/'candidates.json').exists():
        d=load_bundle(('train_development',),bay_filter=train);replay=Replay(d,3)
        reference=replay(np.full(48,60,np.int64),'full');candidates=[];started=time.monotonic()
        for variant in config['variants']:
            for lf,lo in itertools.product(config['lambda_F_grid'],config['lambda_O_grid']):
                table=fit_table(replay,variant,lf,lo,config)
                for cap in config['postfit_free_pause_caps_seconds']:
                    clipped=table.copy();clipped[:24]=np.minimum(clipped[:24],cap)
                    name=f'C3_{variant}_{lf}_{lo}_{cap}';values=replay(clipped,variant)
                    np.savez_compressed(models/f'{name}.npz',lookup=clipped)
                    candidates.append({'name':name,'variant':variant,'lambda_F':lf,'lambda_O':lo,'free_cap':cap,
                      'training_raw':values.tolist(),'training_feasible':feasible(values,reference),'training_metrics':summarize(values)})
                print(f'fit {variant} F={lf} O={lo}: {replay.calls} replays, {time.monotonic()-started:.1f}s',flush=True)
        write_json(models/'candidates.json',{'candidates':candidates,'training_reference':reference.tolist(),
          'training_bays':len(d.bays),'windows':len(d.starts),'evaluations':replay.calls,'source_sha256':d.source_files})
    fit=json.loads((models/'candidates.json').read_text(encoding='utf-8'))
    d=load_bundle(('validation_development',),bay_filter=old)
    by,h=full_replay(d,np.full(48,60,np.int64),'full');ref=by.sum(axis=(0,1));results=[]
    selected={};runtime={};out=WORK/'tuning';out.mkdir(exist_ok=True)
    for candidate in fit['candidates']:
        table=np.load(models/f"{candidate['name']}.npz")['lookup'];key=(candidate['variant'],table.tobytes())
        if key not in runtime:runtime[key]=full_replay(d,table,candidate['variant'])
        by,h=runtime[key];raw=by.sum(axis=(0,1))
        np.savez_compressed(out/f"{candidate['name']}.npz",by_bay_phase=by,delay_histogram=h,bays=d.bays)
        results.append({**candidate,'tuning_raw':raw.tolist(),'tuning_metrics':summarize(raw,h),'tuning_feasible':feasible(raw,ref)})
    for variant in config['variants']:
        eligible=[x for x in results if x['variant']==variant and x['training_feasible'] and x['tuning_feasible']]
        winner=min(eligible,key=lambda x:(x['tuning_raw'][1],x['tuning_raw'][2],x['tuning_raw'][3],x['lambda_F'],x['lambda_O'],x['free_cap'])) if eligible else None
        selected[variant]=winner['name'] if winner else 'fixed_60'
    receipt={'results':results,'tuning_reference':ref.tolist(),'selected':selected,'fresh_check_read':False,'final_test_evaluated':False}
    write_json(WORK/'tuning-results.json',receipt)
    write_json(WORK/'selection-before-fresh-check.json',{'selected':selected,'tuning_results_sha256':sha256(WORK/'tuning-results.json'),
      'model_sha256':{name:sha256(models/f'{name}.npz') for name in set(selected.values()) if name!='fixed_60'},
      'fresh_bays':fresh,'final_test_access':False})
    print('SELECTION '+json.dumps(selected),flush=True)
    check_receipt={'cohorts':{},'selection_file_sha256':sha256(WORK/'selection-before-fresh-check.json'),'final_test_evaluated':False}
    counts=np.load(ROOT/'.codex-work/parking-research-phase3-20261018/models/markov-counts.npz')
    for primary,label in [(True,'primary_7_days'),(False,'sensitivity_1_day')]:
        d=load_bundle(('validation_development',),bay_filter=fresh,primary_only=primary)
        definitions=[('fixed_60',np.full(48,60,np.int64),'full',1,None)]
        for variant,name in selected.items():
            if name!='fixed_60':definitions.append((name,np.load(models/f'{name}.npz')['lookup'],variant,1,None))
        old_c2=np.load(ROOT/'.codex-work/parking-research-phase3-20261018/frozen-policies/C2_0.006_0.024_0.0001.npz')['lookup']
        definitions.append(('old_C2_resource1440',old_c2,'full',1,None))
        for budget in (1440,2880):
            cdfs,notes=s2_cdfs(counts['bays'],counts['counts'],d.bays,budget)
            definitions.append((f'S2_{budget}',np.full(48,60,np.int64),'full',2,cdfs))
        check={};folder=WORK/label;folder.mkdir(exist_ok=True)
        for name,table,variant,kind,cdfs in definitions:
            by,h=full_replay(d,table,variant,kind=kind,cdfs=cdfs);raw=by.sum(axis=(0,1))
            np.savez_compressed(folder/f'{name}.npz',by_bay_phase=by,delay_histogram=h,bays=d.bays)
            check[name]={'raw':raw.tolist(),'metrics':summarize(raw,h)}
        reference=np.array(check['fixed_60']['raw'])
        for name,item in check.items():
            values=np.array(item['raw']);item['quality_passes']=feasible(values,reference)
            item['checks_reduction_percent']=float(100*(1-values[1]/reference[1]))
        check_receipt['cohorts'][label]={'bays':len(d.bays),'windows':len(d.starts),'results':check,'source_sha256':d.source_files}
        print('CHECK '+label+' '+json.dumps({n:{'reduction':i['checks_reduction_percent'],'quality_passes':i['quality_passes'],'M60':i['raw'][14]} for n,i in check.items()}),flush=True)
    write_json(WORK/'fresh-check-results.json',check_receipt)

if __name__=='__main__':main()
