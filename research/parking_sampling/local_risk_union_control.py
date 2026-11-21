"""Post-target control audit including broad backoff rules and all prior candidates."""
import time
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from run_phase3 import write_json
from assess_analytic_contribution import read
from run_local_risk import WORK as BASE,old_bank
from local_risk_calibration_v3 import WORK as CAL
from local_risk_wide_control import WORK as WIDE
from budget_comparison import choose_mixture,metrics,bootstrap_comparison,definitions
from budget_coverage_annex import extra_definitions


def main():
    folder=BASE/'union-control';folder.mkdir(exist_ok=True)
    p=folder/'pre-fit-lock.json';lock={'created_on':'2026-10-25','plan_sha256':sha256(DOCS/'phase3-local-risk-final-audit-plan.json'),
      'source_sha256':sha256(__file__),'target_result_sha256':sha256(CAL/'results.json'),'target_outcomes_already_known':True,
      'final_test_evaluated':False}
    if p.exists():assert read(p)==lock
    else:write_json(p,lock)
    for _ in range(3600):
        if (WIDE/'results.json').exists():break
        time.sleep(.5)
    else:raise TimeoutError('Wide control banks incomplete')
    selected=read(CAL/'selection-before-check.json');head=selected['headline'];main=read(CAL/'results.json')
    oldnames=[d.policy.name for d in definitions()+extra_definitions()]
    def values(cell):
        old,bays=old_bank(cell);wide=np.load(WIDE/(cell+'.npz'));np.testing.assert_array_equal(bays,wide['bays'])
        return np.concatenate((old,wide['by_bay']),axis=0),bays,oldnames+wide['names'].tolist()
    fitcells=selected['fitting_cells'];data=np.array([values(c)[0].sum(axis=1) for c in fitcells]);target=np.array(selected['selected'][head]['fitting_expected_raw'])
    names=values(fitcells[0])[2];answer=choose_mixture(data,target);weights={names[i]:float(w) for i,w in enumerate(answer['weights']) if w>0}
    before={'created_on':'2026-10-25','pre_fit_lock_sha256':sha256(p),'headline':head,'weights':weights,'fitting_t':answer['max_error_ratio'],
      'target_checks_known_but_unused_for_control_fitting':True}
    write_json(folder/'selection-before-control-summary.json',before);rows={}
    for cell,targetrows in main['cohorts'].items():
        v,bays,nn=values(cell);cr=sum(w*v[nn.index(n)] for n,w in weights.items());raw=cr.sum(axis=0);tr=np.array(targetrows[head]['expected_raw'])
        hindsight=choose_mixture(v.sum(axis=1)[None],tr[None],True)
        arr=np.load(CAL/(cell+'.npz'));index={n:i for i,n in enumerate(arr['names'])}
        targetby=sum(w*arr['by_bay'][index[n]] for n,w in selected['selected'][head]['weights'].items())
        rows[cell]={'expected_raw':raw.tolist(),'metrics':metrics(raw),'resource_admissible':bool(raw[1]<=tr[1]+1e-6),
          'control_to_candidate_ratios':{m:float(raw[i]/tr[i]) for m,i in (('calls',1),('F',2),('O',3))},
          'paired_candidate_minus_control':bootstrap_comparison(targetby,cr),
          'hindsight_equal_expected_budget':{'t':hindsight['max_error_ratio'],'not_frozen_policy':True,
            'weights':{nn[i]:float(w) for i,w in enumerate(hindsight['weights']) if w>0}}}
    write_json(folder/'results.json',{'created_on':'2026-10-25','selection_sha256':sha256(folder/'selection-before-control-summary.json'),
      'control_count':len(names),'cohorts':rows,'final_test_evaluated':False,'phase4_may_start':False})
    print('UNION_CONTROL '+str({k:(v['control_to_candidate_ratios'],v['hindsight_equal_expected_budget']['t']) for k,v in rows.items()}),flush=True)


if __name__=='__main__':main()
