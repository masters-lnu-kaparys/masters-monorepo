"""Prelocked control selection, then separate replay on existing check cohorts."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import time
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from data_access import load_bundle
from kernels import evaluate_bundle
from policies import s2_cdfs
from simulation import BASE_ACTIONS
from budget_comparison import definitions,choose_mixture,bootstrap_comparison,metrics
from refine_policy import WORK as C3_WORK
from audit_episode_constraint import WORK as AUDIT
from run_phase3 import write_json

WORK=ROOT/'.codex-work/parking-budget-comparison-20261025'
PLAN=DOCS/'phase3-budget-comparison-plan.json'
COUNTS=ROOT/'.codex-work/parking-research-phase3-20261018/models/markov-counts.npz'
FAMILIES=('fixed','state','two_stage','S2','pooled')
WINDOWS=((True,'primary_7_days'),(False,'sensitivity_1_day'))


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def prepare():
    WORK.mkdir(parents=True,exist_ok=True)
    (WORK/'.gitignore').write_text('*\n!.gitignore\n',encoding='utf-8')
    old=read(C3_WORK/'pre-fit-lock.json');audit=read(AUDIT/'pre-fit-lock.json')
    code=('budget_comparison.py','run_budget_comparison.py','test_budget_comparison.py','kernels.py',
          'simulation.py','policies.py','markov_baseline.py','data_access.py')
    lock={'created_on':'2026-10-25','plan_sha256':sha256(PLAN),
      'code_sha256':{n:sha256(ROOT/'research/parking_sampling'/n) for n in code},
      'cohorts':{'training256':old['training_bays'],'tuning128':old['tuning_bays'],
                 'check256':audit['new_check_bays'],'check512':old['fresh_check_bays']},
      'S2_training_counts_sha256':sha256(COUNTS),
      'C3_frozen_sha256':sha256(C3_WORK/'models/C3_without_time_0.25_0.25_75.npz'),
      'C4_json_sha256':sha256(DOCS/'phase3-pair-envelope-policy.json'),
      'prior_check_outcomes_known':True,'new_check_cohort_opened':False,'final_test_evaluated':False,'phase4_may_start':False}
    path=WORK/'pre-fit-lock.json'
    if path.exists() and read(path)!=lock:raise ValueError('Budget experiment lock changed; create a new version')
    if not path.exists():write_json(path,lock)
    bank=definitions()
    np.testing.assert_array_equal(next(d.policy.lookup for d in bank if d.policy.name=='C3'),
                                  np.load(C3_WORK/'models/C3_without_time_0.25_0.25_75.npz')['lookup'])
    description=[{'name':d.policy.name,'groups':list(d.groups),'kind':d.policy.kind,
       'delays':d.policy.delays.tolist(),'lookup':d.policy.lookup.tolist(),'use_time':d.policy.use_time,
       'use_run':d.policy.use_run,'parameters':d.policy.parameters} for d in bank]
    path=WORK/'policy-bank-before-replay.json'
    if path.exists() and read(path)!=description:raise ValueError('Policy bank changed')
    if not path.exists():write_json(path,description)
    return lock,bank


def replay_cell(cohort,primary,lock,bank):
    label='primary_7_days' if primary else 'sensitivity_1_day';name=cohort+'_'+label
    path=WORK/'banks'/(name+'.npz')
    if path.exists():return path
    role='train_development' if cohort=='training256' else 'validation_development'
    d=load_bundle((role,),bay_filter=lock['cohorts'][cohort],primary_only=primary)
    repetitions=3 if cohort=='training256' else 10
    initial,seeds=d.phases(repetitions)
    counts=np.load(COUNTS)
    by=np.zeros((len(bank),len(d.bays),17),np.int64)
    hist=np.zeros((len(bank),301),np.int64);s2notes={}
    started=time.monotonic()
    for index,definition in enumerate(bank):
        p=definition.policy
        cdfs=np.zeros((len(d.bays),2,len(BASE_ACTIONS)))
        if p.kind==2:
            cdfs,notes=s2_cdfs(counts['bays'],counts['counts'],d.bays,p.parameters['budget'])
            s2notes[p.name]=notes
        values,h=evaluate_bundle(d.ends,d.states,d.offsets,d.starts,d.bay_indexes,initial,seeds,
              p.kind,p.delays,p.lookup,p.fallback,p.use_time,p.use_run,cdfs,BASE_ACTIONS,len(d.bays))
        by[index]=values.sum(axis=1);hist[index]=h
        if (index+1)%50==0:print(f'{name}: {index+1}/{len(bank)}; {time.monotonic()-started:.1f}s',flush=True)
    assert np.all(by[:,:,0]==by[0,:,0])
    path.parent.mkdir(exist_ok=True)
    np.savez_compressed(path,by_bay=by,delay_histograms=hist,bays=d.bays,names=np.array([x.policy.name for x in bank]))
    write_json(path.with_suffix('.json'),{'cohort':cohort,'window_criterion':label,'bays':len(d.bays),'windows':len(d.starts),
      'repetitions':repetitions,'stored_aggregation':'All common phases summed within each BayId; not independent samples',
      'source_files':d.source_files,'policy_bank_sha256':sha256(WORK/'policy-bank-before-replay.json'),
      'arrays_sha256':sha256(path),'S2_model_notes':s2notes,'final_test_evaluated':False})
    print(name+' DONE',flush=True)
    return path


def fit():
    lock,bank=prepare()
    path=WORK/'selection-before-check-replay.json'
    if path.exists():
        assert read(path)['pre_fit_lock_sha256']==sha256(WORK/'pre-fit-lock.json')
        print('Existing frozen selection retained');return
    cells=[];arrays=[];files={}
    for cohort in ('training256','tuning128'):
        for primary,label in WINDOWS:
            p=replay_cell(cohort,primary,lock,bank)
            cells.append(cohort+'_'+label);arrays.append(np.load(p)['by_bay'].sum(axis=1));files[p.relative_to(ROOT).as_posix()]=sha256(p)
    values=np.array(arrays);selected={}
    for target in ('C3','C4'):
        ti=next(i for i,d in enumerate(bank) if d.policy.name==target)
        for family in FAMILIES:
            ids=[i for i,d in enumerate(bank) if family in d.groups]
            answer=choose_mixture(values[:,ids,:],values[:,ti,:])
            weights={bank[i].policy.name:float(w) for i,w in zip(ids,answer['weights']) if w>0}
            selected[target+'_'+family]={'target':target,'family':family,'weights':weights,
              'fitting_max_error_ratio':answer['max_error_ratio'],'fitting_resource_ratios':dict(zip(cells,answer['resource_ratios'].tolist())),
              'expected_raw_by_fitting_cell':dict(zip(cells,answer['expected_raw'].tolist()))}
    receipt={'created_on':'2026-10-25','cells':cells,'selected':selected,
      'pre_fit_lock_sha256':sha256(WORK/'pre-fit-lock.json'),'fitting_bank_files':files,
      'current_experiment_check_replays_started':False,'prior_check_results_known':True,
      'new_check_cohort_opened':False,'final_test_evaluated':False,'phase4_may_start':False}
    write_json(path,receipt)
    print('SELECTION '+json.dumps({n:{'t':r['fitting_max_error_ratio'],'weights':r['weights']} for n,r in selected.items()}),flush=True)


def check():
    lock,bank=prepare();selection=read(WORK/'selection-before-check-replay.json')
    path=WORK/'development-results.json'
    if path.exists():print('Existing development report retained');return
    marker=WORK/'pre-check-lock.json'
    expected={'selection_sha256':sha256(WORK/'selection-before-check-replay.json'),
              'pre_fit_lock_sha256':sha256(WORK/'pre-fit-lock.json'),'final_test_evaluated':False}
    if marker.exists() and read(marker)!=expected:raise ValueError('Selection changed before check replay')
    if not marker.exists():write_json(marker,expected)
    results={};index={d.policy.name:i for i,d in enumerate(bank)}
    for cohort in ('check256','check512'):
        for primary,label in WINDOWS:
            p=replay_cell(cohort,primary,lock,bank);arr=np.load(p);values=arr['by_bay'];totals=values.sum(axis=1)
            rows={};envelopes={}
            for key,item in selection['selected'].items():
                target=item['target'];ti=index[target]
                mixture=sum(w*values[index[name]] for name,w in item['weights'].items())
                mixed=mixture.sum(axis=0);candidate=totals[ti]
                rows[key]={'target_metrics':metrics(candidate),'control_metrics':metrics(mixed),
                  'target_raw':candidate.tolist(),'control_expected_raw':mixed.tolist(),
                  'control_to_target_resource_ratio':float(mixed[1]/candidate[1]),
                  'control_to_target_F_ratio':float(mixed[2]/candidate[2]),'control_to_target_O_ratio':float(mixed[3]/candidate[3]),
                  'paired_bay_intervals_target_minus_control':bootstrap_comparison(values[ti],mixture),
                  'frozen_control_point_dominates_target':bool(mixed[1]<=candidate[1]+1e-6 and mixed[2]<candidate[2] and mixed[3]<candidate[3]),
                  'target_point_dominates_frozen_control':bool(candidate[1]<=mixed[1]+1e-6 and candidate[2]<mixed[2] and candidate[3]<mixed[3])}
                ids=[i for i,d in enumerate(bank) if item['family'] in d.groups]
                fitted=choose_mixture(totals[None,ids,:],candidate[None,:],exact_resource=True)
                envelopes[key]={'target':target,'family':item['family'],'hindsight_reference_not_frozen_policy':True,
                  'max_error_ratio':fitted['max_error_ratio'],'exact_expected_budget':True,
                  'weights':{bank[i].policy.name:float(w) for i,w in zip(ids,fitted['weights']) if w>0},
                  'expected_raw':fitted['expected_raw'][0].tolist(),'metrics':metrics(fitted['expected_raw'][0])}
            results[cohort+'_'+label]={'bays':len(arr['bays']),'bank_sha256':sha256(p),
                 'frozen_controls':rows,'equal_expected_budget_hindsight_envelopes':envelopes}
            print('CHECK '+cohort+'_'+label+' '+json.dumps({k:round(v['max_error_ratio'],4) for k,v in envelopes.items()}),flush=True)
    write_json(path,{'created_on':'2026-10-25','cohorts':results,'selection_sha256':sha256(WORK/'selection-before-check-replay.json'),
       'all_results_are_reused_development':True,'new_check_cohort_opened':False,'final_test_evaluated':False,'phase4_may_start':False})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('fit','check'));args=parser.parse_args()
    fit() if args.stage=='fit' else check()
