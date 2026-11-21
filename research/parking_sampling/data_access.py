"""Partition access for phase 3. Final and late partitions are refused here."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import duckdb
import numpy as np
from prepare_data import ROOT,DOCS,quote,sha256
from simulation import phase_offset,stable_seed

DEFAULT_WORK=ROOT/'.codex-work/parking-research-phase2-20261018'

@dataclass
class Bundle:
    ends:np.ndarray
    states:np.ndarray
    offsets:np.ndarray
    starts:np.ndarray
    bay_indexes:np.ndarray
    bays:np.ndarray
    window_ids:tuple
    source_files:dict

    def phases(self,repetitions,policy_id='deterministic'):
        initial=np.empty((len(self.starts),repetitions),dtype=np.int64)
        seeds=np.empty_like(initial,dtype=np.uint64)
        for w,wid in enumerate(self.window_ids):
            bay=int(self.bays[self.bay_indexes[w]])
            for rep in range(repetitions):
                initial[w,rep]=phase_offset(bay,wid,rep)
                seeds[w,rep]=stable_seed(f'20261018:{policy_id}:{wid}:{rep}')
        return initial,seeds

def tuning_bays(work=DEFAULT_WORK,limit=128):
    c=duckdb.connect()
    p=work/'prepared/windows.parquet'
    ids=[r[0] for r in c.execute('SELECT DISTINCT bay FROM read_parquet(?) WHERE split_role=? AND is_primary',[str(p),'validation_development']).fetchall()]
    c.close()
    return sorted(ids,key=lambda b:hashlib.sha256(f'masters-parking-tuning-v1:{b}'.encode()).hexdigest())[:limit]

def load_bundle(roles,*,work=DEFAULT_WORK,bay_filter=None,training_lock=None,primary_only=True):
    roles=tuple(roles)
    allowed={'train_development','validation_development'}
    if 'quarantine_train_reserved' in roles:
        if training_lock is None:raise PermissionError('Frozen training pipeline is required before reserved training history')
        lock=json.loads(Path(training_lock).read_text(encoding='utf-8'))
        for name,h in lock['training_code_sha256'].items():
            if sha256(ROOT/'research/parking_sampling'/name)!=h:raise PermissionError(f'Training code changed after lock: {name}')
        allowed.add('quarantine_train_reserved')
    if set(roles)-allowed:raise PermissionError('Phase 3 cannot open final-test, late-development, or reserved-validation states')
    manifest=json.loads((work/'prepared/data-manifest.json').read_text(encoding='utf-8'))
    paths=[ROOT/manifest['files'][role]['path'] for role in roles]
    for role,path in zip(roles,paths):
        if sha256(path)!=manifest['files'][role]['sha256']:raise ValueError('Partition checksum mismatch')
    file_sql='['+','.join(quote(p.as_posix()) for p in paths)+']'
    where='is_primary' if primary_only else 'true'
    if bay_filter is not None:
        if not len(bay_filter):raise ValueError('Empty cohort')
        where+=' AND bay IN ('+','.join(str(int(b)) for b in bay_filter)+')'
    c=duckdb.connect();c.execute("SET memory_limit='1GB'");c.execute('SET threads=2')
    v=c.execute(f'''SELECT bay,window_start,window_end,start_local_seconds,end_local_seconds,state FROM read_parquet({file_sql})
      WHERE {where} ORDER BY bay,window_start,start_local_seconds''').fetchnumpy()
    c.close()
    if len(v['bay'])==0:raise ValueError('No intervals in partition/cohort')
    changes=np.r_[True,(v['bay'][1:]!=v['bay'][:-1]) | (v['window_start'][1:]!=v['window_start'][:-1])]
    offsets=np.r_[np.flatnonzero(changes),len(v['bay'])].astype(np.int64)
    first=offsets[:-1];bays=np.unique(v['bay']).astype(np.int64)
    mapping={int(b):i for i,b in enumerate(bays)}
    indexes=np.array([mapping[int(b)] for b in v['bay'][first]],dtype=np.int64)
    # Every role here has a single calendar period; IDs match the phase-2 key.
    period='validation' if roles==('validation_development',) else 'train'
    ids=tuple(hashlib.sha256(f'{int(b)}:{int(a)}:{int(z)}:{period}'.encode()).hexdigest()[:24]
      for b,a,z in zip(v['bay'][first],v['window_start'][first],v['window_end'][first]))
    return Bundle(np.asarray(v['end_local_seconds'],dtype=np.int64),np.asarray(v['state'],dtype=np.int8),
      offsets,np.asarray(v['window_start'][first],dtype=np.int64),indexes,bays,ids,
      {r:manifest['files'][r]['sha256'] for r in roles})
