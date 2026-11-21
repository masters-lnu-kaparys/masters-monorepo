"""Exact-budget hindsight envelopes over all same-estimator simpler control models."""
import time
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from run_phase3 import write_json
from assess_analytic_contribution import read
from run_local_risk import WORK as BASE,grid,model_tables,old_bank,WINDOWS
from local_risk_calibration_v3 import WORK as CAL
from local_risk import align_tables,evaluate_local
from data_access import load_bundle
from budget_comparison import choose_mixture,definitions

WORK=BASE/'full-model-control'
PLAN=DOCS/'phase3-local-risk-full-model-control-plan.json'


def main():
    WORK.mkdir(exist_ok=True)
    pre={'created_on':'2026-10-25','plan_sha256':sha256(PLAN),'code_sha256':sha256(__file__),
      'target_selection_sha256':sha256(CAL/'selection-before-check.json'),'target_results_sha256':sha256(CAL/'results.json'),
      'target_outcomes_already_known':True,'final_test_evaluated':False}
    p=WORK/'pre-analysis-lock.json'
    if p.exists():assert read(p)==pre
    else:write_json(p,pre)
    models=[d for d in grid() if d['arm'] in ('pooled_state','pooled_clock_age','bay_state_alpha50','bay_full_alpha0')]
    stats=np.load(BASE/'training-statistics.npz');cache={};tables={d['name']:model_tables(stats,d,cache) for d in models}
    lock=read(BASE/'pre-fit-lock.json');target=read(CAL/'results.json');out={};began=time.monotonic()
    for cohort in ('check256','check512'):
        for primary,label in WINDOWS:
            cell=cohort+'_'+label;path=WORK/(cell+'.npz');d=load_bundle(('validation_development',),bay_filter=lock['cohorts'][cohort],primary_only=primary)
            if not path.exists():
                base=np.load(BASE/(cell+'.npz'));cal=np.load(CAL/(cell+'.npz'));available={n:base['by_bay'][i] for i,n in enumerate(base['names'])}
                available.update({n:cal['by_bay'][i] for i,n in enumerate(cal['names'])});outarray=np.zeros((len(models),len(d.bays),17),np.int64)
                initial,seeds=d.phases(10);reused=[]
                for i,definition in enumerate(models):
                    name=definition['name']
                    if name in available:outarray[i]=available[name];reused.append(name);continue
                    tab,pool=tables[name];aligned,missing=align_tables(stats['bays'],tab,d.bays,pool)
                    by,h=evaluate_local(d.ends,d.states,d.offsets,d.starts,d.bay_indexes,initial,seeds,aligned,len(d.bays));outarray[i]=by.sum(axis=1)
                    if (i+1)%64==0:print('FULL_MODEL '+cell+' '+str(i+1)+f'/256 {time.monotonic()-began:.1f}s',flush=True)
                np.savez_compressed(path,by_bay=outarray,bays=d.bays,names=np.array([x['name'] for x in models]))
                write_json(path.with_suffix('.json'),{'arrays_sha256':sha256(path),'reused_names':reused,'source_files':d.source_files,
                  'bays':len(d.bays),'windows':len(d.starts),'repetitions':10})
            arr=np.load(path);old,bays=old_bank(cell);np.testing.assert_array_equal(arr['bays'],bays)
            fixed=next(i for i,x in enumerate(definitions()) if x.policy.name=='fixed_60')
            values=np.concatenate((arr['by_bay'],old[fixed:fixed+1]),axis=0);names=arr['names'].tolist()+['fixed_60']
            raw=np.array(target['cohorts'][cell][target['headline']]['expected_raw']);rows={}
            families={'pooled':('pooled_state','pooled_clock_age'),'bay_state':('bay_state_alpha50',),'unshrunk':('bay_full_alpha0',),
              'union':('pooled_state','pooled_clock_age','bay_state_alpha50','bay_full_alpha0')}
            for family,arms in families.items():
                ids=[i for i,x in enumerate(models) if x['arm'] in arms]+[len(models)]
                answer=choose_mixture(values[ids].sum(axis=1)[None],raw[None],True)
                rows[family]={'policy_count':len(ids),'t':answer['max_error_ratio'],
                  'weights':{names[i]:float(w) for i,w in zip(ids,answer['weights']) if w>0},
                  'expected_raw':answer['expected_raw'][0].tolist(),'hindsight_not_frozen_policy':True}
            out[cell]=rows;write_json(WORK/'progress.json',out)
            print('FULL_MODEL_ENVELOPES '+cell+' '+str({k:v['t'] for k,v in rows.items()}),flush=True)
    write_json(WORK/'results.json',{'created_on':'2026-10-25','pre_analysis_lock_sha256':sha256(p),'cohorts':out,
      'all_hindsight_not_deployable_controls':True,'final_test_evaluated':False,'phase4_may_start':False})


if __name__=='__main__':main()
