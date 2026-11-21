"""Locked analytical falsification and unchanged development-trace certificate counts."""
import itertools
import json
from pathlib import Path
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from run_phase3 import write_json
from data_access import load_bundle
from history_certificate import history_bound_bundle
from analytic_certificate import reset_certificate,exact_maximum_misses,count_witness_misses,reset_counts_bundle

WORK=ROOT/'.codex-work/parking-analytic-contribution-20261025'
PLAN=DOCS/'phase3-analytic-contribution-plan.json'
BUDGET=ROOT/'.codex-work/parking-budget-comparison-20261025'
NAMES=('eligible','adjacent_pair','legacy_history','end_reset','recursive_reset')


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def prepare():
    WORK.mkdir(exist_ok=True,parents=True)
    (WORK/'.gitignore').write_text('*\n!.gitignore\n',encoding='utf-8')
    previous=read(BUDGET/'pre-fit-lock.json')
    code=('analytic_certificate.py','test_analytic_certificate.py','assess_analytic_contribution.py',
          'history_certificate.py','episode_certificate.py','data_access.py','simulation.py')
    lock={'created_on':'2026-10-25','plan_sha256':sha256(PLAN),
      'code_sha256':{n:sha256(ROOT/'research/parking_sampling'/n) for n in code},
      'cohorts':previous['cohorts'],'previous_budget_lock_sha256':sha256(BUDGET/'pre-fit-lock.json'),
      'parameters':{'tau':60,'G':75,'A':900},'all_prior_development_results_known':True,
      'scope':'No fitted policy, parameter selection, new cohort or final-test access',
      'new_check_cohort_opened':False,'final_test_evaluated':False,'phase4_may_start':False}
    path=WORK/'pre-analysis-lock.json'
    if path.exists():assert read(path)==lock,'Create a new version; do not change a locked run'
    else:write_json(path,lock)
    return lock


def check_one(ends,states,start,tau,G,A):
    cert=reset_certificate(ends,states,start,tau,G,A)
    exact=exact_maximum_misses(ends,states,start,tau,G,A)
    assert exact['maximum_missed']<=cert['recursive_reset']<=cert['end_reset']<=cert['legacy_history']<=cert['adjacent_pair']
    assert exact['eligible']==cert['eligible']
    assert count_witness_misses(ends,states,start,tau,exact['witness'])==exact['maximum_missed']
    for t,state,run,pause in exact['witness']:
        assert 1<=pause<=(tau if state or t-run<A else G)
    return cert,exact


def exhaustive():
    path=WORK/'finite-enumeration.json'
    if path.exists():return read(path)
    counts={'cases':0,'reachable_states':0,'transitions_examined':0,'end_strict_cases':0,
            'recursive_strict_cases':0,'conservative_positive_cases':0}
    for durations in itertools.product((1,2,3),repeat=5):
        ends=np.cumsum(durations)
        for first,start,params in itertools.product((0,1),(0,1),((2,3,2),(2,4,4),(3,5,5))):
            states=(np.arange(5)+first)%2
            c,x=check_one(ends,states,start,*params)
            counts['cases']+=1;counts['reachable_states']+=x['reachable_states']
            counts['transitions_examined']+=x['transitions_examined']
            counts['end_strict_cases']+=c['end_reset']<c['legacy_history']
            counts['recursive_strict_cases']+=c['recursive_reset']<c['end_reset']
            counts['conservative_positive_cases']+=c['recursive_reset']>x['maximum_missed']
    assert counts['cases']==2916
    rng=np.random.default_rng(20261025);uniform=[]
    for case in range(200):
        ends=np.cumsum(rng.integers(1,8,size=6));states=(np.arange(6)+int(rng.integers(2)))%2
        start=int(rng.integers(ends[-2]));tau=int(rng.integers(2,5));G=tau+int(rng.integers(4));A=int(rng.integers(9))
        c,x=check_one(ends,states,start,tau,G,A);full=reset_certificate(ends,states,0,tau,G,A)
        assert x['maximum_missed']<=full['recursive_reset']
        uniform.append({'ends':ends.tolist(),'states':states.tolist(),'start':start,'tau':tau,'G':G,'A':A,
           'local_bound':c['recursive_reset'],'full_window_bound':full['recursive_reset'],
           'maximum_missed':x['maximum_missed']})
    toys={}
    for name,e,s,params in (
      ('end_reset_strict',[6,14,15,19,22],[1,0,1,0,1],(4,6,8)),
      ('recursive_reset_strict',[6,12,16,22,23,27,30],[1,0,1,0,1,0,1],(4,6,8)),
      ('positive_bound_not_tight',[1,2,5,6,9,10],[0,1,0,1,0,1],(3,5,0))):
        c,x=check_one(e,s,0,*params)
        toys[name]={'ends':e,'states':s,'parameters':dict(zip(('tau','G','A'),params)),'counts':c,'exact':x}
    result={'created_on':'2026-10-25','pre_analysis_lock_sha256':sha256(WORK/'pre-analysis-lock.json'),
       'grid':counts,'seeded_arbitrary_start_cases':uniform,'strict_and_conservative_examples':toys,
       'proof_scope':'Integer-grid checks supplement the separate real-time proof; not an exhaustive proof over real time',
       'all_passed':True,'final_test_evaluated':False}
    write_json(path,result);print('ENUMERATION '+json.dumps(counts),flush=True)
    return result


def recorded(lock):
    output=WORK/'recorded-counts.json'
    if output.exists():return read(output)
    cells={}
    for cohort,bays in lock['cohorts'].items():
        role='train_development' if cohort=='training256' else 'validation_development'
        for primary,label in ((True,'primary_7_days'),(False,'sensitivity_1_day')):
            data=load_bundle((role,),bay_filter=bays,primary_only=primary)
            values=reset_counts_bundle(data.ends,data.states,data.offsets,data.starts,data.bay_indexes,len(data.bays),60,75,900)
            old=history_bound_bundle(data.ends,data.states,data.offsets,data.starts,
                np.zeros((len(data.starts),1),np.int64),data.bay_indexes,len(data.bays),60,75,900)[:,0,:]
            np.testing.assert_array_equal(values[:,:3],old)
            assert np.all(values[:,4]<=values[:,3]) and np.all(values[:,3]<=values[:,2]) and np.all(values[:,2]<=values[:,1])
            name=cohort+'_'+label;path=WORK/(name+'.npz')
            np.savez_compressed(path,by_bay=values,bays=data.bays,names=np.array(NAMES))
            cells[name]={'bays':len(data.bays),'windows':len(data.starts),'intervals':len(data.ends),
              'counts':dict(zip(NAMES,map(int,values.sum(axis=0)))),
              'source_files':data.source_files,'arrays_sha256':sha256(path),
              'legacy_count_equal_by_bay':True,'initialization':'Full source-window start; no phase multiplication'}
            print(name+' '+json.dumps(cells[name]['counts']),flush=True)
    result={'created_on':'2026-10-25','pre_analysis_lock_sha256':sha256(WORK/'pre-analysis-lock.json'),
       'parameters':lock['parameters'],'cells':cells,'new_check_cohort_opened':False,'final_test_evaluated':False,
       'interpretation':'Counts are distinct reference episodes potentially missed by some allowed schedule; positive is not an attainability claim. Window criteria overlap.'}
    write_json(output,result)
    return result


if __name__=='__main__':
    lock=prepare();exhaustive();recorded(lock)
