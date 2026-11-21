"""Recorded windows and deterministic initial phases for replay."""
from dataclasses import dataclass

import numpy as np

from simulation import phase_offset, stable_seed


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
