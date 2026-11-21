"""Evaluate the tighter bound for frozen C3, without selecting another policy."""
import json
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from data_access import load_bundle
from audit_episode_constraint import WORK as PREVIOUS,OLD
from stability_audit import WORK
from history_certificate import history_bound_bundle
from run_phase3 import write_json

def main():
    plan=DOCS/'phase3-history-bound-plan.json';audit=json.loads((PREVIOUS/'pre-fit-lock.json').read_text(encoding='utf-8'))
    prior=json.loads((OLD/'pre-fit-lock.json').read_text(encoding='utf-8'))
    folder=WORK/'history-bound';folder.mkdir(parents=True,exist_ok=True)
    lock={'plan_sha256':sha256(plan),'code_sha256':{n:sha256(ROOT/'research/parking_sampling'/n) for n in ('history_certificate.py','assess_history_certificate.py')},
      'frozen_C3_sha256':sha256(OLD/'models/C3_without_time_0.25_0.25_75.npz'),'final_test_evaluated':False}
    path=folder/'pre-analysis-lock.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=lock:raise ValueError('History-bound lock changed')
    write_json(path,lock);results={}
    for cohort,bays,role in (('training256',prior['training_bays'],'train_development'),
        ('check256',audit['new_check_bays'],'validation_development'),('check512',prior['fresh_check_bays'],'validation_development')):
        for primary,label in ((True,'primary_7_days'),(False,'sensitivity_1_day')):
            d=load_bundle((role,),bay_filter=bays,primary_only=primary)
            zeros=np.zeros((len(d.starts),1),np.int64)
            bound=history_bound_bundle(d.ends,d.states,d.offsets,d.starts,zeros,d.bay_indexes,len(d.bays),60,75,900)
            item={'bays':len(d.bays),'windows':len(d.starts),'eligible_complete_episodes':int(bound[:,:,0].sum()),
              'generic_pair_bound':int(bound[:,:,1].sum()),'history_conditioned_bound':int(bound[:,:,2].sum())}
            np.savez_compressed(folder/f'{cohort}_{label}.npz',by_bay_bounds=bound,bays=d.bays)
            results[f'{cohort}_{label}']=item;print(cohort,label,json.dumps(item),flush=True)
    write_json(folder/'results.json',{'cohorts':results,'free_cap_seconds':75,'age_threshold_seconds':900,
      'policy_retuned':False,'final_test_evaluated':False})

if __name__=='__main__':main()
