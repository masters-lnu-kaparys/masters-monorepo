"""Matched intervention on the episode constraint, preserving all old code/results."""
from __future__ import annotations
import hashlib
import itertools
import json
import time
from pathlib import Path
import duckdb
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from data_access import DEFAULT_WORK,load_bundle
from refine_policy import Replay,groups_for,full_replay
from simulation import summarize
from run_phase3 import write_json

WORK=ROOT/'.codex-work/parking-novelty-audit-20261025'
OLD=ROOT/'.codex-work/parking-research-refinement-20261018'
PLAN=DOCS/'phase3-novelty-audit-plan.json'
GUARDS={'display_errors_only':None,'total_missed_episodes':12,'missed_episodes_at_least_60_seconds':14}

def guarded_objective(raw,ref,lf,lo,index):
    if index is not None and raw[index]>ref[index]:return float('inf')
    return float(raw[1]/ref[1]+lf*raw[2]/max(1,ref[2])+lo*raw[3]/max(1,ref[3]))

def allowed(raw,ref,index):
    return bool(raw[2]<=ref[2] and raw[3]<=ref[3] and (index is None or raw[index]<=ref[index]))

def fit(replay,lf,lo,index,config):
    table=np.full(48,60,np.int64);ref=replay(table,'without_time')
    for sweep in range(2):
        changed=False
        for ids in groups_for('without_time'):
            actions=config['free_actions_seconds'] if ids[0]<24 else config['occupied_actions_seconds']
            best=table.copy();bestkey=(guarded_objective(replay(best,'without_time'),ref,lf,lo,index),int(np.abs(best-60).sum()),tuple(best))
            for pause in actions:
                trial=table.copy();trial[ids]=pause
                if np.array_equal(trial,table):continue
                key=(guarded_objective(replay(trial,'without_time'),ref,lf,lo,index),int(np.abs(trial-60).sum()),tuple(trial))
                if key<bestkey:best,bestkey=trial,key
            if not np.array_equal(table,best):table=best;changed=True
        if not changed:break
    return table

def prepare():
    WORK.mkdir(parents=True,exist_ok=True);(WORK/'.gitignore').write_text('*\n!.gitignore\n',encoding='utf-8')
    prior=json.loads((OLD/'pre-fit-lock.json').read_text(encoding='utf-8'))
    prefix=json.loads((DOCS/'phase1-evidence.json').read_text(encoding='utf-8'))['pilot_prefix']['all_inspected_bay_ids']
    excluded=set(prior['tuning_bays'])|set(prior['fresh_check_bays'])|set(map(int,prefix))
    c=duckdb.connect();ids=[int(x[0]) for x in c.execute('SELECT DISTINCT bay FROM read_parquet(?) WHERE split_role=? AND is_primary',[str(DEFAULT_WORK/'prepared/windows.parquet'),'validation_development']).fetchall()];c.close()
    fresh=sorted((b for b in ids if b not in excluded),key=lambda b:hashlib.sha256(f'masters-parking-duration-audit-v1:{b}'.encode()).hexdigest())[:256]
    lock={'plan_sha256':sha256(PLAN),'training_bays':prior['training_bays'],'tuning_bays':prior['tuning_bays'],'new_check_bays':fresh,
      'training_source':'train_development','prior512_excluded':True,'pilot_prefix_excluded':True,
      'code_sha256':{name:sha256(ROOT/'research/parking_sampling'/name) for name in ('audit_episode_constraint.py','refine_policy.py','kernels.py','simulation.py','data_access.py')},
      'prior_c3_model_sha256':sha256(OLD/'models/C3_without_time_0.25_0.25_75.npz'),
      'source_manifest_sha256':sha256(DEFAULT_WORK/'prepared/data-manifest.json'),'final_test_evaluated':False,'new_check_outcomes_seen_at_lock':False}
    path=WORK/'pre-fit-lock.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=lock:raise ValueError('Audit lock changed; use a new version')
    write_json(path,lock);return lock

def main():
    lock=prepare();config=json.loads((DOCS/'phase3-refinement-plan.json').read_text(encoding='utf-8'))
    models=WORK/'models';models.mkdir(exist_ok=True);candidate_path=WORK/'candidates.json'
    if not candidate_path.exists():
        d=load_bundle(('train_development',),bay_filter=lock['training_bays']);replay=Replay(d,3)
        ref=replay(np.full(48,60,np.int64),'without_time');records=[];start=time.monotonic()
        for arm,index in GUARDS.items():
            for lf,lo in itertools.product(config['lambda_F_grid'],config['lambda_O_grid']):
                table=fit(replay,lf,lo,index,config)
                for cap in (75,90,120):
                    clipped=table.copy();clipped[:24]=np.minimum(clipped[:24],cap);name=f'{arm}_{lf}_{lo}_{cap}';raw=replay(clipped,'without_time')
                    np.savez_compressed(models/f'{name}.npz',lookup=clipped)
                    if index==14:
                        old=np.load(OLD/'models'/f'C3_without_time_{lf}_{lo}_{cap}.npz')['lookup']
                        if not np.array_equal(old,clipped):raise ValueError('Protected arm no longer reproduces original C3')
                    records.append({'name':name,'arm':arm,'index':index,'lambda_F':lf,'lambda_O':lo,'free_cap':cap,'training_raw':raw.tolist(),'training_allowed':allowed(raw,ref,index)})
                print(f'fit {arm} F={lf} O={lo}: {replay.calls} replays, {time.monotonic()-start:.1f}s',flush=True)
        write_json(candidate_path,{'candidates':records,'training_reference':ref.tolist(),'training_evaluations':replay.calls,'protected_arm_exactly_reproduces_C3':True})
    trained=json.loads(candidate_path.read_text(encoding='utf-8'))
    d=load_bundle(('validation_development',),bay_filter=lock['tuning_bays']);b,h=full_replay(d,np.full(48,60,np.int64),'without_time');ref=b.sum(axis=(0,1));records=[];cache={}
    for row in trained['candidates']:
        table=np.load(models/f"{row['name']}.npz")['lookup'];key=table.tobytes()
        if key not in cache:
            b,h=full_replay(d,table,'without_time');cache[key]=(b.sum(axis=(0,1)),h)
        raw,h=cache[key];records.append({**row,'tuning_raw':raw.tolist(),'tuning_metrics':summarize(raw,h),'tuning_allowed':allowed(raw,ref,row['index'])})
    selected={}
    for arm in GUARDS:
        rows=[x for x in records if x['arm']==arm and x['training_allowed'] and x['tuning_allowed']]
        best=min(rows,key=lambda x:(x['tuning_raw'][1],x['tuning_raw'][2],x['tuning_raw'][3],x['lambda_F'],x['lambda_O'],x['free_cap'])) if rows else None
        selected[arm]=best['name'] if best else 'fixed60'
    receipt={'candidates':records,'selected':selected,'tuning_reference':ref.tolist(),'new_check_read':False,'final_test_evaluated':False}
    write_json(WORK/'tuning-results.json',receipt)
    write_json(WORK/'selection-before-check.json',{'selected':selected,'tuning_sha256':sha256(WORK/'tuning-results.json'),
      'model_sha256':{n:sha256(models/f'{n}.npz') for n in set(selected.values()) if n!='fixed60'},'new_check_bays':lock['new_check_bays'],'final_test_evaluated':False})
    print('SELECTION '+json.dumps(selected),flush=True)
    check={}
    for primary,label in ((True,'primary_7_days'),(False,'sensitivity_1_day')):
        d=load_bundle(('validation_development',),bay_filter=lock['new_check_bays'],primary_only=primary);folder=WORK/label;folder.mkdir(exist_ok=True)
        definitions={'fixed60':'fixed60',**selected};results={}
        for arm,name in definitions.items():
            table=np.full(48,60,np.int64) if name=='fixed60' else np.load(models/f'{name}.npz')['lookup']
            b,h=full_replay(d,table,'without_time');raw=b.sum(axis=(0,1));np.savez_compressed(folder/f'{arm}.npz',by_bay_phase=b,delay_histogram=h,bays=d.bays)
            results[arm]={'name':name,'raw':raw.tolist(),'metrics':summarize(raw,h)}
        ref=np.array(results['fixed60']['raw'])
        for arm,item in results.items():
            raw=np.array(item['raw']);item['original_quality_passes']=allowed(raw,ref,14);item['checks_reduction_percent']=float(100*(1-raw[1]/ref[1]))
        check[label]={'bays':len(d.bays),'windows':len(d.starts),'results':results}
        print('CHECK '+label+' '+json.dumps({a:{'M0':v['raw'][12],'M60':v['raw'][14],'C_reduction':v['checks_reduction_percent'],'original_quality_passes':v['original_quality_passes']} for a,v in results.items()}),flush=True)
    write_json(WORK/'new-check-results.json',{'cohorts':check,'selection_sha256':sha256(WORK/'selection-before-check.json'),'final_test_evaluated':False})

if __name__=='__main__':main()
