"""Prelocked all-initialization coverage diagnostic on already known cohorts."""
import itertools
from pathlib import Path
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from run_phase3 import write_json
from data_access import load_bundle
from simulation import reference_simulate,context
from budget_comparison import definitions
from analytic_certificate import reset_certificate
from start_reachability import FreeProfile,c3_profile,episode_reachability,forward_missed_indices
from assess_analytic_contribution import read

WORK=ROOT/'.codex-work/parking-start-reachability-20261025'
PLAN=DOCS/'phase3-start-reachability-plan.json'
ANALYTIC=ROOT/'.codex-work/parking-analytic-contribution-20261025'


def prepare():
    WORK.mkdir(parents=True,exist_ok=True)
    (WORK/'.gitignore').write_text('*\n!.gitignore\n',encoding='utf-8')
    old=read(ANALYTIC/'pre-analysis-lock.json')
    names=('start_reachability.py','test_start_reachability.py','assess_start_reachability.py',
      'analytic_certificate.py','data_access.py','simulation.py','budget_comparison.py')
    lock={'created_on':'2026-10-25','plan_sha256':sha256(PLAN),
      'code_sha256':{n:sha256(ROOT/'research/parking_sampling'/n) for n in names},'cohorts':old['cohorts'],
      'prior_analytic_lock_sha256':sha256(ANALYTIC/'pre-analysis-lock.json'),
      'all_prior_outcomes_known':True,'new_check_cohort_opened':False,'final_test_evaluated':False,'phase4_may_start':False}
    path=WORK/'pre-analysis-lock.json'
    if path.exists():assert read(path)==lock,'Locked run changed; create a new version'
    else:write_json(path,lock)
    for cap,name in ((75,'C3'),(72,'C4')):
        p=next(x.policy for x in definitions() if x.policy.name==name);profile=c3_profile(cap)
        for age in profile.ages:
            for clock in (0,21600,43200,64800):
                index=context(type('O',(),{'time':clock+age,'state':0,'observed_run_start':clock})(),False,True)
                assert int(p.lookup[index])==profile.free_pause(age)
        for age in (0,30,60,270,300,900,14400):
            index=context(type('O',(),{'time':age,'state':1,'observed_run_start':0})(),False,True)
            assert int(p.lookup[index])==(30 if age<300 else 60)
        if name=='C3':
            frozen=ROOT/'.codex-work/parking-research-refinement-20261018/models/C3_without_time_0.25_0.25_75.npz'
            np.testing.assert_array_equal(p.lookup,np.load(frozen)['lookup'])
    return lock


def validate_small():
    path=WORK/'independent-start-enumeration.json'
    if path.exists():return read(path)
    profiles=(FreeProfile((),5,3),FreeProfile((1,2),5,3),FreeProfile((2,2),6,3))
    counts={'trace_profile_cases':0,'integer_initializations':0,'fractional_initializations':0,'attainable_episode_cases':0}
    examples=[]
    def one(e,s,p,record=False):
        backward=episode_reachability(e,s,0,p);expected=set()
        for t in range(e[-1]):
            missed=forward_missed_indices(e,s,t,p);expected|=missed
            counts['integer_initializations']+=1
            for f in (.25,.75):
                assert forward_missed_indices(e,s,t+f,p)==missed
                counts['fractional_initializations']+=1
        got={row['source_index'] for row in backward['risky_episodes'] if row['attainable']}
        assert got==expected,(e,s,p,got,expected)
        bound=reset_certificate(e,s,0,p.tau,p.plateau,p.ages[-1])
        assert len(expected)<=bound['recursive_reset']
        counts['trace_profile_cases']+=1;counts['attainable_episode_cases']+=len(expected)
        if record:examples.append({'ends':e,'states':s,'prefix_pauses':list(p.prefix_pauses),'plateau':p.plateau,
          'tau':p.tau,'expected_indices':sorted(expected),'backward':backward})
    for durations in itertools.product((1,2,3),repeat=5):
        e=np.cumsum(durations).tolist()
        for first,p in itertools.product((0,1),profiles):one(e,((np.arange(5)+first)%2).tolist(),p)
    assert counts['trace_profile_cases']==1458
    grid=dict(counts);rng=np.random.default_rng(20261025)
    for _ in range(100):
        e=np.cumsum(rng.integers(1,9,size=8)).tolist();s=((np.arange(8)+int(rng.integers(2)))%2).tolist()
        for p in profiles:one(e,s,p,True)
    result={'created_on':'2026-10-25','pre_analysis_lock_sha256':sha256(WORK/'pre-analysis-lock.json'),
      'grid':grid,'combined':counts,'seeded_source_traces':100,'seeded_trace_profile_cases':examples,
      'all_passed':True,'meaning':'All integer initializations plus two fractional representatives, independent forward recurrence; the mathematical reduction covers all fractions'}
    write_json(path,result);print('SMALL '+str(counts),flush=True)
    return result


def recorded(lock):
    path=WORK/'recorded-reachability.json'
    if path.exists():return read(path)
    cells={};positive=[];negative=[]
    for cohort,bays in lock['cohorts'].items():
        role='train_development' if cohort=='training256' else 'validation_development'
        for primary,label in ((True,'primary_7_days'),(False,'sensitivity_1_day')):
            data=load_bundle((role,),bay_filter=bays,primary_only=primary)
            for cap,name in ((75,'C3'),(72,'C4')):
                profile=c3_profile(cap);by=np.zeros((len(data.bays),4),np.int64)
                ops={'candidate_last_samples':0,'plateau_nodes':0,'source_queries':0,'prefix_attempts':0}
                rows=[];policy=next(x.policy for x in definitions() if x.policy.name==name)
                for w in range(len(data.starts)):
                    lo,hi=data.offsets[w:w+2];e=data.ends[lo:hi];s=data.states[lo:hi];start=int(data.starts[w])
                    r=episode_reachability(e,s,start,profile);bound=reset_certificate(e,s,start,60,cap,900)
                    assert r['eligible']==bound['eligible'] and r['generic_pair_bound']==bound['adjacent_pair']
                    assert r['attainable_episodes']<=bound['recursive_reset']
                    by[data.bay_indexes[w]]+=[r['eligible'],r['generic_pair_bound'],bound['recursive_reset'],r['attainable_episodes']]
                    for key in ops:ops[key]+=r['operations'][key]
                    for item in r['risky_episodes']:
                        row={'cohort':cohort,'window_criterion':label,'policy':name,'bay':int(data.bays[data.bay_indexes[w]]),
                          'window_id':data.window_ids[w],'window_start':start,'window_end':int(e[-1]),**item}
                        if item['attainable']:
                            witness=item['witness'];i=item['source_index'];cut_e=e[:i+2];cut_s=s[:i+2]
                            raw,h,decisions=reference_simulate(cut_e,cut_s,witness['initial_start'],
                                lambda o:(int(policy.lookup[context(o,False,True)]),False))
                            times=[int(d[0]) for d in decisions]
                            assert [t for t in times if t<=witness['last_free_sample']]==witness['sample_times_through_last_free']
                            assert not any(item['a']<=t<item['b'] for t in times)
                            assert raw[14]>=1
                            row['independent_reference_verified']=True
                            row['initial_offset_seconds']=witness['initial_start']-start
                            row['target_slice_reference_raw']=raw.tolist()
                            row['reference_decisions']=[list(d) for d in decisions]
                            positive.append(row)
                        else:negative.append(row)
                        rows.append(row)
                cell=cohort+'_'+label+'_'+name;arrays=WORK/(cell+'.npz')
                np.savez_compressed(arrays,by_bay=by,bays=data.bays,
                    names=np.array(['eligible','generic_pair_bound','recursive_bound','attainable_episodes']))
                counts=dict(zip(('eligible','generic_pair_bound','recursive_bound','attainable_episodes'),map(int,by.sum(axis=0))))
                cells[cell]={'cohort':cohort,'policy':name,'window_criterion':label,'bays':len(data.bays),
                  'windows':len(data.starts),'counts':counts,'operations':ops,'source_files':data.source_files,
                  'arrays_sha256':sha256(arrays),'risky_episodes':rows}
                print(cell+' '+str(counts),flush=True)
    result={'created_on':'2026-10-25','pre_analysis_lock_sha256':sha256(WORK/'pre-analysis-lock.json'),
      'cells':cells,'positive_witness_rows':len(positive),'negative_candidate_rows':len(negative),
      'count_semantics':'Individually attainable episodes, potentially different initialization for every episode; overlapping criteria are not independent',
      'new_check_cohort_opened':False,'final_test_evaluated':False,'phase4_may_start':False}
    write_json(path,result);write_json(WORK/'positive-witnesses.json',positive);write_json(WORK/'excluded-candidates.json',negative)
    return result


if __name__=='__main__':
    lock=prepare();validate_small();recorded(lock)
