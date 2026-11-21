"""Lock training, fit candidates, tune on development data; never open final test."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import time
import numpy as np
from prepare_data import ROOT, DOCS, sha256
from data_access import DEFAULT_WORK, load_bundle, tuning_bays
from training import fit_models
from policies import policy_grid, s2_cdfs
from kernels import evaluate_bundle
from simulation import BASE_ACTIONS, summarize
from markov_baseline import verify_published_examples

WORK=ROOT/'.codex-work/parking-research-phase3-20261018'
TRAINING_CODE=('simulation.py','kernels.py','data_access.py','training.py','policies.py','markov_baseline.py')

def write_json(path, value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def numeric_key(policy):
    return tuple(float(v) for v in (policy.parameters or {}).values() if isinstance(v,(int,float)))

def strict_select(policies, totals, family):
    """Use integer paired sums: every method has exactly the same exposure."""
    reference=totals['fixed_60']
    candidates=[p for p in policies if p.family==family or (family=='state' and p.family=='fixed')]
    eligible=[p for p in candidates if all(totals[p.name][k]<=reference[k] for k in (2,3,14))]
    if not eligible:
        return {'policy':'fixed_60','fallback':True,'feasible_candidates':0}
    chosen=min(eligible,key=lambda p:(int(totals[p.name][1]),int(totals[p.name][2]),int(totals[p.name][3]),numeric_key(p)))
    return {'policy':chosen.name,'fallback':False,'feasible_candidates':len(eligible)}

def resource_select(policies,totals,family,budget):
    """Secondary comparison, with finite-window overhead paired to a fixed rule.

    S2 retains its own nominal LP budget, reporting realized frequency explicitly.
    The original literal nominal-cap selection is retained below for audit.
    """
    if family=='S2':
        name=f'S2_{budget}'
        return {'policy':name,'feasible_candidates':1,'selection':'nominal_S2_model_budget',
          'realized_exceeds_nominal_budget':bool(totals[name][1]*86400>budget*totals[name][0])}
    reference=totals[f'fixed_{86400//budget}']
    candidates=[p for p in policies if p.family==family or (family=='state' and p.family=='fixed')]
    eligible=[p for p in candidates if totals[p.name][1]<=reference[1]]
    if not eligible:return {'policy':None,'feasible_candidates':0}
    chosen=min(eligible,key=lambda p:(int(totals[p.name][2]),int(totals[p.name][3]),int(totals[p.name][14]),int(totals[p.name][1]),numeric_key(p)))
    return {'policy':chosen.name,'feasible_candidates':len(eligible),'selection':'empirical_matched_fixed_budget',
      'reference_policy':f'fixed_{86400//budget}','empirical_cap_checks_per_bay_day':float(reference[1]*86400/reference[0])}

def original_resource_select(policies,totals,family,budget):
    candidates=[p for p in policies if p.family==family or (family=='state' and p.family=='fixed')]
    eligible=[p for p in candidates if totals[p.name][1]*86400<=budget*totals[p.name][0]]
    if not eligible:return {'policy':None,'feasible_candidates':0}
    chosen=min(eligible,key=lambda p:(int(totals[p.name][2]),int(totals[p.name][3]),int(totals[p.name][14]),int(totals[p.name][1]),numeric_key(p)))
    return {'policy':chosen.name,'feasible_candidates':len(eligible)}

def prepare_lock(work,source_work):
    work.mkdir(parents=True,exist_ok=True);(work/'.gitignore').write_text('*\n!.gitignore\n',encoding='utf-8')
    config_path=DOCS/'phase3-methods.json';config=json.loads(config_path.read_text(encoding='utf-8'))
    lock_path=work/'training-code-lock.json'
    hashes={name:sha256(ROOT/'research/parking_sampling'/name) for name in TRAINING_CODE}
    cohort=[int(b) for b in tuning_bays(source_work,config['tuning_bay_count'])]
    if lock_path.exists():
        lock=json.loads(lock_path.read_text(encoding='utf-8'))
        if (lock['training_code_sha256']!=hashes or lock['config_sha256']!=sha256(config_path) or lock['tuning_bays']!=cohort
            or lock['phase2_data_manifest_sha256']!=sha256(source_work/'prepared/data-manifest.json')
            or lock['phase2_lock_sha256']!=sha256(DOCS/'phase2-data-lock.json')):
            raise RuntimeError('Existing pre-outcome lock differs; do not silently overwrite it')
    else:
        write_json(lock_path,{'created_at_utc':datetime.now(timezone.utc).isoformat(),
          'training_code_sha256':hashes,'config_sha256':sha256(config_path),'tuning_bays':cohort,
          'phase2_data_manifest_sha256':sha256(source_work/'prepared/data-manifest.json'),
          'phase2_lock_sha256':sha256(DOCS/'phase2-data-lock.json'),
          'resource_selection_order':['F','O','M60','calls','numeric_parameters'],
          'reserved_training_opened_before_this_lock':False,'validation_policy_metrics_seen_before_this_lock':False,
          'prior_exploratory_exposure':'phase1-evidence.json; original pilot only',
          'final_test_evaluated':False})
    return config,lock_path,cohort

def run(work=WORK,source_work=DEFAULT_WORK,train_only=False):
    config,lock,cohort=prepare_lock(work,source_work)
    models_dir=work/'models';results_dir=work/'candidate-results';results_dir.mkdir(exist_ok=True)
    if not (models_dir/'training-metadata.json').exists():
        fit_models(models_dir,lock,work=source_work,cadences=config['training_cadences_seconds'],anchor_period=config['training_anchor_period_seconds'])
    published=verify_published_examples();write_json(work/'s2-published-example-verification.json',published)
    if not published['all_required_checks_passed']:raise RuntimeError('Literature reconstruction failed')
    original=ROOT/'research/parking_sampling/fixtures/C0-archived-pilot.npz'
    legacy=models_dir/'C0-archived-pilot.npz'
    if not legacy.exists():shutil.copy2(original,legacy)
    if sha256(original)!=sha256(legacy):raise ValueError('Archived control changed')
    if train_only:return
    models={key:dict(np.load(models_dir/f'risk-{key}.npz')) for key in ('full','without_time','without_run')}
    policies=policy_grid(models,config,dict(np.load(legacy)))
    data=load_bundle(('validation_development',),work=source_work,bay_filter=cohort)
    initial,seeds=data.phases(config['tuning_phase_repetitions'])
    cache_context=hashlib.sha256(b''.join([json.dumps(data.source_files,sort_keys=True).encode(),
      data.bays.tobytes(),initial.tobytes(),seeds.tobytes(),sha256(ROOT/'research/parking_sampling/kernels.py').encode()])).hexdigest()
    write_json(work/'tuning-cohort.json',{'bays':data.bays.tolist(),'windows':len(data.starts),
      'window_ids':list(data.window_ids),'source_sha256':data.source_files,'repetitions':config['tuning_phase_repetitions'],
      'initial_offsets_sha256':hashlib.sha256(initial.tobytes()).hexdigest(),
      'note':'Episode counts are episode-phase observations; ratios pool ten common start phases.'})
    counts=np.load(models_dir/'markov-counts.npz');s2={};notes={}
    for budget in config['s2_budgets_samples_per_bay_day']:
        s2[budget],notes[str(budget)]=s2_cdfs(counts['bays'],counts['counts'],data.bays,budget)
    write_json(work/'s2-parking-adaptation.json',notes)
    dummy=np.zeros((len(data.bays),2,len(BASE_ACTIONS)));summaries={};totals={};equivalent={};started=time.monotonic()
    records=[]
    for index,p in enumerate(policies):
        cdf=s2[p.parameters['budget']] if p.kind==2 else dummy
        fingerprint=hashlib.sha256(b''.join([str((p.kind,p.use_time,p.use_run)).encode(),p.delays.tobytes(),p.lookup.tobytes(),p.fallback.tobytes(),cdf.tobytes()])).hexdigest()
        cache_key=hashlib.sha256((cache_context+fingerprint).encode()).hexdigest()
        path=results_dir/f'{cache_key}.npz'
        if not path.exists():
            values,hist=evaluate_bundle(data.ends,data.states,data.offsets,data.starts,data.bay_indexes,initial,seeds,
              p.kind,p.delays,p.lookup,p.fallback,p.use_time,p.use_run,cdf,BASE_ACTIONS,len(data.bays))
            np.savez_compressed(path,by_bay_phase=values,delay_histogram=hist,bays=data.bays)
        result=np.load(path);raw=result['by_bay_phase'].sum(axis=(0,1));hist=result['delay_histogram']
        totals[p.name]=raw;summaries[p.name]=summarize(raw,hist)
        equivalent.setdefault(fingerprint,[]).append(p.name)
        records.append({'name':p.name,'family':p.family,'parameters':p.parameters,'runtime_fingerprint':fingerprint,
          'result_path':path.relative_to(ROOT).as_posix(),'metrics':summaries[p.name]})
        if index%25==0 or index+1==len(policies):
            print(f'tune {index+1}/{len(policies)}, unique runtimes={len(equivalent)}, elapsed={time.monotonic()-started:.1f}s',flush=True)
    families=['fixed','state','S2','C0','C1','C2','C2_no_duration','C2_no_time','C2_no_run']
    selected={family:strict_select(policies,totals,family) for family in families}
    resources={str(b):{f:resource_select(policies,totals,f,b) for f in families} for b in config['s2_budgets_samples_per_bay_day']}
    original_resources={str(b):{f:original_resource_select(policies,totals,f,b) for f in families} for b in config['s2_budgets_samples_per_bay_day']}
    reference=totals['fixed_60']
    for family,item in selected.items():
        value=totals[item['policy']]
        item['measurement_reduction_percent_vs_fixed60']=float(100*(1-value[1]/reference[1]))
        item['metrics']=summaries[item['policy']]
    write_json(work/'tuning-results.json',{'scope':'validation_tuning_not_final_test','candidates':records,
      'strict_selection':selected,'resource_selection':resources,'resource_selection_initial_literal_nominal_cap':original_resources,
      'resource_selection_amendment':'phase3-resource-selection.json','unique_runtime_policies':len(equivalent),
      'runtime_equivalence':equivalent,'elapsed_evaluation_seconds':time.monotonic()-started,
      'shared_exposure_seconds_all_candidates':bool(all(v[0]==reference[0] for v in totals.values())),
      'final_test_opened':False,'physical_accuracy_evaluated':False,'battery_energy_measured':False})
    with (work/'tuning-summary.csv').open('w',newline='',encoding='utf-8-sig') as file:
        writer=csv.writer(file);writer.writerow(['policy','family','checks_per_bay_day','false_free_seconds_per_bay_day','false_occupied_seconds_per_bay_day','miss_fraction_0','miss_fraction_30','miss_fraction_60','miss_fraction_120','miss_fraction_300'])
        for p in policies:
            s=summaries[p.name];writer.writerow([p.name,p.family,s['samples_per_bay_day'],s['false_free_seconds_per_bay_day'],s['false_occupied_seconds_per_bay_day'],*[s['vacancy_duration_profiles'][str(t)]['missed_fraction'] for t in (0,30,60,120,300)]])
    # Self-contained policy definitions and random tables for later frozen test.
    chosen_names=sorted(set([i['policy'] for i in selected.values()]+[i['policy'] for values in resources.values() for i in values.values() if i['policy']]+[f'fixed_{x}' for x in (5,30,60,120,300)]))
    frozen=[];frozen_dir=work/'frozen-policies';frozen_dir.mkdir(exist_ok=True)
    for p in policies:
        if p.name not in chosen_names:continue
        np.savez_compressed(frozen_dir/f'{p.name}.npz',kind=p.kind,delays=p.delays,lookup=p.lookup,fallback=p.fallback,use_time=p.use_time,use_run=p.use_run)
        frozen.append({'name':p.name,'family':p.family,'parameters':p.parameters,'table_path':(frozen_dir/f'{p.name}.npz').relative_to(ROOT).as_posix()})
    write_json(work/'frozen-policy-definitions.json',{'policies':frozen,'strict_selection':{f:i['policy'] for f,i in selected.items()},'resource_selection':resources,
      'S2_test_rule':'Recompute CDFs for test BayIds using unchanged Jan-Jun training counts and identical solver; no test-state fit.'})
    paths=[*models_dir.glob('*.npz'),models_dir/'training-metadata.json',lock,work/'frozen-policy-definitions.json',*frozen_dir.glob('*.npz'),work/'tuning-results.json',work/'tuning-summary.csv',work/'tuning-cohort.json',work/'s2-published-example-verification.json',work/'s2-parking-adaptation.json',DOCS/'phase3-methods.json',DOCS/'phase3-resource-selection.json',original]
    code_paths=[ROOT/'research/parking_sampling'/n for n in (*TRAINING_CODE,'run_phase3.py','test_methods.py')]
    write_json(DOCS/'phase3-method-lock.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),
      'scope':'methods_frozen_after_validation_before_final_test','files':{p.relative_to(ROOT).as_posix():sha256(p) for p in paths+code_paths},
      'strict_selection':selected,'resource_selection':resources,'candidate_count':len(policies),'unique_runtime_policies':len(equivalent),
      'final_test_evaluated':False,'source_data':'phase2-data-lock.json','original_protocol':'protocol.json'})
    print(json.dumps({f:{'policy':v['policy'],'reduction_percent':v['measurement_reduction_percent_vs_fixed60']} for f,v in selected.items()},indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--work',type=Path,default=WORK);parser.add_argument('--source-work',type=Path,default=DEFAULT_WORK);parser.add_argument('--train-only',action='store_true')
    args=parser.parse_args();run(args.work,args.source_work,args.train_only)
