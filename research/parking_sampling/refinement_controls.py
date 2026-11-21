"""Ablation controls: guard old C2, and a small causal backoff grid."""
import argparse
import itertools
import json
import numpy as np
from prepare_data import ROOT,DOCS,sha256
from data_access import load_bundle
from policies import risk_policy
from simulation import AGES,summarize
from refine_policy import WORK,full_replay,feasible
from run_phase3 import write_json

def definitions():
    old=ROOT/'.codex-work/parking-research-phase3-20261018/models/risk-full.npz'
    model=dict(np.load(old));result=[]
    for f,o,m,cap in itertools.product([.003,.006,.012,.024],[.003,.006,.012,.024],[1e-6,1e-5,1e-4,1e-3],[75,90,120]):
        policy=risk_policy('c','C2',model,f,o,m,normalize_misses=True)
        table=policy.lookup.copy();table[:24]=np.minimum(table[:24],cap);table[24:]=np.minimum(table[24:],60)
        result.append((f'guarded_C2_{f}_{o}_{m}_{cap}','guarded_C2',table,(f,o,m,cap)))
    for early,threshold,long,occupied in itertools.product([15,30,45,60],[60,300,900,3600],[75,90,120],[30,45,60]):
        table=np.full(48,occupied,np.int64)
        for tb in range(4):
            for ab,start in enumerate([0,*AGES]):table[tb*6+ab]=long if start>=threshold else early
        result.append((f'backoff_{early}_{threshold}_{long}_{occupied}','backoff',table,(early,threshold,long,occupied)))
    return result

def main(check=False):
    plan=DOCS/'phase3-refinement-comparators.json'
    meta=json.loads((WORK/'pre-fit-lock.json').read_text(encoding='utf-8'))
    out=WORK/'controls';out.mkdir(exist_ok=True)
    defs=definitions();lookup={name:table for name,family,table,params in defs}
    if not check:
        if (WORK/'fresh-check-results.json').exists():raise RuntimeError('Control selection was intended before fresh results')
        d=load_bundle(('validation_development',),bay_filter=meta['tuning_bays'])
        b,h=full_replay(d,np.full(48,60,np.int64),'full');ref=b.sum(axis=(0,1));cache={};records=[]
        for name,family,table,params in defs:
            key=table.tobytes()
            if key not in cache:
                b,h=full_replay(d,table,'full');cache[key]=(b,h)
            b,h=cache[key];raw=b.sum(axis=(0,1))
            records.append({'name':name,'family':family,'parameters':params,'raw':raw.tolist(),'metrics':summarize(raw,h),'feasible':feasible(raw,ref)})
        chosen={}
        for family in ('guarded_C2','backoff'):
            rows=[x for x in records if x['family']==family and x['feasible']]
            best=min(rows,key=lambda x:(x['raw'][1],x['raw'][2],x['raw'][3],x['parameters'])) if rows else None
            chosen[family]=best['name'] if best else 'fixed_60'
            if best:np.savez_compressed(out/f"{best['name']}.npz",lookup=lookup[best['name']])
        write_json(out/'selection-before-check.json',{'chosen':chosen,'records':records,'plan_sha256':sha256(plan),'code_sha256':sha256(__file__),
          'fresh_outcomes_seen':False,'reference':ref.tolist()})
        print('CONTROLS '+json.dumps(chosen),flush=True)
    else:
        chosen=json.loads((out/'selection-before-check.json').read_text(encoding='utf-8'))['chosen'];results={}
        for primary,label in [(True,'primary_7_days'),(False,'sensitivity_1_day')]:
            d=load_bundle(('validation_development',),bay_filter=meta['fresh_check_bays'],primary_only=primary);rows={}
            rb,rh=full_replay(d,np.full(48,60,np.int64),'full');ref=rb.sum(axis=(0,1))
            for family,name in chosen.items():
                if name=='fixed_60':b,h=rb,rh
                else:b,h=full_replay(d,np.load(out/f'{name}.npz')['lookup'],'full')
                raw=b.sum(axis=(0,1));np.savez_compressed(out/f'{label}_{family}.npz',by_bay_phase=b,delay_histogram=h,bays=d.bays)
                rows[family]={'name':name,'raw':raw.tolist(),'metrics':summarize(raw,h),'quality_passes':feasible(raw,ref),'checks_reduction_percent':float(100*(1-raw[1]/ref[1]))}
            results[label]=rows
        write_json(out/'fresh-check-results.json',{'cohorts':results,'selection_sha256':sha256(out/'selection-before-check.json'),'final_test_evaluated':False})
        print(json.dumps({label:{family:{k:v for k,v in item.items() if k in ('name','quality_passes','checks_reduction_percent')} for family,item in rows.items()} for label,rows in results.items()},indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');main(parser.parse_args().check)
