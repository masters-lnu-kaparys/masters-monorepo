"""Deployable research policy: known BayId, sampled state, clock, observed run only."""
import hashlib
import json
from bisect import bisect_right
from pathlib import Path


class CalibratedSchedule:
    def __init__(self,payload):
        if payload.get('schema_version')!=1:raise ValueError('Unsupported policy schema')
        self.seed=int(payload['allocation_seed']);self.edges=tuple(payload['observed_run_edges_seconds'])
        if self.edges!=(60,300,900,3600,14400):raise ValueError('Unexpected context boundaries')
        self.weights=payload['component_weights'];self.components=payload['components'];self.assignments={}
        if set(self.weights)!=set(self.components) or any(w<0 for w in self.weights.values()) or abs(sum(self.weights.values())-1)>1e-9:
            raise ValueError('Invalid component weights')
        for component in self.components.values():
            for row in [component['pooled_fallback'],*component['bay_tables'].values()]:
                if len(row)!=48 or any(type(d)!=int or not 1<=d<=300 for d in row):raise ValueError('Invalid action table')

    @classmethod
    def load(cls,path):return cls(json.loads(Path(path).read_text(encoding='utf-8')))

    def component_for_bay(self,bay):
        bay=int(bay)
        if bay not in self.assignments:
            u=int.from_bytes(hashlib.sha256(f'local-risk-allocation:{self.seed}:{bay}'.encode()).digest()[:8],'little')/2**64
            cumulative=0.;names=sorted(self.weights);chosen=names[-1]
            for name in names:
                cumulative+=self.weights[name]
                if u<cumulative:chosen=name;break
            self.assignments[bay]=chosen
        return self.assignments[bay]

    def next_pause(self,bay,observation):
        time=observation.time;run=observation.observed_run_start;state=observation.state
        if state not in (0,1) or time<run:raise ValueError('Invalid paid observation')
        component=self.components[self.component_for_bay(bay)];table=component['bay_tables'].get(str(int(bay)),component['pooled_fallback'])
        ctx=(state*4+int(time%86400//21600))*6+bisect_right(self.edges,time-run)
        return table[ctx]
