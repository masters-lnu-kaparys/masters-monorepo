"""Development-only check of the sharper adjacent-pair bound; no policy retuning."""
import json
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from data_access import load_bundle
from audit_episode_constraint import WORK,OLD
from episode_pair_certificate import count_pair_bound_bundle
from run_phase3 import write_json

def main():
    coarse=json.loads((WORK/'cycle-certificate-results.json').read_text(encoding='utf-8'))
    audit=json.loads((WORK/'pre-fit-lock.json').read_text(encoding='utf-8'))
    prior=json.loads((OLD/'pre-fit-lock.json').read_text(encoding='utf-8'))
    selection=json.loads((OLD/'selection-before-fresh-check.json').read_text(encoding='utf-8'))['selected']
    result={'created_on':'2026-10-25','status':'analytical_explanatory_audit_on_previously_used_development_histories',
      'formula':'M_tau <= N(eligible free duration D >= tau AND preceding occupied B + D < free_cap)',
      'occupied_pause_requirement_seconds':60,'free_caps_checked_seconds':[60,75,90,120],
      'source_of_policy_parameters':'Previously fixed C3 and backoff; this analysis changes no parameter',
      'code_sha256':{n:sha256(ROOT/'research/parking_sampling'/n) for n in ('episode_pair_certificate.py','assess_pair_certificate.py')},
      'coarse_results_sha256':sha256(WORK/'cycle-certificate-results.json'),'cohorts':{},'final_test_evaluated':False}
    for cohort,bays in (('new256',audit['new_check_bays']),('prior512',prior['fresh_check_bays'])):
        for primary,label in ((True,'primary_7_days'),(False,'sensitivity_1_day')):
            data=load_bundle(('validation_development',),bay_filter=bays,primary_only=primary);initial,_=data.phases(10)
            bounds={g:count_pair_bound_bundle(data.ends,data.states,data.offsets,data.starts,initial,data.bay_indexes,len(data.bays),60,g) for g in (60,75,90,120)}
            if cohort=='new256':policies={'C3_without_time':(WORK/label/'missed_episodes_at_least_60_seconds.npz',75)}
            else:policies={'C3_full':(OLD/label/f"{selection['full']}.npz",90),
                          'C3_without_time':(OLD/label/f"{selection['without_time']}.npz",75),
                          'simple_backoff':(OLD/'controls'/f'{label}_backoff.npz',75)}
            checks={}
            for policy,(path,cap) in policies.items():
                raw=np.load(path);np.testing.assert_array_equal(raw['bays'],data.bays);r=raw['by_bay_phase'];b=bounds[cap]
                np.testing.assert_array_equal(r[:,:,9],b[:,:,0]);holds=bool(np.all(r[:,:,14]<=b[:,:,1]))
                if not holds:raise AssertionError('Pair certificate violated')
                checks[policy]={'M60':int(r[:,:,14].sum()),'pair_bound':int(b[:,:,1].sum()),
                  'coarse_bound':coarse['cohorts'][f'{cohort}_{label}']['policies'][policy]['bound'],
                  'holds_for_every_bay_and_phase':holds}
            item={'bays':len(data.bays),'windows':len(data.starts),'start_phases':10,
              'eligible_episode_phase_count':int(bounds[60][:,:,0].sum()),
              'pair_bounds_by_free_cap_seconds':{str(k):int(v[:,:,1].sum()) for k,v in bounds.items()},'policies':checks}
            result['cohorts'][f'{cohort}_{label}']=item;print(cohort,label,json.dumps(item),flush=True)
    write_json(WORK/'pair-certificate-results.json',result)

if __name__=='__main__':main()
