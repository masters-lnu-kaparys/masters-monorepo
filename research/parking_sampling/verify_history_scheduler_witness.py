"""Verify every new C3 tuning sensitivity miss using the independent simulator."""
import json
import numpy as np
from prepare_data import ROOT, DOCS, sha256
from data_access import load_bundle
from fit_history_scheduler import WORK, read
from history_scheduler import HistorySchedule, replay_window
from simulation import reference_simulate
from stability_audit import civil
from run_phase3 import write_json


def main():
    result = read(WORK/'results.json')
    lock = read(WORK/'pre-fit-lock.json')
    check_lock = {'created_on':'2026-10-25','experiment_results_sha256':sha256(WORK/'results.json'),
                  'verification_code_sha256':sha256(__file__),
                  'scope':'Verify all C3 M60 on original tuning128 >=1day; no parameter changes',
                  'final_test_evaluated':False}
    write_json(WORK/'witness-verification-lock.json',check_lock)
    d = load_bundle(('validation_development',),bay_filter=lock['tuning_bays'],primary_only=False)
    initial,_ = d.phases(10)
    schedules = [HistorySchedule('C3_shape',75,900), HistorySchedule('C3_shape',72,900)]
    byname = {r['name']:r for r in result['candidates']}
    for key in ('unrestricted_pooled','history_guard_pooled'):
        row = byname[result['selected'][key]]
        schedules.append(HistorySchedule(row['shape'],row['long_pause'],row['age_threshold']))
    cases=[];count=0
    for w in range(len(d.starts)):
        lo,hi = d.offsets[w:w+2]
        ends,states = d.ends[lo:hi],d.states[lo:hi]
        for rep in range(10):
            start=int(d.starts[w]+initial[w,rep])
            raw,_ = replay_window(ends,states,start,1,75,900)
            if not raw[14]: continue
            case = {'bay':int(d.bays[d.bay_indexes[w]]),'window_id':d.window_ids[w],
                    'window_duration_seconds':int(ends[-1]-d.starts[w]),'repetition':rep,
                    'initial_offset_seconds':int(initial[w,rep]),'initial_time':civil(start),'policies':{}}
            arrays={'ends':ends,'states':states,'replay_start':np.array(start)}
            for schedule in schedules:
                r,h,decisions=reference_simulate(ends,states,start,lambda o:(schedule.next_pause(o),False))
                fast,fh=replay_window(ends,states,start,schedule.kind,schedule.long_pause,schedule.age_threshold)
                np.testing.assert_array_equal(r,fast);np.testing.assert_array_equal(h,fh)
                episodes=[];times=np.array([x[0] for x in decisions])
                first=int(np.searchsorted(ends,start,side='right'))
                for i in range(first+1,len(ends)-1):
                    if states[i]!=0 or ends[i]-ends[i-1]<60:continue
                    a,b=int(ends[i-1]),int(ends[i]);j=int(np.searchsorted(times,a,side='left'))
                    if j<len(times) and times[j]<b:continue
                    p=int(ends[i-2]);near=decisions[max(0,j-4):min(len(decisions),j+3)]
                    episodes.append({'index':i,'occupied_start':civil(p),'free_start':civil(a),'free_end':civil(b),
                      'B_seconds':a-p,'D_seconds':b-a,'pair_sum_seconds':b-p,
                      'preceding_sample_displayed_state':int(decisions[j-1][1]),
                      'nearby_measurements':[{'time':civil(t),'state':int(s),'observed_run_age_seconds':int(t-run),'pause_seconds':int(pause)}
                                             for t,s,run,pause,fb in near]})
                assert len(episodes)==r[14]
                arrays[schedule.name+'_raw']=r
                arrays[schedule.name+'_decisions']=np.array(decisions,dtype=np.int64)
                case['policies'][schedule.name]={'reference_raw':r.tolist(),'missed_target_episodes':episodes}
            assert case['policies'][schedules[1].name]['reference_raw'][14]==0
            count+=len(case['policies'][schedules[0].name]['missed_target_episodes'])
            path=WORK/'witnesses'/f'{d.window_ids[w]}_rep{rep}.npz'
            path.parent.mkdir(exist_ok=True)
            np.savez_compressed(path,**arrays);case['arrays_path']=path.relative_to(ROOT).as_posix()
            cases.append(case)
    expected=byname[schedules[0].name]['cells']['tuning_sensitivity_1_day']['raw'][14]
    assert count==expected
    write_json(WORK/'verified-witnesses.json',{'created_on':'2026-10-25','verified_C3_M60':count,
              'cases':cases,'all_17_raw_metrics_and_histograms_match_reference':True,
              'C4_M60_on_these_cases':0,'final_test_evaluated':False,'policy_retuned':False})
    print(json.dumps({'verified_C3_M60':count,'cases':cases},ensure_ascii=False))


if __name__=='__main__':main()
