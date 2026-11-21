"""Previously fixed simpler schedules under the same training-derived envelope."""
import json
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from audit_episode_constraint import WORK,OLD,allowed
from data_access import load_bundle
from refine_policy import full_replay
from simulation import summarize
from run_phase3 import write_json

def control_tables(template,cap=72):
    previous=np.asarray(template,dtype=np.int64)
    if previous.shape!=(48,) or not np.all(previous[24:]==60) or not np.all(np.isin(previous[:24],[45,75])):
        raise ValueError('Unexpected fixed backoff template')
    simpler=previous.copy();simpler[:24]=np.where(simpler[:24]==75,cap,simpler[:24])
    constant=np.full(48,60,np.int64);constant[:24]=cap
    return {'simple75':previous.copy(),'simple72':simpler,'state_only72':constant}

def main():
    plan=DOCS/'phase3-pair-envelope-controls-plan.json';out=WORK/'pair-envelope-controls';out.mkdir(exist_ok=True)
    audit=json.loads((WORK/'pre-fit-lock.json').read_text(encoding='utf-8'));prior=json.loads((OLD/'pre-fit-lock.json').read_text(encoding='utf-8'))
    cap=json.loads((WORK/'pair-envelope-v2/selection-before-development-replay.json').read_text(encoding='utf-8'))['free_cap_seconds']
    source=OLD/'controls/backoff_45_900_75_60.npz';tables=control_tables(np.load(source)['lookup'],cap)
    lock={'created_on':'2026-10-25','plan_sha256':sha256(plan),'code_sha256':sha256(__file__),'template_sha256':sha256(source),
      'training_cap_seconds':cap,'development_outcomes_previously_seen':True,'final_test_evaluated':False}
    path=out/'pre-evaluation-lock.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=lock:raise ValueError('Control lock changed')
    write_json(path,lock)
    for name,table in tables.items():np.savez_compressed(out/f'{name}.npz',lookup=table)
    results={}
    for cohort,bays in (('check256',audit['new_check_bays']),('check512',prior['fresh_check_bays'])):
        for primary,label in ((True,'primary_7_days'),(False,'sensitivity_1_day')):
            d=load_bundle(('validation_development',),bay_filter=bays,primary_only=primary)
            ref=json.loads((WORK/'pair-envelope-v2/development-results.json').read_text(encoding='utf-8'))['cohorts'][f'{cohort}_{label}']['fixed60_raw']
            rows={}
            for name,table in tables.items():
                b,h=full_replay(d,table,'without_time');raw=b.sum(axis=(0,1));np.savez_compressed(out/f'{cohort}_{label}_{name}.npz',by_bay_phase=b,delay_histogram=h,bays=d.bays)
                item={'raw':raw.tolist(),'metrics':summarize(raw,h),'original_quality_passes':allowed(raw,np.asarray(ref),14),
                  'checks_reduction_percent':float(100*(1-raw[1]/ref[1]))}
                rows[name]=item
            results[f'{cohort}_{label}']=rows
            print(cohort,label,json.dumps({name:{'checks_reduction':v['checks_reduction_percent'],'F':v['metrics']['false_free_seconds_per_bay_day'],
                'O':v['metrics']['false_occupied_seconds_per_bay_day'],'M60':v['raw'][14],'passes':v['original_quality_passes']} for name,v in rows.items()}),flush=True)
    write_json(out/'results.json',{'cohorts':results,'pre_evaluation_lock_sha256':sha256(path),'final_test_evaluated':False})

if __name__=='__main__':main()
