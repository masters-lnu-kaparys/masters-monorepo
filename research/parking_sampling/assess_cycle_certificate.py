"""Evaluate the derived trace bound on development histories only, without tuning."""
import json
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from data_access import load_bundle
from episode_certificate import count_bound_bundle,duration_counterexample
from audit_episode_constraint import WORK,OLD
from run_phase3 import write_json

def main():
    audit=json.loads((WORK/'pre-fit-lock.json').read_text(encoding='utf-8'))
    previous=json.loads((OLD/'pre-fit-lock.json').read_text(encoding='utf-8'))
    selection=json.loads((OLD/'selection-before-fresh-check.json').read_text(encoding='utf-8'))['selected']
    result={'created_on':'2026-10-25','analysis_status':'post_ablation_explanatory_analysis_no_policy_retuning',
      'formula':'M_tau <= count(eligible free >= tau with immediately preceding occupied < L)',
      'assumptions':'instantaneous correct observations of the recorded binary trace; occupied pauses <= tau; free pauses <= tau+L; no unknown intervals bridged',
      'code_sha256':{n:sha256(ROOT/'research/parking_sampling'/n) for n in ('episode_certificate.py','assess_cycle_certificate.py')},
      'counterexample':duration_counterexample(),'cohorts':{},'final_test_evaluated':False}
    for cohort,bays in (('new256',audit['new_check_bays']),('prior512',previous['fresh_check_bays'])):
        for primary,label in ((True,'primary_7_days'),(False,'sensitivity_1_day')):
            data=load_bundle(('validation_development',),bay_filter=bays,primary_only=primary)
            initial,_=data.phases(10);bounds={}
            for extension in (0,15,30,60):
                values=count_bound_bundle(data.ends,data.states,data.offsets,data.starts,initial,data.bay_indexes,len(data.bays),60,extension)
                bounds[extension]=values
            if cohort=='new256':
                policies={'C3_without_time':(WORK/label/'missed_episodes_at_least_60_seconds.npz',75,60)}
            else:
                policies={
                  'C3_full':(OLD/label/f"{selection['full']}.npz",90,60),
                  'C3_without_time':(OLD/label/f"{selection['without_time']}.npz",75,60),
                  'simple_backoff':(OLD/'controls'/f'{label}_backoff.npz',75,60)}
                for variant in ('full','without_time'):
                    table=np.load(OLD/'models'/f'{selection[variant]}.npz')['lookup']
                    if np.max(table[24:])>60 or np.max(table[:24])>(90 if variant=='full' else 75):
                        raise ValueError('Declared policy caps do not hold globally')
            checks={}
            for policy,(path,free_cap,occupied_cap) in policies.items():
                raw=np.load(path);np.testing.assert_array_equal(raw['bays'],data.bays)
                b=raw['by_bay_phase'];bound=bounds[free_cap-60]
                np.testing.assert_array_equal(b[:,:,9],bound[:,:,0])
                holds=bool(np.all(b[:,:,14]<=bound[:,:,1]))
                if not holds:raise AssertionError('Analytical certificate violated')
                checks[policy]={'M60':int(b[:,:,14].sum()),'bound':int(bound[:,:,1].sum()),
                    'holds_for_every_bay_and_phase':holds,'free_cap_seconds':free_cap,'occupied_cap_seconds':occupied_cap}
            item={'bays':len(data.bays),'windows':len(data.starts),'start_phases':10,
              'eligible_episode_phase_count':int(bounds[0][:,:,0].sum()),
              'bounds_by_extension_seconds':{str(k):int(v[:,:,1].sum()) for k,v in bounds.items()},'policies':checks}
            result['cohorts'][f'{cohort}_{label}']=item
            print(cohort,label,json.dumps(item),flush=True)
    write_json(WORK/'cycle-certificate-results.json',result)

if __name__=='__main__':main()
