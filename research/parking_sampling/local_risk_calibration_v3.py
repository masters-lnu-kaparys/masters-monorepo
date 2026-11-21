"""Constrained whole-policy calibration, with expected and realized deployment costs."""
import hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from prepare_data import ROOT,DOCS,sha256
from run_phase3 import write_json
from assess_analytic_contribution import read
from run_local_risk import WORK as BASE,grid,old_bank,model_tables,solve_control,WINDOWS
from local_risk import ARMS,align_tables,evaluate_local
from data_access import load_bundle
from budget_comparison import definitions,metrics,bootstrap_comparison,choose_mixture
from budget_coverage_annex import extra_definitions,solve_covered

WORK=BASE/'calibration-v3'
PLAN=DOCS/'phase3-local-risk-calibration-v3-plan.json'


def calibrate(raw,reference,gamma=.9,strict=False):
    raw=np.asarray(raw,dtype=float);ref=np.asarray(reference,dtype=float)
    if raw.ndim!=3 or raw.shape[0]!=4 or raw.shape[2]!=17 or ref.shape!=(4,17):raise ValueError('Four aligned fitting cells required')
    if not 0<gamma<=1 or not np.allclose(raw[:,:,0],ref[:,None,0],rtol=0,atol=0):raise ValueError('Invalid gamma or exposure')
    if np.any(raw<0) or np.any(ref[:,[0,1,2,3]]<=0):raise ValueError('Invalid counters')
    k=raw.shape[1];objective=(raw[2:,:,1]/ref[2:,None,1]).mean(axis=0);ub=[];limits=[]
    for c in range(4):
        for m in (2,3):ub.append(raw[c,:,m]/ref[c,m]);limits.append(gamma)
        if strict:ub.append(raw[c,:,14]/max(1,ref[c,14]));limits.append(ref[c,14]/max(1,ref[c,14]))
    fit=linprog(objective,A_ub=np.array(ub),b_ub=np.array(limits),A_eq=np.ones((1,k)),b_eq=[1.],bounds=(0,None),method='highs')
    if not fit.success:raise ValueError('Calibration LP infeasible: '+fit.message)
    weights=np.maximum(fit.x,0);weights[weights<1e-12]=0;weights/=weights.sum();expected=np.einsum('p,cpj->cj',weights,raw)
    # Exposure is identical for every component; avoid roundoff of this invariant.
    expected[:,0]=ref[:,0]
    assert np.all(expected[:,2:4]/ref[:,2:4]<=gamma+1e-7)
    if strict:assert np.all(expected[:,14]<=ref[:,14]+1e-7)
    return {'weights':weights,'expected_raw':expected,'fitting_calls_objective':float(weights@objective)}


def realized_by_bay(values,bays,names,weights,seed=20261025):
    ordered=sorted(weights);cdf=np.cumsum([weights[n] for n in ordered]);cdf[-1]=1.;index={n:i for i,n in enumerate(names)}
    result=np.empty_like(values[0]);chosen=[]
    for i,bay in enumerate(bays):
        u=int.from_bytes(hashlib.sha256(f'local-risk-allocation:{seed}:{int(bay)}'.encode()).digest()[:8],'little')/2**64
        j=min(int(np.searchsorted(cdf,u,side='right')),len(ordered)-1);name=ordered[j]
        result[i]=values[index[name],i];chosen.append(name)
    return result,chosen


def prepare():
    WORK.mkdir(exist_ok=True);(WORK/'models').mkdir(exist_ok=True)
    code=('local_risk_calibration_v3.py','test_local_risk_calibration.py','test_local_risk_calibration_v3.py','local_risk.py','run_local_risk.py','data_access.py','simulation.py')
    lock={'created_on':'2026-10-25','plan_sha256':sha256(PLAN),'source_sha256':{n:sha256(ROOT/'research/parking_sampling'/n) for n in code},
      'base_result_sha256':sha256(BASE/'check-results.json'),'base_selection_sha256':sha256(BASE/'selection-before-check.json'),
      'all_base_results_known':True,'final_test_evaluated':False,'phase4_may_start':False}
    p=WORK/'pre-fit-lock.json'
    if p.exists():assert read(p)==lock
    else:write_json(p,lock)
    return read(BASE/'pre-fit-lock.json')


def fit():
    path=WORK/'selection-before-check.json'
    if path.exists():return read(path)
    base=read(BASE/'selection-before-check.json');bank=grid();old_defs=definitions()+extra_definitions();old_names=[d.policy.name for d in old_defs]
    cells=base['fitting_cells'];old=np.array([old_bank(c)[0].sum(axis=1) for c in cells]);fixed=old_names.index('fixed_60');refs=old[:,fixed,:]
    values=np.array([np.load(BASE/(c+'.npz'))['by_bay'].sum(axis=1) for c in cells]);values=np.concatenate((values,refs[:,None,:]),axis=1)
    names=[d['name'] for d in bank]+['fixed_60'];selected={};controls={}
    for arm in ARMS:
        ids=[i for i,d in enumerate(bank) if d['arm']==arm]+[len(bank)]
        for criterion,gamma,strict in (('display_guarded',.9,False),('original_strict',1.,True)):
            answer=calibrate(values[:,ids,:],refs,gamma,strict);weights={names[i]:float(w) for i,w in zip(ids,answer['weights']) if w>0};key=arm+'_'+criterion
            selected[key]={'arm':arm,'criterion':criterion,'gamma':gamma,'weights':weights,
              'fitting_calls_objective':answer['fitting_calls_objective'],'fitting_expected_raw':answer['expected_raw'].tolist()}
            target=answer['expected_raw']
            for family in ('state','two_stage','pooled','same_estimator_pooled','same_estimator_bay_state','same_estimator_unshrunk'):
                own=family.startswith('same_estimator')
                if own:
                    armset={'same_estimator_pooled':('pooled_state','pooled_clock_age'),'same_estimator_bay_state':('bay_state_alpha50',),
                      'same_estimator_unshrunk':('bay_full_alpha0',)}[family]
                    ii=[i for i,d in enumerate(bank) if d['arm'] in armset]+[len(bank)];cr=values[:,ii,:];cn=[names[i] for i in ii]
                else:ii=[i for i,d in enumerate(old_defs) if family in d.groups];cr=old[:,ii,:];cn=[old_names[i] for i in ii]
                r=solve_control(cr,target,strict);cw={cn[i]:float(w) for i,w in enumerate(r.pop('weights',[])) if w>0}
                controls[key+'_'+family]={'target':key,'family':family,'new_model_constituents':own,'weights':cw,**r}
    headline=min(('bay_full_alpha50_display_guarded','bay_full_alpha500_display_guarded'),
      key=lambda k:(selected[k]['fitting_calls_objective'],0 if 'alpha50_' in k else 1))
    needed=set()
    for r in selected.values():needed.update(r['weights'])
    for r in controls.values():
        if r['new_model_constituents']:needed.update(r['weights'])
    needed.discard('fixed_60');stats=np.load(BASE/'training-statistics.npz');cache={};byname={d['name']:d for d in bank};hashes={}
    for name in sorted(needed):
        tables,pooled=model_tables(stats,byname[name],cache);p=WORK/'models'/(name+'.npz');np.savez_compressed(p,bays=stats['bays'],tables=tables,pooled=pooled);hashes[name]=sha256(p)
    result={'created_on':'2026-10-25','pre_fit_lock_sha256':sha256(WORK/'pre-fit-lock.json'),'fitting_cells':cells,
      'selected':selected,'controls':controls,'headline':headline,'check_model_hashes':hashes,
      'old_check_outcomes_known':True,'new_constituent_check_replays_started':False,'final_test_evaluated':False}
    write_json(path,result);print('CALIBRATION_FROZEN '+headline+' '+str({k:round(v['fitting_calls_objective'],3) for k,v in selected.items()}),flush=True)
    return result


def check(lock,selection):
    path=WORK/'results.json'
    if path.exists():return read(path)
    p=WORK/'pre-check-lock.json';marker={'selection_sha256':sha256(WORK/'selection-before-check.json'),'final_test_evaluated':False}
    if p.exists():assert read(p)==marker
    else:write_json(p,marker)
    old_defs=definitions()+extra_definitions();old_names=[d.policy.name for d in old_defs];outcome={};modelnames=sorted(selection['check_model_hashes'])
    for cohort in ('check256','check512'):
        for primary,label in WINDOWS:
            cell=cohort+'_'+label;data=load_bundle(('validation_development',),bay_filter=lock['cohorts'][cohort],primary_only=primary)
            old,bays=old_bank(cell);np.testing.assert_array_equal(bays,data.bays);base=np.load(BASE/(cell+'.npz'));baseindex={n:i for i,n in enumerate(base['names'])}
            bankpath=WORK/(cell+'.npz');reuse=[]
            if not bankpath.exists():
                initial,seeds=data.phases(10);out=np.zeros((len(modelnames),len(data.bays),17),np.int64)
                for i,name in enumerate(modelnames):
                    if name in baseindex:out[i]=base['by_bay'][baseindex[name]];reuse.append(name);continue
                    p=WORK/'models'/(name+'.npz');assert sha256(p)==selection['check_model_hashes'][name];m=np.load(p)
                    tables,missing=align_tables(m['bays'],m['tables'],data.bays,m['pooled'])
                    by,h=evaluate_local(data.ends,data.states,data.offsets,data.starts,data.bay_indexes,initial,seeds,tables,len(data.bays));out[i]=by.sum(axis=1)
                np.savez_compressed(bankpath,by_bay=out,bays=data.bays,names=np.array(modelnames))
                write_json(bankpath.with_suffix('.json'),{'arrays_sha256':sha256(bankpath),'reused_primary_models':reuse,
                  'windows':len(data.starts),'bays':len(data.bays),'source_files':data.source_files})
            arr=np.load(bankpath);names=old_names+arr['names'].tolist();values=np.concatenate((old,arr['by_bay']),axis=0);index={n:i for i,n in enumerate(names)}
            refby=old[old_names.index('fixed_60')];ref=refby.sum(axis=0);rows={}
            for key,s in selection['selected'].items():
                target=sum(w*values[index[n]] for n,w in s['weights'].items())
                target[:,0]=refby[:,0]
                raw=target.sum(axis=0)
                realized,allocation=realized_by_bay(values,data.bays,names,s['weights']);rr=realized.sum(axis=0)
                seeds=[]
                for seed in range(20261025,20261035):
                    allocated,_=realized_by_bay(values,data.bays,names,s['weights'],seed);r=allocated.sum(axis=0)
                    seeds.append({'seed':seed,'raw':r.tolist(),'calls_reduction_percent':float(100*(1-r[1]/ref[1])),
                      'display_passes':bool(np.all(r[2:4]<=ref[2:4]))})
                comparisons={}
                for c in selection['controls'].values():
                    if c['target']!=key:continue
                    if not c['feasible']:comparisons[c['family']]={'feasible':False};continue
                    control=sum(w*values[index[n]] for n,w in c['weights'].items());cr=control.sum(axis=0);ratios={n:float(cr[i]/raw[i]) for n,i in (('calls',1),('F',2),('O',3))}
                    record={'feasible':True,'expected_raw':cr.tolist(),'metrics':metrics(cr),'control_to_candidate_ratios':ratios,
                      'resource_admissible':bool(cr[1]<=raw[1]+1e-6),'coverage_admissible':bool(cr[14]<=raw[14]+1e-6),
                      'candidate_5percent_gain_at_admitted_budget':bool(cr[1]<=raw[1]+1e-6 and cr[2]>=raw[2] and cr[3]>=raw[3] and max(ratios['F'],ratios['O'])>=1/.95),
                      'paired_expected_candidate_minus_control':bootstrap_comparison(target,control)}
                    if not c['new_model_constituents']:
                        ids=[i for i,d in enumerate(old_defs) if c['family'] in d.groups]
                        try:
                            env=solve_covered(old[ids].sum(axis=1)[None],raw[None],True) if s['criterion']=='original_strict' else choose_mixture(old[ids].sum(axis=1)[None],raw[None],True)
                            record['hindsight_equal_expected_budget']={'feasible':True,'t':env['max_error_ratio'],'not_frozen_policy':True}
                        except ValueError as e:
                            if 'infeasible' not in str(e).lower():raise
                            record['hindsight_equal_expected_budget']={'feasible':False}
                    comparisons[c['family']]=record
                rows[key]={'arm':s['arm'],'criterion':s['criterion'],'expected_raw':raw.tolist(),'expected_metrics':metrics(raw),
                  'expected_calls_reduction_percent':float(100*(1-raw[1]/ref[1])),'expected_display_passes':bool(np.all(raw[2:4]<=ref[2:4])),
                  'primary_raw':rr.tolist(),'primary_metrics':metrics(rr),'primary_calls_reduction_percent':float(100*(1-rr[1]/ref[1])),
                  'primary_display_passes':bool(np.all(rr[2:4]<=ref[2:4])),'primary_allocation':allocation,'allocation_seeds':seeds,
                  'reference_raw':ref.tolist(),'reference_metrics':metrics(ref),'controls':comparisons,
                  'paired_expected_minus_fixed60':bootstrap_comparison(target,refby),'paired_primary_minus_fixed60':bootstrap_comparison(realized,refby)}
            outcome[cell]=rows;write_json(WORK/'progress.json',outcome)
            h=rows[selection['headline']];print('CALIBRATION_CHECK '+cell+' '+str((h['expected_calls_reduction_percent'],h['primary_calls_reduction_percent'],h['expected_display_passes'],h['primary_display_passes'])),flush=True)
    gates={}
    for key in selection['selected']:
        rows=[v[key] for v in outcome.values()]
        gates[key]={'expected_usefulness_all4':all(r['expected_display_passes'] and r['expected_calls_reduction_percent']>=10 for r in rows),
          'primary_usefulness_all4':all(r['primary_display_passes'] and r['primary_calls_reduction_percent']>=10 for r in rows),
          'expected_M60_zero_all4':all(r['expected_raw'][14]<=1e-7 for r in rows),'primary_M60_zero_all4':all(r['primary_raw'][14]==0 for r in rows),
          'control_support_cells':{f:sum(r['controls'][f].get('candidate_5percent_gain_at_admitted_budget',False) for r in rows)
             for f in ('state','two_stage','pooled','same_estimator_pooled','same_estimator_bay_state','same_estimator_unshrunk')}}
    result={'created_on':'2026-10-25','selection_sha256':sha256(WORK/'selection-before-check.json'),'headline':selection['headline'],
      'cohorts':outcome,'gates':gates,'new_check_cohort_opened':False,'final_test_evaluated':False,'phase4_may_start':False}
    write_json(path,result);print('CALIBRATION_GATES '+str(gates[selection['headline']]),flush=True)
    return result


if __name__=='__main__':
    lock=prepare();selected=fit();check(lock,selected)
