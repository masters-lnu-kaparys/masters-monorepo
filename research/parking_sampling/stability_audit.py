"""Frozen-C4 influence, temporal calibration and adversarial phase diagnostics."""
from __future__ import annotations
import csv
from datetime import datetime,timedelta
import json
import numpy as np
from numba import njit
from prepare_data import ROOT,DOCS,sha256
from data_access import load_bundle
from audit_episode_constraint import WORK as PREVIOUS,OLD
from fit_pair_envelope import select_cap
from kernels import simulate_window
from simulation import reference_simulate
from run_phase3 import write_json

WORK=ROOT/'.codex-work/parking-stability-audit-20261025'
PLAN=DOCS/'phase3-stability-plan.json'
PAIR_DTYPE=np.dtype([(n,'i8') for n in ('bay','window','index','p','a','b','B','D','sum')])

def civil(seconds):return (datetime(1970,1,1)+timedelta(seconds=int(seconds))).isoformat(' ')
def civil_seconds(year,month):return int((datetime(year,month,1)-datetime(1970,1,1)).total_seconds())

def extract_pairs(data,minimum_free=50):
    pieces=[]
    for w in range(len(data.starts)):
        lo,hi=data.offsets[w:w+2];ends=data.ends[lo:hi];states=data.states[lo:hi]
        ids=np.arange(2,len(ends)-1);ids=ids[(states[ids]==0)&(ends[ids]-ends[ids-1]>=minimum_free)]
        rows=np.zeros(len(ids),dtype=PAIR_DTYPE)
        rows['bay']=data.bays[data.bay_indexes[w]];rows['window']=w;rows['index']=ids
        rows['p']=ends[ids-2];rows['a']=ends[ids-1];rows['b']=ends[ids]
        rows['B']=rows['a']-rows['p'];rows['D']=rows['b']-rows['a'];rows['sum']=rows['b']-rows['p']
        pieces.append(rows)
    return np.concatenate(pieces) if pieces else np.empty(0,dtype=PAIR_DTYPE)

def minimum_diagnostics(rows,bays,draws=2000):
    if not len(rows):raise ValueError('Influence diagnostics need eligible pairs')
    values=rows['sum'];minimum=int(values.min());count=int(np.sum(values==minimum))
    distinct=np.unique(values);next_value=int(distinct[1]) if len(distinct)>1 else None
    groups={}
    for field,universe in (('bay',bays),('window',np.unique(rows['window']))):
        group_min=np.array([int(values[rows[field]==g].min()) if np.any(rows[field]==g) else 10**12 for g in universe])
        caps=[]
        for i,g in enumerate(universe):
            remaining=np.delete(group_min,i);valid=remaining[remaining<10**12]
            cap=select_cap(valid) if len(valid) else 60
            caps.append({'removed':int(g),'cap_seconds':int(cap)})
        groups[field]={'caps':caps,'changed_removals':[x for x in caps if x['cap_seconds']!=min(120,minimum)]}
        if field=='bay':
            rng=np.random.default_rng(20261025);sampled=group_min[rng.integers(0,len(group_min),size=(draws,len(group_min)))]
            minima=sampled.min(axis=1);boot=np.where(minima>=10**12,60,np.minimum(120,minima))
    vals,freq=np.unique(boot,return_counts=True)
    return {'minimum_seconds':minimum,'minimum_pair_count':count,
      'minimum_support_bays':np.unique(rows['bay'][values==minimum]).tolist(),
      'minimum_support_windows':np.unique(rows['window'][values==minimum]).tolist(),
      'next_distinct_sum_seconds':next_value,
      'leave_one_pair_out_changed_count':int(count==1 and min(120,next_value or 60)!=min(120,minimum)),
      'leave_one_pair_out_largest_cap_seconds':min(120,next_value or 60) if count==1 else min(120,minimum),
      'leave_group_out':groups,
      'bootstrap':{'draws':draws,'seed':20261025,'unit':'whole BayId with replacement',
        'interpretation':'Instability diagnostic; NOT a confidence interval for an unobserved population minimum',
        'cap_frequency':{str(int(v)):int(n) for v,n in zip(vals,freq)}},
      'smallest_distinct_sums':[{'sum_seconds':int(s),'pairs':int(np.sum(values==s)),
        'bays':len(np.unique(rows['bay'][values==s]))} for s in distinct[:20]]}

def temporal_diagnostics(rows):
    out=[];nominal=rows[rows['D']>=60]
    for month in range(1,6):
        cutoff=civil_seconds(2019,month+1);end=civil_seconds(2019,month+2)
        prefix=nominal[nominal['b']<cutoff];cap=select_cap(prefix['sum'])
        following=nominal[(nominal['p']>cutoff)&(nominal['b']<end)]
        risky=following[following['sum']<cap]
        out.append({'prefix_through_month':month,'calibration_pairs':len(prefix),'cap_seconds':cap,
          'following_month':month+1,'following_complete_pairs':len(following),
          'following_risky_pairs':len(risky),'following_min_sum_seconds':int(following['sum'].min()) if len(following) else None,
          'actual_misses_inferred':False})
    return out

def timing_diagnostics(rows,cap=72):
    out=[]
    for delta in (0,1,2,5):
        eligible=rows[rows['D']>=60-2*delta];risky=eligible[eligible['sum']-2*delta<cap]
        out.append({'hypothetical_boundary_error_seconds':delta,'eligible_recorded_pairs':len(eligible),
          'candidate_risky_pairs':len(risky),'risky_bays':len(np.unique(risky['bay'])),
          'measured_timestamp_error':False,'actual_misses_inferred':False})
    return out

@njit(cache=True)
def replay_all_starts(ends,states,start,table,count=3600):
    raw=np.zeros((count,17),np.int64)
    for phase in range(count):
        values,hist=simulate_window(ends,states,start+phase,1,np.array([60,60],np.int64),table,
          np.zeros(48,np.int64),False,True,np.zeros((2,13)),np.array([60],np.int64),np.uint64(1))
        raw[phase]=values
    return raw

def reference_witness(ends,states,start,table):
    from simulation import context
    values,h,decisions=reference_simulate(ends,states,start,lambda o:(int(table[context(o,False,True)]),False))
    times=np.array([d[0] for d in decisions]);first=int(np.searchsorted(ends,start,side='right'));episodes=[]
    for i in range(first+1,len(ends)-1):
        if states[i]!=0:continue
        a,b=int(ends[i-1]),int(ends[i]);j=int(np.searchsorted(times,a,side='left'))
        if b-a>=60 and (j==len(times) or times[j]>=b):
            p=int(ends[i-2]);near=decisions[max(0,j-4):min(len(decisions),j+3)]
            episodes.append({'occupied_start':civil(p),'free_start':civil(a),'free_end':civil(b),
              'B_seconds':a-p,'D_seconds':b-a,'sum_seconds':b-p,
              'nearby_measurements':[{'time':civil(t),'recorded_state':s,'observed_run_start':civil(run),'pause_seconds':pause} for t,s,run,pause,fb in near]})
    return values,episodes

def main():
    WORK.mkdir(parents=True,exist_ok=True);(WORK/'.gitignore').write_text('*\n!.gitignore\n',encoding='utf-8')
    old= json.loads((OLD/'pre-fit-lock.json').read_text(encoding='utf-8'))
    previous=json.loads((PREVIOUS/'pre-fit-lock.json').read_text(encoding='utf-8'))
    lock={'created_on':'2026-10-25','plan_sha256':sha256(PLAN),'code_sha256':sha256(__file__),
      'frozen_C4_json_sha256':sha256(DOCS/'phase3-pair-envelope-policy.json'),
      'training_bays':old['training_bays'],'validation_bays':{'check256':previous['new_check_bays'],'check512':old['fresh_check_bays']},
      'prior_development_outcomes_known':True,'final_test_evaluated':False}
    path=WORK/'pre-analysis-lock.json'
    if path.exists() and json.loads(path.read_text(encoding='utf-8'))!=lock:raise ValueError('Versioned stability lock changed')
    write_json(path,lock);result={'created_on':'2026-10-25','training':{},'development':{},'final_test_evaluated':False}
    for primary,label in ((True,'primary_7_days'),(False,'sensitivity_1_day')):
        data=load_bundle(('train_development',),bay_filter=old['training_bays'],primary_only=primary)
        pairs=extract_pairs(data);nominal=pairs[pairs['D']>=60]
        if primary:assert len(nominal)==132840 and select_cap(nominal['sum'])==72
        item={'bays':len(data.bays),'windows':len(data.starts),'eligible_pairs':len(nominal),
          'minimum_diagnostics':minimum_diagnostics(nominal,data.bays),'temporal':temporal_diagnostics(pairs),'timing':timing_diagnostics(pairs)}
        result['training'][label]=item
        np.savez_compressed(WORK/f'training-pairs-{label}.npz',pairs=pairs,bays=data.bays)
        with (WORK/f'smallest-pairs-{label}.csv').open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.writer(f);writer.writerow(['bay','window_id','occupied_start','free_start','free_end','B_seconds','D_seconds','sum_seconds'])
            for row in np.sort(nominal,order=['sum','bay','p'])[:100]:
                writer.writerow([int(row['bay']),data.window_ids[int(row['window'])],civil(row['p']),civil(row['a']),civil(row['b']),int(row['B']),int(row['D']),int(row['sum'])])
        print('TRAIN',label,json.dumps({'pairs':len(nominal),'minimum':item['minimum_diagnostics']['minimum_seconds'],
          'support_bays':item['minimum_diagnostics']['minimum_support_bays'],'bootstrap':item['minimum_diagnostics']['bootstrap']['cap_frequency'],
          'temporal':item['temporal'],'timing':item['timing']}),flush=True)
    c3=np.load(OLD/'models/C3_without_time_0.25_0.25_75.npz')['lookup'];c4=np.load(PREVIOUS/'pair-envelope-v2/C4.npz')['lookup']
    for cohort,bays in lock['validation_bays'].items():
        data=load_bundle(('validation_development',),bay_filter=bays,primary_only=False);pairs=extract_pairs(data)
        risky=pairs[(pairs['D']>=60)&(pairs['sum']<75)];windows=np.unique(risky['window']);out=[]
        for w in windows:
            lo,hi=data.offsets[w:w+2];ends=data.ends[lo:hi];states=data.states[lo:hi];start=int(data.starts[w]);wid=data.window_ids[w]
            a=replay_all_starts(ends,states,start,c3);b=replay_all_starts(ends,states,start,c4)
            if np.any(b[:,14]):raise AssertionError('C4 violates the zero pair certificate')
            folder=WORK/'phases';folder.mkdir(exist_ok=True)
            np.savez_compressed(folder/f'{wid}.npz',C3=a,C4=b,ends=ends,states=states,start=start)
            bad=np.flatnonzero(a[:,14]);row={'bay':int(data.bays[data.bay_indexes[w]]),'window_id':wid,'window_start':civil(start),
              'window_end':civil(ends[-1]),'primary':bool(ends[-1]-start>=7*86400),'risky_pairs':int(np.sum(risky['window']==w)),
              'C3_bad_offsets_count':len(bad),'C3_bad_offsets':bad.tolist(),'C3_total_episode_phase_misses':int(a[:,14].sum()),
              'C4_bad_offsets_count':0,'offset_domain':'integer seconds0..3599 after window start'}
            if len(bad):
                phase=int(bad[0]);ref,episodes=reference_witness(ends,states,start+phase,c3)
                np.testing.assert_array_equal(ref,a[phase]);row['independent_reference_witness']={'offset':phase,'episodes':episodes}
            out.append(row);print('PHASES',cohort,row['bay'],wid,'C3_bad',len(bad),'C4_bad',0,flush=True)
        result['development'][cohort]={'bays':len(data.bays),'windows':len(data.starts),'timing':timing_diagnostics(pairs),
          'nominal_risky_pairs_for75':len(risky),'phase_windows':out,
          'non_risky_windows_excluded_by_the_pair_bound':len(data.starts)-len(windows)}
    write_json(WORK/'results.json',result);print('DONE',flush=True)

if __name__=='__main__':main()
