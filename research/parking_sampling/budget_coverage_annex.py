"""Explicit post-primary follow-up: equal resource AND original M60 constraint."""
import argparse
from itertools import product
import json
import shutil
import time
import numpy as np
from scipy.optimize import linprog
from prepare_data import ROOT,DOCS,sha256
from data_access import load_bundle
from simulation import AGES,BASE_ACTIONS
from policies import constant_policy,Policy
from kernels import evaluate_bundle
from budget_comparison import Definition,definitions,metrics,bootstrap_comparison
from run_budget_comparison import WORK,read,FAMILIES,WINDOWS
from run_phase3 import write_json

ANNEX=WORK/'coverage-annex-v2'
PREVIOUS=WORK/'coverage-annex'
PLAN=DOCS/'phase3-budget-coverage-annex-v2-plan.json'


def extra_definitions():
    out=[]
    for free,occupied in product(sorted([*map(int,BASE_ACTIONS),72]),repeat=2):
        if 72 not in (free,occupied):continue
        out.append(Definition(constant_policy(free,occupied),('fixed','state','pooled') if free==occupied else ('state','pooled')))
    for fe,fa,oe,ol in product((30,45,60),(300,900),(30,45,60),(45,60)):
        if oe>ol:continue
        table=np.empty(48,np.int64)
        for state in range(2):
            early,edge,late=(fe,fa,72) if state==0 else (oe,300,ol)
            for tb in range(4):
                for ab,age in enumerate((0,*AGES)):table[(state*4+tb)*6+ab]=early if age<edge else late
        name=f'two_stage_F{fe}_{fa}_72_O{oe}_300_{ol}'
        out.append(Definition(Policy(name,'two_stage',1,np.array([60,60],np.int64),table,np.zeros(48,np.int64),
                    False,True,{'free':[fe,fa,72],'occupied':[oe,300,ol]}),('two_stage','pooled')))
    return out


def solve_covered(controls,target,exact=False):
    controls=np.asarray(controls,dtype=float);target=np.asarray(target,dtype=float)
    if controls.ndim!=3 or target.shape!=(len(controls),17) or controls.shape[2]!=17:
        raise ValueError('Invalid counter dimensions')
    if np.any(controls<0) or np.any(target<0) or not np.all(np.isfinite(controls)) or not np.all(np.isfinite(target)):
        raise ValueError('Invalid counters')
    if not np.allclose(controls[:,:,0],target[:,None,0],rtol=0,atol=0):raise ValueError('Unequal exposure')
    if np.any(target[:,[0,1,2,3]]<=0) or (exact and len(target)!=1):raise ValueError('Invalid target')
    k=controls.shape[1];ub=[];limits=[];eq=[np.r_[np.ones(k),0.]];rhs=[1.]
    for c in range(len(target)):
        row=np.r_[controls[c,:,1]/target[c,1],0.]
        if exact:eq.append(row);rhs.append(1.)
        else:ub.append(row);limits.append(1.)
        for metric in (2,3):ub.append(np.r_[controls[c,:,metric]/target[c,metric],-1.]);limits.append(0.)
        scale=max(1.,target[c,14]);ub.append(np.r_[controls[c,:,14]/scale,0.]);limits.append(target[c,14]/scale)
    answer=linprog(np.r_[np.zeros(k),1.],A_ub=np.array(ub),b_ub=np.array(limits),
                  A_eq=np.array(eq),b_eq=np.array(rhs),bounds=(0,None),method='highs')
    if not answer.success:raise ValueError('Coverage LP failed: '+answer.message)
    weights=np.maximum(answer.x[:k],0);weights[weights<1e-12]=0;weights/=weights.sum()
    raw=np.einsum('p,cpj->cj',weights,controls)
    if np.any(raw[:,14]>target[:,14]+1e-7):raise ArithmeticError('Coverage constraint residual')
    if exact:
        if not np.allclose(raw[:,1]/target[:,1],1,rtol=0,atol=1e-7):raise ArithmeticError('Resource equality residual')
    elif np.any(raw[:,1]/target[:,1]>1+1e-7):raise ArithmeticError('Resource cap residual')
    t=float(np.max(raw[:,2:4]/target[:,2:4]))
    if abs(t-answer.fun)>1e-6:raise ArithmeticError('Objective residual')
    return {'weights':weights,'expected_raw':raw,'max_error_ratio':t}


def prepare():
    ANNEX.mkdir(exist_ok=True)
    lock={'created_on':'2026-10-25','plan_sha256':sha256(PLAN),
      'code_sha256':{n:sha256(ROOT/'research/parking_sampling'/n) for n in ('budget_coverage_annex.py','test_budget_coverage_annex.py')},
      'primary_results_sha256':sha256(WORK/'development-results.json'),
      'primary_selection_sha256':sha256(WORK/'selection-before-check-replay.json'),
      'base_plan_sha256':sha256(DOCS/'phase3-budget-coverage-annex-plan.json'),
      'v1_incomplete_execution_sha256':sha256(PREVIOUS/'incomplete-execution.json'),
      'primary_outcomes_known_before_annex':True,'final_test_evaluated':False,'phase4_may_start':False}
    p=ANNEX/'pre-fit-lock.json'
    if p.exists() and read(p)!=lock:raise ValueError('Annex lock changed')
    if not p.exists():write_json(p,lock)
    return read(WORK/'pre-fit-lock.json'),definitions()+extra_definitions()


def cell_values(cohort,primary,lock,bank):
    label='primary_7_days' if primary else 'sensitivity_1_day';cell=cohort+'_'+label
    old=np.load(WORK/'banks'/(cell+'.npz'));p=ANNEX/(cell+'.npz');extras=bank[269:]
    previous=PREVIOUS/(cell+'.npz')
    if not p.exists() and previous.exists():
        assert read(previous.with_suffix('.json'))['arrays_sha256']==sha256(previous)
        shutil.copy2(previous,p);shutil.copy2(previous.with_suffix('.json'),p.with_suffix('.json'))
        write_json(ANNEX/(cell+'-cache-reuse.json'),{'source':previous.relative_to(ROOT).as_posix(),
                   'source_sha256':sha256(previous),'exact_binary_copy':True})
    if not p.exists():
        d=load_bundle(('train_development' if cohort=='training256' else 'validation_development',),
                      bay_filter=lock['cohorts'][cohort],primary_only=primary)
        initial,seeds=d.phases(3 if cohort=='training256' else 10)
        np.testing.assert_array_equal(old['bays'],d.bays)
        rows=[]
        for definition in extras:
            x=definition.policy
            by,h=evaluate_bundle(d.ends,d.states,d.offsets,d.starts,d.bay_indexes,initial,seeds,x.kind,x.delays,
                 x.lookup,x.fallback,x.use_time,x.use_run,np.zeros((len(d.bays),2,len(BASE_ACTIONS))),BASE_ACTIONS,len(d.bays))
            rows.append(by.sum(axis=1))
        rows=np.array(rows);assert np.all(rows[:,:,0]==old['by_bay'][0,:,0])
        np.savez_compressed(p,by_bay=rows,bays=d.bays,names=np.array([x.policy.name for x in extras]))
        write_json(p.with_suffix('.json'),{'primary_bank_sha256':sha256(WORK/'banks'/(cell+'.npz')),
          'arrays_sha256':sha256(p),'extra_policies':57,'windows':len(d.starts),'repetitions':initial.shape[1],
          'source_files':d.source_files,'final_test_evaluated':False})
        print('ANNEX '+cell+' DONE',flush=True)
    new=np.load(p)
    return np.concatenate((old['by_bay'],new['by_bay']),axis=0)


def fit():
    lock,bank=prepare();p=ANNEX/'selection-before-annex-check.json'
    if p.exists():print('Existing annex selection retained');return
    cells=[];values=[]
    for cohort in ('training256','tuning128'):
        for primary,label in WINDOWS:
            cells.append(cohort+'_'+label);values.append(cell_values(cohort,primary,lock,bank).sum(axis=1))
    values=np.array(values);selected={}
    for target in ('C3','C4'):
        ti=next(i for i,d in enumerate(bank) if d.policy.name==target)
        for family in FAMILIES:
            ids=[i for i,d in enumerate(bank) if family in d.groups]
            try:a=solve_covered(values[:,ids,:],values[:,ti,:])
            except ValueError as error:
                if 'infeasible' not in str(error).lower():raise
                selected[target+'_'+family]={'target':target,'family':family,'feasible':False,'reason':str(error)}
                continue
            selected[target+'_'+family]={'target':target,'family':family,'feasible':True,'max_error_ratio':a['max_error_ratio'],
              'weights':{bank[i].policy.name:float(w) for i,w in zip(ids,a['weights']) if w>0},
              'fitting_expected_raw':a['expected_raw'].tolist()}
    write_json(p,{'created_on':'2026-10-25','cells':cells,'selected':selected,
                 'annex_lock_sha256':sha256(ANNEX/'pre-fit-lock.json'),'annex_check_replays_started':False,
                 'all_primary_check_outcomes_known':True,'final_test_evaluated':False})
    print('ANNEX SELECTION '+json.dumps({k:round(v['max_error_ratio'],5) if v['feasible'] else 'infeasible' for k,v in selected.items()}),flush=True)


def check():
    lock,bank=prepare();selection=read(ANNEX/'selection-before-annex-check.json');p=ANNEX/'results.json'
    if p.exists():print('Existing annex results retained');return
    write_json(ANNEX/'pre-check-lock.json',{'selection_sha256':sha256(ANNEX/'selection-before-annex-check.json'),
                                         'primary_results_known':True,'final_test_evaluated':False})
    index={d.policy.name:i for i,d in enumerate(bank)};result={}
    for cohort in ('check256','check512'):
        for primary,label in WINDOWS:
            cell=cohort+'_'+label;values=cell_values(cohort,primary,lock,bank);totals=values.sum(axis=1);rows={}
            for key,item in selection['selected'].items():
                ti=index[item['target']];raw=totals[ti]
                ids=[i for i,d in enumerate(bank) if item['family'] in d.groups]
                try:
                    envelope=solve_covered(totals[None,ids,:],raw[None,:],True)
                    env={'feasible':True,'max_error_ratio':envelope['max_error_ratio'],
                       'expected_raw':envelope['expected_raw'][0].tolist(),
                       'weights':{bank[i].policy.name:float(w) for i,w in zip(ids,envelope['weights']) if w>0},
                       'hindsight_not_confirmatory':True}
                except ValueError as error:
                    if 'infeasible' not in str(error).lower():raise
                    env={'feasible':False,'reason':str(error),'hindsight_not_confirmatory':True}
                if not item['feasible']:
                    rows[key]={'target_metrics':metrics(raw),'frozen_control_feasible_in_fitting':False,'hindsight_envelope':env}
                    continue
                mixture=sum(w*values[index[name]] for name,w in item['weights'].items());mr=mixture.sum(axis=0)
                rows[key]={'target_metrics':metrics(raw),'frozen_control_feasible_in_fitting':True,'frozen_control_metrics':metrics(mr),
                  'frozen_control_to_target_resource_ratio':float(mr[1]/raw[1]),
                  'frozen_control_to_target_F_ratio':float(mr[2]/raw[2]),'frozen_control_to_target_O_ratio':float(mr[3]/raw[3]),
                  'frozen_control_M60_admissible':bool(mr[14]<=raw[14]+1e-7),
                  'frozen_control_resource_admissible':bool(mr[1]<=raw[1]+1e-7),
                  'paired_bay_intervals_target_minus_control':bootstrap_comparison(values[ti],mixture),
                  'hindsight_envelope':env}
            result[cell]=rows
            print('ANNEX CHECK '+cell+' '+json.dumps({k:round(v['hindsight_envelope']['max_error_ratio'],5) if v['hindsight_envelope']['feasible'] else 'infeasible' for k,v in rows.items()}),flush=True)
    write_json(p,{'created_on':'2026-10-25','cohorts':result,'selection_sha256':sha256(ANNEX/'selection-before-annex-check.json'),
                 'post_primary_exploratory_annex':True,'final_test_evaluated':False,'phase4_may_start':False})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('fit','check'));args=parser.parse_args()
    fit() if args.stage=='fit' else check()
