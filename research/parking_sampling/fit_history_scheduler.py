"""Prelocked C5 construction experiment, restricted to existing development data."""
import json
import time
from pathlib import Path
import numpy as np
from prepare_data import ROOT, DOCS, sha256
from data_access import load_bundle
from refine_policy import WORK as C3_WORK, feasible
from history_scheduler import HistorySchedule, calibrate_age, evaluate
from simulation import summarize
from run_phase3 import write_json

WORK = ROOT/'.codex-work/parking-history-scheduler-20261025'
PLAN = DOCS/'phase3-history-scheduler-plan.json'
LABELS = ((True, 'primary_7_days'), (False, 'sensitivity_1_day'))


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def candidate_definitions(calibration, config):
    definitions = {}
    for g in config['calibration']['long_pauses_seconds']:
        for a in sorted(set(config['candidate_family']['age_grid_seconds']+[calibration[str(g)]['required_age_seconds']])):
            for shape in ('C3_shape', 'simple_shape'):
                s = HistorySchedule(shape, int(g), int(a))
                definitions[s.name] = s
    for s in (HistorySchedule('fixed60',60,300), HistorySchedule('C3_shape',72,900)):
        definitions[s.name] = s
    return definitions


def selection_key(row, reference):
    def ratios(index):
        return sum(row['cells']['tuning_'+label]['raw'][index]/max(1,reference['cells']['tuning_'+label]['raw'][index])
                   for _,label in LABELS)/2
    return (ratios(1), ratios(2), ratios(3), row['long_pause'], row['age_threshold'], row['name'])


def select_rows(rows, reference):
    selected = {}
    for arm in ('unrestricted', 'history_guard'):
        for shape in ('pooled', 'C3_shape', 'simple_shape'):
            eligible = [r for r in rows if r['search_candidate'] and r['quality_passes_all_cells']
                        and (shape == 'pooled' or r['shape'] == shape)
                        and (arm == 'unrestricted' or r['history_guard_admissible'])]
            winner = min(eligible, key=lambda r: selection_key(r,reference)) if eligible else reference
            selected[arm+'_'+shape] = winner['name']
    return selected


def main():
    config = read(PLAN)
    old = read(C3_WORK/'pre-fit-lock.json')
    WORK.mkdir(parents=True,exist_ok=True)
    (WORK/'.gitignore').write_text('*\n!.gitignore\n',encoding='utf-8')
    code_names = ('history_scheduler.py','fit_history_scheduler.py','test_history_scheduler.py',
                  'history_certificate.py','simulation.py','data_access.py')
    lock = {'created_on':'2026-10-25','plan_sha256':sha256(PLAN),
            'code_sha256':{n:sha256(ROOT/'research/parking_sampling'/n) for n in code_names},
            'training_bays':old['training_bays'],'tuning_bays':old['tuning_bays'],
            'prior_development_results_known':True,'new_check_bays_opened':False,
            'final_test_evaluated':False,'phase4_may_start':False}
    lock_path = WORK/'pre-fit-lock.json'
    if lock_path.exists() and read(lock_path) != lock:
        raise ValueError('Frozen pre-fit lock changed; use an explicitly versioned experiment instead')
    write_json(lock_path,lock)
    calibration_path = WORK/'calibration.json'
    if not calibration_path.exists():
        data = load_bundle(('train_development',),bay_filter=old['training_bays'],primary_only=False)
        calibration = {str(g):calibrate_age(data,g) for g in config['calibration']['long_pauses_seconds']}
        write_json(calibration_path,{'source_files':data.source_files,'bays':len(data.bays),
                    'windows':len(data.starts),'calibration':calibration,'final_test_evaluated':False})
        print('CALIBRATION '+json.dumps({k:{n:v for n,v in c.items() if n!='pairs'} for k,c in calibration.items()}),flush=True)
        del data
    calibration = read(calibration_path)['calibration']
    definitions = candidate_definitions(calibration,config)
    candidates = []
    for s in definitions.values():
        c = calibration.get(str(s.long_pause))
        bound = sum(p['critical_age_seconds']>s.age_threshold for p in c['pairs']) if c else None
        candidates.append({'name':s.name,'shape':s.shape,'long_pause':s.long_pause,'age_threshold':s.age_threshold,
             'training_history_bound':bound,'history_guard_admissible':c is not None and bound == 0,
             'search_candidate':s.shape!='fixed60' and s.long_pause in config['calibration']['long_pauses_seconds'],
             'cells':{}})
    frozen = {'calibration_sha256':sha256(calibration_path),'candidates':[{k:v for k,v in r.items() if k!='cells'} for r in candidates],
              'pre_fit_lock_sha256':sha256(lock_path),'final_test_evaluated':False}
    candidate_path = WORK/'candidate-lock-before-replay.json'
    if candidate_path.exists() and read(candidate_path)!=frozen: raise ValueError('Candidate lock changed')
    write_json(candidate_path,frozen)
    start_time = time.monotonic()
    for role,cohort,repetitions in (('train_development','training',3),('validation_development','tuning',10)):
        for primary,label in LABELS:
            d = load_bundle((role,),bay_filter=old['training_bays' if cohort=='training' else 'tuning_bays'],primary_only=primary)
            folder = WORK/(cohort+'_'+label)
            folder.mkdir(exist_ok=True)
            for index,row in enumerate(candidates):
                path = folder/(row['name']+'.npz')
                if not path.exists():
                    by,h = evaluate(d,definitions[row['name']],repetitions)
                    np.savez_compressed(path,by_bay_phase=by,delay_histogram=h,bays=d.bays)
                arrays = np.load(path)
                raw = arrays['by_bay_phase'].sum(axis=(0,1))
                row['cells'][cohort+'_'+label] = {'raw':raw.tolist(),'metrics':summarize(raw,arrays['delay_histogram']),
                     'bays':len(d.bays),'windows':len(d.starts),'repetitions':repetitions,'source_files':d.source_files}
                if (index+1)%10 == 0:
                    print(f'{cohort}_{label} {index+1}/{len(candidates)}, {time.monotonic()-start_time:.1f}s',flush=True)
            del d
            write_json(WORK/'replay-progress.json',{'candidates':candidates,'final_test_evaluated':False})
    reference = next(r for r in candidates if r['name']=='fixed60')
    for row in candidates:
        for cell,item in row['cells'].items():
            raw=np.array(item['raw']);ref=np.array(reference['cells'][cell]['raw'])
            item['quality_passes']=feasible(raw,ref)
            item['samples_reduction_percent']=100*(1-raw[1]/ref[1])
            item['failed_quality_metrics']=[name for name,k in [('F',2),('O',3),('M60',14)] if raw[k]>ref[k]]
        row['quality_passes_all_cells']=all(v['quality_passes'] for v in row['cells'].values())
    selected = select_rows(candidates,reference)
    c3 = next(r for r in candidates if r['name']=='C3_shape_G75_A900')
    by_name = {r['name']:r for r in candidates}
    usefulness = {}
    for key,name in selected.items():
        winner=by_name[name]
        margins={cell:winner['cells'][cell]['samples_reduction_percent']-c3['cells'][cell]['samples_reduction_percent']
                 for cell in reference['cells']}
        usefulness[key]={'selected':name,'improvement_over_C3_percentage_points':margins,
                         'passes_predeclared_gate':bool(name!='fixed60' and winner['quality_passes_all_cells'] and min(margins.values())>=1)}
    outcome = {'created_on':'2026-10-25','candidates':candidates,'selected':selected,'usefulness':usefulness,
       'plan_sha256':sha256(PLAN),'candidate_lock_sha256':sha256(candidate_path),
       'new_check_bays_opened':False,'final_test_evaluated':False,'phase4_may_start':False,
       'guard_changes_pooled_winner':selected['unrestricted_pooled']!=selected['history_guard_pooled'],
       'elapsed_replay_seconds':time.monotonic()-start_time}
    write_json(WORK/'results.json',outcome)
    print('SELECTION '+json.dumps(selected),flush=True)
    print('USEFULNESS '+json.dumps(usefulness),flush=True)


if __name__=='__main__':main()
