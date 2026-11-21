"""Export/replay the actual research runtime and check aggregation, not just means."""
import hashlib
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from run_phase3 import write_json
from assess_analytic_contribution import read
from run_local_risk import WORK as BASE,old_bank,WINDOWS
from local_risk_calibration_v3 import WORK as CAL
from calibrated_schedule import CalibratedSchedule
from data_access import load_bundle
from kernels import simulate_window
from simulation import reference_simulate,BASE_ACTIONS
from budget_comparison import definitions


def main():
    folder=CAL/'independent-audit';folder.mkdir(exist_ok=True)
    plan=DOCS/'phase3-local-risk-final-audit-plan.json'
    lock={'created_on':'2026-10-25','plan_sha256':sha256(plan),'code_sha256':sha256(__file__),
      'runtime_source_sha256':sha256(ROOT/'research/parking_sampling/calibrated_schedule.py'),
      'calibration_selection_sha256':sha256(CAL/'selection-before-check.json'),'calibration_result_sha256':sha256(CAL/'results.json'),
      'final_test_evaluated':False}
    p=folder/'pre-audit-lock.json'
    if p.exists():assert read(p)==lock
    else:write_json(p,lock)
    selection=read(CAL/'selection-before-check.json');head=selection['headline'];weights=selection['selected'][head]['weights']
    payload={'schema_version':1,'allocation_seed':20261025,'observed_run_edges_seconds':[60,300,900,3600,14400],
      'component_weights':weights,'components':{},'research_status':'Development candidate; not deployed; original zeroM60 criterion fails',
      'selection_sha256':sha256(CAL/'selection-before-check.json')}
    for name in weights:
        assert name!='fixed_60','Current headline is expected to contain actual models only'
        m=np.load(CAL/'models'/(name+'.npz'))
        payload['components'][name]={'pooled_fallback':m['pooled'].tolist(),
          'bay_tables':{str(int(b)):row.tolist() for b,row in zip(m['bays'],m['tables'])}}
    policyfile=DOCS/'phase3-local-risk-policy.json';write_json(policyfile,payload);policy=CalibratedSchedule.load(policyfile)
    previous=read(BASE/'pre-fit-lock.json');result=read(CAL/'results.json');qa=[];aggregation={}
    for cohort in ('check256','check512'):
        for primary,label in WINDOWS:
            cell=cohort+'_'+label;data=load_bundle(('validation_development',),bay_filter=previous['cohorts'][cohort],primary_only=primary)
            initial,seeds=data.phases(10)
            ids=sorted(range(len(data.starts)),key=lambda w:hashlib.sha256(f'local-runtime-QA:{int(data.bays[data.bay_indexes[w]])}:{data.window_ids[w]}'.encode()).hexdigest())[:2]
            unsupported=[w for w in range(len(data.starts)) if str(int(data.bays[data.bay_indexes[w]])) not in next(iter(payload['components'].values()))['bay_tables']]
            if unsupported:ids.append(unsupported[0])
            for w in dict.fromkeys(ids):
                lo,hi=data.offsets[w:w+2];e=data.ends[lo:hi];s=data.states[lo:hi];bay=int(data.bays[data.bay_indexes[w]]);start=int(data.starts[w]+initial[w,0])
                component=payload['components'][policy.component_for_bay(bay)];table=np.array(component['bay_tables'].get(str(bay),component['pooled_fallback']),np.int64)
                fast,h=simulate_window(e,s,start,1,np.array([60,60],np.int64),table,np.zeros(48,np.int64),True,True,
                  np.zeros((2,len(BASE_ACTIONS))),BASE_ACTIONS,np.uint64(1))
                raw,hh,decisions=reference_simulate(e,s,start,lambda o:(policy.next_pause(bay,o),False))
                np.testing.assert_array_equal(fast,raw);np.testing.assert_array_equal(h,hh)
                qa.append({'cell':cell,'bay':bay,'window_id':data.window_ids[w],'phase':0,'raw':raw.tolist(),
                  'fallback':str(bay) not in component['bay_tables'],'decision_count':len(decisions),'all17_and_histogram_equal':True})
                print('INDEPENDENT_RUNTIME '+cell+' '+str(bay)+' '+str(len(decisions)),flush=True)
            old,bays=old_bank(cell);np.testing.assert_array_equal(bays,data.bays);fixed=next(i for i,d in enumerate(definitions()) if d.policy.name=='fixed_60');ref=old[fixed]
            arr=np.load(CAL/(cell+'.npz'));index={n:i for i,n in enumerate(arr['names'])}
            expected=sum(w*arr['by_bay'][index[n]] for n,w in weights.items());actual=np.zeros_like(ref)
            for i,b in enumerate(data.bays):actual[i]=arr['by_bay'][index[policy.component_for_bay(int(b))],i]
            np.testing.assert_array_equal(actual.sum(axis=0),result['cohorts'][cell][head]['primary_raw'])
            rates=actual[:,1:4]/(actual[:,0,None]/86400);refrates=ref[:,1:4]/(ref[:,0,None]/86400)
            trained=np.array([str(int(b)) in next(iter(payload['components'].values()))['bay_tables'] for b in data.bays])
            aggregation[cell]={'bays':len(bays),'with_training_history':int(trained.sum()),'fallback_bays':int((~trained).sum()),
              'macro_primary_means':dict(zip(('calls','F','O'),map(float,rates.mean(axis=0)))),
              'macro_fixed60_means':dict(zip(('calls','F','O'),map(float,refrates.mean(axis=0)))),
              'bays_fewer_calls':int((actual[:,1]<ref[:,1]).sum()),'bays_worse_F':int((actual[:,2]>ref[:,2]).sum()),
              'bays_worse_O':int((actual[:,3]>ref[:,3]).sum()),'bays_no_worse_both_errors_and_fewer_calls':int(((actual[:,1]<ref[:,1])&(actual[:,2]<=ref[:,2])&(actual[:,3]<=ref[:,3])).sum()),
              'primary_M60_count':int(actual[:,14].sum()),'eligible60_episode_phases':int(actual[:,9].sum()),
              'primary_M60_fraction':float(actual[:,14].sum()/actual[:,9].sum())}
    write_json(folder/'runtime-and-aggregation.json',{'created_on':'2026-10-25','pre_audit_lock_sha256':sha256(p),
      'policy_json_sha256':sha256(policyfile),'runtime_reference_checks':qa,'aggregation':aggregation,'final_test_evaluated':False})
    print('RUNTIME_AND_AGGREGATION_DONE '+str(len(qa)),flush=True)


if __name__=='__main__':main()
