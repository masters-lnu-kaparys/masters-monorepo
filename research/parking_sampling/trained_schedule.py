"""Compact runtime for a frozen sampled-history policy; no unsampled state access."""
from dataclasses import dataclass
import json
from pathlib import Path
from simulation import Observation

@dataclass(frozen=True)
class TrainedSchedule:
    age_thresholds:tuple[int,...]
    free_pauses:tuple[int,...]
    occupied_pauses:tuple[int,...]

    @classmethod
    def load(cls,path:Path):
        payload=json.loads(Path(path).read_text(encoding='utf-8'))
        thresholds=tuple(payload['observed_run_thresholds_seconds'])
        free=tuple(payload['free_pauses_seconds']);occupied=tuple(payload['occupied_pauses_seconds'])
        if any(type(x)!=int or x<=0 for x in thresholds) or tuple(sorted(set(thresholds)))!=thresholds:raise ValueError('Invalid thresholds')
        if len(free)!=len(thresholds)+1 or len(occupied)!=len(free):raise ValueError('Invalid schedule dimensions')
        if any(type(x)!=int or not 1<=x<=300 for x in (*free,*occupied)):raise ValueError('Invalid pauses')
        return cls(thresholds,free,occupied)

    def next_pause(self,observation:Observation)->int:
        age=observation.time-observation.observed_run_start
        if observation.state not in (0,1) or age<0:raise ValueError('Invalid sampled history')
        index=sum(age>=edge for edge in self.age_thresholds)
        return (self.free_pauses if observation.state==0 else self.occupied_pauses)[index]
