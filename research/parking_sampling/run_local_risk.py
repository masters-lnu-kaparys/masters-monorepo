"""Fit and freeze a local integral-risk scheduler before known-check diagnostics."""
import itertools
from pathlib import Path
import time
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from data_access import load_bundle
from run_phase3 import write_json
from assess_analytic_contribution import read
from local_risk import ACTIONS,ARMS,collect_bundle,estimates,make_tables,align_tables,evaluate_local
from budget_comparison import definitions,choose_mixture,metrics,bootstrap_comparison
from budget_coverage_annex import extra_definitions,solve_covered

WORK=ROOT/'.codex-work/parking-local-risk-20261025'
OLD=ROOT/'.codex-work/parking-budget-comparison-20261025'
PLAN=DOCS/'phase3-local-risk-plan.json'
WINDOWS=((True,'primary_7_days'),(False,'sensitivity_1_day'))


def grid():
    cfg=read(PLAN)['parameter_grid'];result=[]
    for arm,lf,lo in itertools.product(ARMS,cfg['lambda_F'],cfg['lambda_O']):
        result.append({'name':f'{arm}_F{lf}_O{lo}','arm':arm,'lambda_F':lf,'lambda_O':lo})
    return result


def prepare():
    WORK.mkdir(exist_ok=True,parents=True);(WORK/'.gitignore').write_text('*\n!.gitignore\n',encoding='utf-8')
    old=read(OLD/'pre-fit-lock.json');union=sorted(set().union(*map(set,old['cohorts'].values())))
    files=('local_risk.py','run_local_risk.py','test_local_risk.py','kernels.py','simulation.py','data_access.py',
      'budget_comparison.py','budget_coverage_annex.py')
    lock={'created_on':'2026-10-25','plan_sha256':sha256(PLAN),'cohorts':old['cohorts'],'training_bay_ids':union,
      'code_sha256':{n:sha256(ROOT/'research/parking_sampling'/n) for n in files},
      'previous_results_known':True,'new_check_cohort_opened':False,'final_test_evaluated':False,'phase4_may_start':False}
    p=WORK/'pre-fit-lock.json'
    if p.exists():assert read(p)==lock,'Locked run changed; create a new version'
    else:write_json(p,lock)
    return lock


def train(lock):
    path=WORK/'training-statistics.npz'
    if not path.exists():
        data=load_bundle(('train_development',),bay_filter=lock['training_bay_ids'],primary_only=False)
        n,cost=collect_bundle(data.ends,data.states,data.offsets,data.starts,data.bay_indexes,len(data.bays))
        np.savez_compressed(path,bays=data.bays,n=n,cost=cost)
        write_json(WORK/'training-metadata.json',{'bays':len(data.bays),'requested_ids':len(lock['training_bay_ids']),
          'windows':len(data.starts),'intervals':len(data.ends),'anchors':int(n.sum()),'source_files':data.source_files,
          'missing_training_bays':sorted(set(lock['training_bay_ids'])-set(map(int,data.bays))),
          'pre_fit_lock_sha256':sha256(WORK/'pre-fit-lock.json'),'statistics_sha256':sha256(path),
          'support_is_not_independent_trials':True,'final_test_evaluated':False})
        print('TRAIN '+str(read(WORK/'training-metadata.json')),flush=True)
    return np.load(path)


def model_tables(stats,definition,risk_cache):
    arm=definition['arm']
    if arm not in risk_cache:risk_cache[arm]=estimates(stats['n'],stats['cost'],arm)
    risk,pooled=risk_cache[arm]
    return make_tables(risk,definition['lambda_F'],definition['lambda_O']),make_tables(pooled[None],definition['lambda_F'],definition['lambda_O'])[0]


def old_bank(cell):
    base=np.load(OLD/'banks'/(cell+'.npz'));annex=np.load(OLD/'coverage-annex-v2'/(cell+'.npz'))
    np.testing.assert_array_equal(base['bays'],annex['bays'])
    return np.concatenate((base['by_bay'],annex['by_bay']),axis=0),base['bays']


def replay_fit_cell(cohort,primary,label,lock,stats,bank):
    cell=cohort+'_'+label;path=WORK/(cell+'.npz')
    if path.exists():return np.load(path)
    role='train_development' if cohort=='training256' else 'validation_development';reps=3 if cohort=='training256' else 10
    data=load_bundle((role,),bay_filter=lock['cohorts'][cohort],primary_only=primary)
    init,seeds=data.phases(reps);out=np.zeros((len(bank),len(data.bays),17),np.int64);hist=np.zeros((len(bank),301),np.int64)
    risk_cache={};missing=set();started=time.monotonic()
    for i,definition in enumerate(bank):
        tables,pooled=model_tables(stats,definition,risk_cache)
        aligned,fallback=align_tables(stats['bays'],tables,data.bays,pooled);missing.update(fallback)
        by,h=evaluate_local(data.ends,data.states,data.offsets,data.starts,data.bay_indexes,init,seeds,aligned,len(data.bays))
        out[i]=by.sum(axis=1);hist[i]=h
        if (i+1)%64==0:print(f'{cell}: {i+1}/{len(bank)} {time.monotonic()-started:.1f}s',flush=True)
    previous,bays=old_bank(cell);np.testing.assert_array_equal(bays,data.bays)
    assert np.all(out[:,:,0]==previous[0,:,0])
    np.savez_compressed(path,by_bay=out,bays=data.bays,histograms=hist,names=np.array([d['name'] for d in bank]))
    write_json(path.with_suffix('.json'),{'cohort':cohort,'windows':len(data.starts),'bays':len(data.bays),'repetitions':reps,
      'source_files':data.source_files,'fallback_bays':sorted(missing),'arrays_sha256':sha256(path)})
    return np.load(path)


def solve_control(controls,targets,strict):
    try:
        r=solve_covered(controls,targets) if strict else choose_mixture(controls,targets)
        return {'feasible':True,**{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in r.items()}}
    except ValueError as e:
        if 'infeasible' not in str(e).lower():raise
        return {'feasible':False,'reason':str(e)}


def fit(lock,stats):
    selection=WORK/'selection-before-check.json'
    if selection.exists():return read(selection)
    bank=grid();cells=[];arrays=[];old=[];files={}
    for cohort in ('training256','tuning128'):
        for primary,label in WINDOWS:
            cell=cohort+'_'+label;a=replay_fit_cell(cohort,primary,label,lock,stats,bank)
            cells.append(cell);arrays.append(a['by_bay'].sum(axis=1));old.append(old_bank(cell)[0].sum(axis=1))
            files[cell]=sha256(WORK/(cell+'.npz'))
    values=np.array(arrays);ov=np.array(old);old_defs=definitions()+extra_definitions()
    names=[d.policy.name for d in old_defs];fixed=names.index('fixed_60');refs=ov[:,fixed,:]
    selected={};risk_cache={};controls={}
    for arm in ARMS:
        indexes=[i for i,d in enumerate(bank) if d['arm']==arm]
        for criterion in ('display','original_strict'):
            eligible=[i for i in indexes if np.all(values[:,i,2:4]<=refs[:,2:4]) and
              (criterion=='display' or np.all(values[:,i,14]<=refs[:,14]))]
            def key(i):return (float(np.mean(values[2:,i,1]/refs[2:,1])),float(np.mean(values[2:,i,2:4]/refs[2:,2:4])),bank[i]['lambda_F'],bank[i]['lambda_O'])
            winner=min(eligible,key=key) if eligible else None
            definition=bank[winner] if winner is not None else None;name='fixed_60' if definition is None else definition['name']
            target=refs if winner is None else values[:,winner,:];keyname=arm+'_'+criterion
            selected[keyname]={'arm':arm,'criterion':criterion,'name':name,'bank_index':winner,'definition':definition,
              'feasible_candidates':len(eligible),'raw_by_cell':dict(zip(cells,target.tolist()))}
            if definition is not None:
                tables,pooled=model_tables(stats,definition,risk_cache);path=WORK/'models'/(name+'.npz');path.parent.mkdir(exist_ok=True)
                np.savez_compressed(path,bays=stats['bays'],tables=tables,pooled=pooled)
                selected[keyname]['model_sha256']=sha256(path)
            for family in ('state','two_stage','pooled','same_estimator_pooled','same_estimator_unshrunk'):
                own=family.startswith('same_estimator')
                if own:
                    arms=('pooled_state','pooled_clock_age') if family=='same_estimator_pooled' else ('bay_full_alpha0',)
                    ids=[i for i,d in enumerate(bank) if d['arm'] in arms];cr=values[:,ids,:];cn=[bank[i]['name'] for i in ids]
                else:
                    ids=[i for i,d in enumerate(old_defs) if family in d.groups];cr=ov[:,ids,:];cn=[names[i] for i in ids]
                answer=solve_control(cr,target,criterion=='original_strict')
                weights={cn[i]:float(w) for i,w in enumerate(answer.pop('weights',[])) if w>0}
                controls[keyname+'_'+family]={'target':keyname,'family':family,'new_model_constituents':own,'weights':weights,**answer}
    # Freeze any newly fitted control constituents, not only target models.
    byname={d['name']:d for d in bank}
    needed={s['name'] for s in selected.values() if s['name']!='fixed_60'}
    for item in controls.values():
        if item['new_model_constituents']:needed.update(item['weights'])
    model_hashes={}
    for name in sorted(needed):
        path=WORK/'models'/(name+'.npz')
        if not path.exists():
            tables,pooled=model_tables(stats,byname[name],risk_cache);np.savez_compressed(path,bays=stats['bays'],tables=tables,pooled=pooled)
        model_hashes[name]=sha256(path)
    result={'created_on':'2026-10-25','pre_fit_lock_sha256':sha256(WORK/'pre-fit-lock.json'),
      'training_statistics_sha256':sha256(WORK/'training-statistics.npz'),'fitting_cells':cells,'fitting_bank_hashes':files,
      'selected':selected,'controls':controls,'check_model_hashes':model_hashes,
      'final_test_evaluated':False,'new_check_cohort_opened':False,'phase4_may_start':False}
    write_json(selection,result)
    print('FROZEN_SELECTION '+str({k:{'policy':v['name'],'feasible':v['feasible_candidates']} for k,v in selected.items()}),flush=True)
    return result


def check(lock,selected):
    path=WORK/'check-results.json'
    if path.exists():return read(path)
    marker={'selection_sha256':sha256(WORK/'selection-before-check.json'),'model_hashes':selected['check_model_hashes'],
      'final_test_evaluated':False}
    before=WORK/'pre-check-lock.json'
    if before.exists():assert read(before)==marker
    else:write_json(before,marker)
    old_defs=definitions()+extra_definitions();old_names=[d.policy.name for d in old_defs];fixed=old_names.index('fixed_60')
    models={name:np.load(WORK/'models'/(name+'.npz')) for name in selected['check_model_hashes']}
    outcome={};started=time.monotonic()
    for cohort in ('check256','check512'):
        for primary,label in WINDOWS:
            cell=cohort+'_'+label;bankpath=WORK/(cell+'.npz')
            data=load_bundle(('validation_development',),bay_filter=lock['cohorts'][cohort],primary_only=primary)
            init,seeds=data.phases(10);prior,bays=old_bank(cell);np.testing.assert_array_equal(bays,data.bays)
            new_names=sorted(models)
            if not bankpath.exists():
                out=np.zeros((len(new_names),len(data.bays),17),np.int64);hist=np.zeros((len(new_names),301),np.int64)
                fallback={}
                for i,name in enumerate(new_names):
                    model=models[name];assert sha256(WORK/'models'/(name+'.npz'))==selected['check_model_hashes'][name]
                    tables,missing=align_tables(model['bays'],model['tables'],data.bays,model['pooled']);fallback[name]=missing
                    by,h=evaluate_local(data.ends,data.states,data.offsets,data.starts,data.bay_indexes,init,seeds,tables,len(data.bays))
                    out[i]=by.sum(axis=1);hist[i]=h
                np.savez_compressed(bankpath,by_bay=out,bays=data.bays,names=np.array(new_names),histograms=hist)
                write_json(bankpath.with_suffix('.json'),{'bays':len(data.bays),'windows':len(data.starts),'repetitions':10,
                  'source_files':data.source_files,'fallback_bays_by_model':fallback,'arrays_sha256':sha256(bankpath)})
            arr=np.load(bankpath);all_names=old_names+arr['names'].tolist();all_values=np.concatenate((prior,arr['by_bay']),axis=0)
            index={n:i for i,n in enumerate(all_names)};ref=prior[fixed].sum(axis=0);rows={}
            for key,s in selected['selected'].items():
                candidate=all_values[index[s['name']]];raw=candidate.sum(axis=0);comparisons={}
                for ck,item in selected['controls'].items():
                    if item['target']!=key:continue
                    if not item['feasible']:comparisons[item['family']]={'feasible':False};continue
                    control=sum(weight*all_values[index[name]] for name,weight in item['weights'].items());cr=control.sum(axis=0)
                    rowside={'feasible':True,'expected_raw':cr.tolist(),'metrics':metrics(cr),
                      'control_to_candidate_ratios':{'calls':float(cr[1]/raw[1]),'F':float(cr[2]/raw[2]),'O':float(cr[3]/raw[3])},
                      'resource_admissible':bool(cr[1]<=raw[1]+1e-6),'coverage_admissible':bool(cr[14]<=raw[14]+1e-6),
                      'paired_candidate_minus_control':bootstrap_comparison(candidate,control)}
                    if not item['new_model_constituents']:
                        ids=[i for i,d in enumerate(old_defs) if item['family'] in d.groups]
                        try:
                            env=solve_covered(prior[ids].sum(axis=1)[None],raw[None],True) if s['criterion']=='original_strict' else choose_mixture(prior[ids].sum(axis=1)[None],raw[None],True)
                            rowside['hindsight_equal_expected_budget']={'feasible':True,'t':env['max_error_ratio'],
                              'weights':{old_names[i]:float(w) for i,w in zip(ids,env['weights']) if w>0},
                              'not_a_frozen_policy':True}
                        except ValueError as e:
                            if 'infeasible' not in str(e).lower():raise
                            rowside['hindsight_equal_expected_budget']={'feasible':False}
                    comparisons[item['family']]=rowside
                rows[key]={'name':s['name'],'arm':s['arm'],'criterion':s['criterion'],'raw':raw.tolist(),'metrics':metrics(raw),
                  'reference_raw':ref.tolist(),'reference_metrics':metrics(ref),'calls_reduction_percent':float(100*(1-raw[1]/ref[1])),
                  'display_passes':bool(np.all(raw[2:4]<=ref[2:4])),'original_strict_passes':bool(np.all(raw[[2,3,14]]<=ref[[2,3,14]])),
                  'controls':comparisons}
            outcome[cell]=rows
            write_json(WORK/'check-progress.json',outcome)
            print('CHECK '+cell+' '+str({k:(round(v['calls_reduction_percent'],1),v['display_passes'],v['raw'][14]) for k,v in rows.items()})+
              f' {time.monotonic()-started:.1f}s',flush=True)
    gates={}
    for key,s in selected['selected'].items():
        rows=[v[key] for v in outcome.values()];display=all(v['display_passes'] and v['calls_reduction_percent']>=10 for v in rows)
        strong={}
        for family in ('state','two_stage','pooled','same_estimator_pooled','same_estimator_unshrunk'):
            passes=[]
            for row in rows:
                c=row['controls'][family]
                passes.append(c.get('feasible',False) and c['resource_admissible'] and
                  c['control_to_candidate_ratios']['F']>=1 and c['control_to_candidate_ratios']['O']>=1 and
                  max(c['control_to_candidate_ratios']['F'],c['control_to_candidate_ratios']['O'])>=1/.95)
            strong[family]={'cells_with_5percent_gain_at_admissible_budget':sum(passes),'at_least_3_of_4':sum(passes)>=3}
        gates[key]={'display_usefulness_passes_all4':display,'original_strict_usefulness_passes_all4':display and all(v['original_strict_passes'] for v in rows),
          'minimum_calls_reduction_percent':min(v['calls_reduction_percent'] for v in rows),'strong_controls':strong}
    result={'created_on':'2026-10-25','selection_sha256':sha256(WORK/'selection-before-check.json'),'cohorts':outcome,'gates':gates,
      'all_check_results_are_development_diagnostics':True,'new_check_cohort_opened':False,'final_test_evaluated':False,'phase4_may_start':False}
    write_json(path,result);print('GATES '+str({k:(v['display_usefulness_passes_all4'],round(v['minimum_calls_reduction_percent'],1),v['strong_controls']['pooled']) for k,v in gates.items()}),flush=True)
    return result


if __name__=='__main__':
    lock=prepare();stats=train(lock);selection=fit(lock,stats);check(lock,selection)
