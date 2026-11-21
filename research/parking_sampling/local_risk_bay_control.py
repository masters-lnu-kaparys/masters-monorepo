"""Frozen simpler personalized controls; no base-check outcomes enter fitting."""
import time
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from run_phase3 import write_json
from assess_analytic_contribution import read
from run_local_risk import WORK,grid,old_bank,model_tables,solve_control,WINDOWS
from local_risk import align_tables,evaluate_local
from data_access import load_bundle
from budget_comparison import metrics,bootstrap_comparison

ANNEX=WORK/'bay-state-control'
PLAN=DOCS/'phase3-local-risk-bay-control-plan.json'


def wait_json(path):
    for _ in range(1800):
        if path.exists():
            try:return read(path)
            except ValueError:pass
        time.sleep(.5)
    raise TimeoutError('Dependency did not finish: '+str(path))


def main():
    ANNEX.mkdir(exist_ok=True)
    pre={'created_on':'2026-10-25','plan_sha256':sha256(PLAN),'source_sha256':sha256(__file__),
      'base_fit_lock_sha256':sha256(WORK/'pre-fit-lock.json'),'new_check_cohort_opened':False,'final_test_evaluated':False}
    path=ANNEX/'pre-fit-lock.json'
    if path.exists():assert read(path)==pre
    else:write_json(path,pre)
    base=wait_json(WORK/'selection-before-check.json');bank=grid();indexes=[i for i,d in enumerate(bank) if d['arm']=='bay_state_alpha50']
    stats=np.load(WORK/'training-statistics.npz');risk_cache={};selection=ANNEX/'selection-before-annex-check.json'
    if selection.exists():selected=read(selection)
    else:
        cr=np.array([np.load(WORK/(cell+'.npz'))['by_bay'][indexes].sum(axis=1) for cell in base['fitting_cells']]);controls={};needed=set()
        for key,target in base['selected'].items():
            raw=np.array([target['raw_by_cell'][cell] for cell in base['fitting_cells']]);answer=solve_control(cr,raw,target['criterion']=='original_strict')
            weights={bank[i]['name']:float(w) for i,w in zip(indexes,answer.pop('weights',[])) if w>0};needed.update(weights)
            controls[key]={'weights':weights,**answer}
        hashes={};byname={d['name']:d for d in bank};(ANNEX/'models').mkdir(exist_ok=True)
        for name in sorted(needed):
            tables,pooled=model_tables(stats,byname[name],risk_cache);p=ANNEX/'models'/(name+'.npz')
            np.savez_compressed(p,bays=stats['bays'],tables=tables,pooled=pooled);hashes[name]=sha256(p)
        selected={'created_on':'2026-10-25','annex_lock_sha256':sha256(path),'base_selection_sha256':sha256(WORK/'selection-before-check.json'),
          'base_check_results_existed_when_annex_frozen':(WORK/'check-results.json').exists(),
          'base_check_outcomes_used_for_annex_fit':False,'controls':controls,'models':hashes,'final_test_evaluated':False}
        write_json(selection,selected)
        print('BAY_CONTROLS_FROZEN '+str(len(hashes)),flush=True)
    base_result=wait_json(WORK/'check-results.json');cohorts={};lock=read(WORK/'pre-fit-lock.json');names=sorted(selected['models'])
    for cohort in ('check256','check512'):
        for primary,label in WINDOWS:
            cell=cohort+'_'+label;path=ANNEX/(cell+'.npz')
            d=load_bundle(('validation_development',),bay_filter=lock['cohorts'][cohort],primary_only=primary)
            if not path.exists():
                init,seeds=d.phases(10);out=np.zeros((len(names),len(d.bays),17),np.int64)
                for i,name in enumerate(names):
                    p=ANNEX/'models'/(name+'.npz');assert sha256(p)==selected['models'][name];m=np.load(p)
                    table,missing=align_tables(m['bays'],m['tables'],d.bays,m['pooled'])
                    values,h=evaluate_local(d.ends,d.states,d.offsets,d.starts,d.bay_indexes,init,seeds,table,len(d.bays));out[i]=values.sum(axis=1)
                np.savez_compressed(path,by_bay=out,bays=d.bays,names=np.array(names))
            arrays=np.load(path);prior,bays=old_bank(cell);basebank=np.load(WORK/(cell+'.npz'));baseindex={n:i for i,n in enumerate(basebank['names'])}
            rows={}
            for key,target in base['selected'].items():
                control=selected['controls'][key]
                if not control['feasible']:rows[key]={'feasible':False};continue
                cr=sum(weight*arrays['by_bay'][names.index(name)] for name,weight in control['weights'].items())
                # Fixed60 has row4 in the standard13x13 state grid, but resolve by name.
                from budget_comparison import definitions
                fixed=next(i for i,x in enumerate(definitions()) if x.policy.name=='fixed_60')
                targetby=prior[fixed] if target['name']=='fixed_60' else basebank['by_bay'][baseindex[target['name']]]
                tr=targetby.sum(axis=0);raw=cr.sum(axis=0);ratios={m:float(raw[i]/tr[i]) for m,i in (('calls',1),('F',2),('O',3))}
                admitted=bool(raw[1]<=tr[1]+1e-6)
                rows[key]={'feasible':True,'expected_raw':raw.tolist(),'metrics':metrics(raw),'control_to_candidate_ratios':ratios,
                  'resource_admissible':admitted,'coverage_admissible':bool(raw[14]<=tr[14]+1e-6),
                  'target_5percent_gain_at_admissible_budget':admitted and ratios['F']>=1 and ratios['O']>=1 and max(ratios['F'],ratios['O'])>=1/.95,
                  'paired_candidate_minus_control':bootstrap_comparison(targetby,cr)}
            cohorts[cell]=rows
            write_json(ANNEX/'progress.json',cohorts)
            print('BAY_CONTROL_CHECK '+cell,flush=True)
    gates={key:sum(cell[key].get('target_5percent_gain_at_admissible_budget',False) for cell in cohorts.values()) for key in base['selected']}
    write_json(ANNEX/'results.json',{'created_on':'2026-10-25','selection_sha256':sha256(selection),
      'base_result_sha256':sha256(WORK/'check-results.json'),'cohorts':cohorts,'cells_with_5percent_gain_at_admissible_budget':gates,
      'new_check_cohort_opened':False,'final_test_evaluated':False,'phase4_may_start':False})
    print('BAY_CONTROL_GATES '+str(gates),flush=True)


if __name__=='__main__':main()
