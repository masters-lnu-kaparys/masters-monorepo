"""Broad simple controls with the same maximal300-second pause as the candidate."""
import itertools
import time
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from run_phase3 import write_json
from assess_analytic_contribution import read
from run_local_risk import WORK as BASE,old_bank,WINDOWS
from local_risk_calibration_v3 import WORK as CAL
from kernels import evaluate_bundle
from simulation import AGES,BASE_ACTIONS
from budget_comparison import choose_mixture,metrics,bootstrap_comparison
from data_access import load_bundle

WORK=BASE/'wide-control'
PLAN=DOCS/'phase3-local-risk-wide-control-plan.json'


def bank():
    stages=list(itertools.product((30,45,60),(300,900),(60,90,120,180,300)));result=[]
    for free,occupied in itertools.product(stages,repeat=2):
        lookup=np.empty(48,np.int64)
        for s,params in enumerate((free,occupied)):
            early,edge,late=params
            for t in range(4):
                for a,age in enumerate((0,*AGES)):lookup[(s*4+t)*6+a]=early if age<edge else late
        result.append((f'wide_F{free[0]}_{free[1]}_{free[2]}_O{occupied[0]}_{occupied[1]}_{occupied[2]}',lookup))
    assert len(result)==900
    return result


def replay(cohort,primary,label,lock,policies):
    cell=cohort+'_'+label;path=WORK/(cell+'.npz')
    if path.exists():return np.load(path)
    d=load_bundle(('train_development' if cohort=='training256' else 'validation_development',),bay_filter=lock['cohorts'][cohort],primary_only=primary)
    reps=3 if cohort=='training256' else 10;initial,seeds=d.phases(reps)
    out=np.zeros((len(policies),len(d.bays),17),np.int64);hist=np.zeros((len(policies),301),np.int64);began=time.monotonic()
    for i,(name,lookup) in enumerate(policies):
        by,h=evaluate_bundle(d.ends,d.states,d.offsets,d.starts,d.bay_indexes,initial,seeds,1,np.array([60,60],np.int64),
          lookup,np.zeros(48,np.int64),False,True,np.zeros((len(d.bays),2,len(BASE_ACTIONS))),BASE_ACTIONS,len(d.bays))
        out[i]=by.sum(axis=1);hist[i]=h
        if (i+1)%300==0:print(f'WIDE {cell} {i+1}/900 {time.monotonic()-began:.1f}s',flush=True)
    prior,bays=old_bank(cell);np.testing.assert_array_equal(bays,d.bays);assert np.all(out[:,:,0]==prior[0,:,0])
    np.savez_compressed(path,by_bay=out,bays=d.bays,names=np.array([n for n,_ in policies]),histograms=hist)
    write_json(path.with_suffix('.json'),{'arrays_sha256':sha256(path),'bays':len(d.bays),'windows':len(d.starts),
      'repetitions':reps,'source_files':d.source_files})
    return np.load(path)


def main():
    WORK.mkdir(exist_ok=True);policies=bank();lock=read(BASE/'pre-fit-lock.json')
    pre={'created_on':'2026-10-25','plan_sha256':sha256(PLAN),'code_sha256':sha256(__file__),
      'headline_selection_sha256':sha256(CAL/'selection-before-check.json'),'known_headline_result_sha256':sha256(CAL/'results.json'),
      'new_check_cohort_opened':False,'final_test_evaluated':False}
    p=WORK/'pre-fit-lock.json'
    if p.exists():assert read(p)==pre
    else:write_json(p,pre)
    target=read(CAL/'selection-before-check.json');headline=target['headline'];selectionpath=WORK/'selection-before-check.json'
    if selectionpath.exists():selection=read(selectionpath)
    else:
        arrays=[]
        for cohort in ('training256','tuning128'):
            for primary,label in WINDOWS:arrays.append(replay(cohort,primary,label,lock,policies)['by_bay'].sum(axis=1))
        targets=np.array(target['selected'][headline]['fitting_expected_raw'])
        answer=choose_mixture(np.array(arrays),targets)
        selection={'created_on':'2026-10-25','pre_fit_lock_sha256':sha256(p),'weights':{policies[i][0]:float(w) for i,w in enumerate(answer['weights']) if w>0},
          'fitting_t':answer['max_error_ratio'],'fitting_expected_raw':answer['expected_raw'].tolist(),
          'headline':headline,'final_test_evaluated':False}
        write_json(selectionpath,selection);print('WIDE_FROZEN '+str(selection),flush=True)
    resultpath=WORK/'results.json'
    if resultpath.exists():return
    mainresult=read(CAL/'results.json');out={};names=[n for n,_ in policies]
    for cohort in ('check256','check512'):
        for primary,label in WINDOWS:
            cell=cohort+'_'+label;arr=replay(cohort,primary,label,lock,policies)
            cr=sum(w*arr['by_bay'][names.index(n)] for n,w in selection['weights'].items());raw=cr.sum(axis=0)
            targetraw=np.array(mainresult['cohorts'][cell][headline]['expected_raw'])
            envelope=choose_mixture(arr['by_bay'].sum(axis=1)[None],targetraw[None],True)
            # Reconstruct headline expected Bay counters for paired comparisons.
            old,bays=old_bank(cell);cal=np.load(CAL/(cell+'.npz'));index={n:i for i,n in enumerate(cal['names'])}
            targetby=sum(w*cal['by_bay'][index[n]] for n,w in target['selected'][headline]['weights'].items() if n!='fixed_60')
            if 'fixed_60' in target['selected'][headline]['weights']:
                from budget_comparison import definitions
                fixed=next(i for i,d in enumerate(definitions()) if d.policy.name=='fixed_60')
                targetby+=target['selected'][headline]['weights']['fixed_60']*old[fixed]
            ratios={m:float(raw[i]/targetraw[i]) for m,i in (('calls',1),('F',2),('O',3))}
            out[cell]={'expected_raw':raw.tolist(),'metrics':metrics(raw),'control_to_candidate_ratios':ratios,
              'resource_admissible':bool(raw[1]<=targetraw[1]+1e-6),'paired_candidate_minus_control':bootstrap_comparison(targetby,cr),
              'hindsight_equal_expected_budget':{'t':envelope['max_error_ratio'],
                'weights':{names[i]:float(w) for i,w in enumerate(envelope['weights']) if w>0},'not_a_frozen_policy':True}}
            write_json(WORK/'progress.json',out);print('WIDE_CHECK '+cell+' '+str(out[cell]),flush=True)
    write_json(resultpath,{'created_on':'2026-10-25','selection_sha256':sha256(selectionpath),'headline':headline,
      'cohorts':out,'final_test_evaluated':False,'new_check_cohort_opened':False,'phase4_may_start':False})


if __name__=='__main__':main()
