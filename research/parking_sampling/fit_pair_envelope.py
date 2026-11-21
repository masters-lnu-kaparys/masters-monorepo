"""Single predeclared training-derived cap; no development selection over caps."""
import json
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from data_access import load_bundle
from audit_episode_constraint import WORK,OLD,allowed
from episode_pair_certificate import count_pair_bound_bundle
from refine_policy import full_replay
from simulation import summarize
from run_phase3 import write_json

PLAN=DOCS/'phase3-pair-envelope-plan.json'

def select_cap(pair_sums,tau=60,upper=120):
    pairs=np.asarray(pair_sums,dtype=np.int64)
    if upper<tau or tau<=0 or pairs.ndim!=1 or np.any(pairs<=tau):
        raise ValueError('Every complete pair requires positive occupied time and free time >=tau')
    return int(min(upper,int(pairs.min()))) if len(pairs) else int(tau)

def apply_cap(template,cap):
    table=np.asarray(template,dtype=np.int64).copy()
    if table.shape!=(48,) or not np.all(np.isin(table[:24],[30,45,75])) or np.max(table[24:])>60 or cap<60:
        raise ValueError('Unexpected inherited template or cap')
    table[:24]=np.where(table[:24]==75,int(cap),table[:24])
    return table

def training_pair_sums(data,tau=60):
    values=[]
    for w in range(len(data.starts)):
        a,b=data.offsets[w:w+2];ends=data.ends[a:b];states=data.states[a:b]
        # Both the occupied predecessor and target free episode must be complete,
        # and an earlier free interval must be available in this window.
        ids=np.arange(2,len(ends)-1)
        ids=ids[(states[ids]==0)&(ends[ids]-ends[ids-1]>=tau)]
        values.append(ends[ids]-ends[ids-2])
    return np.concatenate(values) if values else np.empty(0,np.int64)

def main():
    plan=json.loads(PLAN.read_text(encoding='utf-8'));prior=json.loads((OLD/'pre-fit-lock.json').read_text(encoding='utf-8'))
    audit=json.loads((WORK/'pre-fit-lock.json').read_text(encoding='utf-8'));folder=WORK/'pair-envelope-v2';folder.mkdir(exist_ok=True)
    lock={'plan_sha256':sha256(PLAN),'code_sha256':{n:sha256(ROOT/'research/parking_sampling'/n) for n in ('fit_pair_envelope.py','episode_pair_certificate.py')},
      'training_bays':prior['training_bays'],'prior_development_results_known':True,'final_test_evaluated':False,
      'revision':'v2: implement the declared conservative fallback for an empty eligible training set; actual nonempty experiment unchanged'}
    lock_path=folder/'pre-fit-lock.json'
    if lock_path.exists() and json.loads(lock_path.read_text(encoding='utf-8'))!=lock:raise ValueError('C4 lock changed')
    write_json(lock_path,lock)
    train=load_bundle(('train_development',),bay_filter=prior['training_bays']);pairs=training_pair_sums(train)
    cap=select_cap(pairs)
    table=apply_cap(np.load(OLD/'models/C3_without_time_0.25_0.25_75.npz')['lookup'],cap)
    np.savez_compressed(folder/'C4.npz',lookup=table)
    write_json(folder/'selection-before-development-replay.json',{'free_cap_seconds':cap,'eligible_training_pairs':len(pairs),
      'minimum_training_pair_sum_seconds':int(pairs.min()) if len(pairs) else None,
      'risky_training_pairs':int(np.sum(pairs<cap)),'training_source_sha256':train.source_files,
      'model_sha256':sha256(folder/'C4.npz'),'rule_chosen_by_training_only':True,
      'development_outcomes_previously_seen':True,'final_test_evaluated':False})
    print('C4_TRAINING_CAP',cap,'PAIRS',len(pairs),flush=True)
    all_results={}
    for cohort,bays in (('tuning128',prior['tuning_bays']),('check256',audit['new_check_bays']),('check512',prior['fresh_check_bays'])):
        for primary,label in ((True,'primary_7_days'),(False,'sensitivity_1_day')):
            d=load_bundle(('validation_development',),bay_filter=bays,primary_only=primary)
            b,h=full_replay(d,table,'without_time');raw=b.sum(axis=(0,1));initial,_=d.phases(10)
            bounds={g:count_pair_bound_bundle(d.ends,d.states,d.offsets,d.starts,initial,d.bay_indexes,len(d.bays),60,g) for g in {cap,75}}
            np.testing.assert_array_equal(bounds[cap][:,:,0],b[:,:,9])
            if np.any(b[:,:,14]>bounds[cap][:,:,1]):raise AssertionError('Certificate failed')
            # Zero-start bounds consider every complete pair in each window, not
            # only the ten chosen replay phases. This is a path certificate.
            zero=np.zeros((len(d.starts),1),np.int64)
            all_phase_bounds={g:count_pair_bound_bundle(d.ends,d.states,d.offsets,d.starts,zero,d.bay_indexes,len(d.bays),60,g) for g in {cap,75}}
            ref_table=np.full(48,60,np.int64);ref_b,ref_h=full_replay(d,ref_table,'without_time');ref=ref_b.sum(axis=(0,1))
            np.savez_compressed(folder/f'{cohort}_{label}.npz',by_bay_phase=b,delay_histogram=h,bays=d.bays)
            item={'bays':len(d.bays),'windows':len(d.starts),'raw':raw.tolist(),'metrics':summarize(raw,h),
              'fixed60_raw':ref.tolist(),'fixed60_metrics':summarize(ref,ref_h),'original_quality_passes':allowed(raw,ref,14),
              'checks_reduction_percent':float(100*(1-raw[1]/ref[1])),
              'risky_pair_phase_counts':{str(g):int(v[:,:,1].sum()) for g,v in bounds.items()},
              'complete_risky_pairs_all_phases':{str(g):int(v[:,:,1].sum()) for g,v in all_phase_bounds.items()},
              'certificate_holds_for_every_bay_and_phase':True}
            all_results[f'{cohort}_{label}']=item
            print(cohort,label,'checks%',item['checks_reduction_percent'],'F',item['metrics']['false_free_seconds_per_bay_day'],
                  'O',item['metrics']['false_occupied_seconds_per_bay_day'],'M60',int(raw[14]),'bounds',item['complete_risky_pairs_all_phases'],
                  'passes',item['original_quality_passes'],flush=True)
    write_json(folder/'development-results.json',{'free_cap_seconds':cap,'cohorts':all_results,'final_test_evaluated':False})

if __name__=='__main__':main()
