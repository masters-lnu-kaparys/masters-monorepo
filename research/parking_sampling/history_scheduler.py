"""C5: construct and replay an observed-history scheduler under a path bound.

Calibration sees training traces. Runtime receives only paid observations. This
new module does not change the frozen C3/C4 simulator or fitting code.
"""
from dataclasses import dataclass
import numpy as np
from numba import njit
from simulation import Observation, N_STATS, THRESHOLDS


@dataclass(frozen=True)
class HistorySchedule:
    shape: str
    long_pause: int
    age_threshold: int

    def __post_init__(self):
        if self.shape not in ('C3_shape', 'simple_shape', 'fixed60'):
            raise ValueError('Unknown schedule shape')
        if type(self.long_pause) is not int or not 60 <= self.long_pause <= 300:
            raise ValueError('Invalid long pause')
        if type(self.age_threshold) is not int or self.age_threshold < 300:
            raise ValueError('Invalid age threshold')

    @property
    def name(self):
        if self.shape == 'fixed60':
            return 'fixed60'
        return f'{self.shape}_G{self.long_pause}_A{self.age_threshold}'

    @property
    def kind(self):
        return {'fixed60': 0, 'C3_shape': 1, 'simple_shape': 2}[self.shape]

    def next_pause(self, observation: Observation) -> int:
        age = observation.time - observation.observed_run_start
        if observation.state not in (0, 1) or age < 0:
            raise ValueError('Invalid sampled history')
        if self.shape == 'fixed60':
            return 60
        if observation.state == 1:
            return 30 if self.shape == 'C3_shape' and age < 300 else 60
        if age >= self.age_threshold:
            return self.long_pause
        return 30 if self.shape == 'C3_shape' and age < 300 else 45


@njit(cache=True)
def critical_ages_window(ends, states, start, tau, free_cap):
    """Training-only construction. Return p-r for each generic risky pair."""
    first = int(np.searchsorted(ends, start, side='right'))
    anchor = start
    values = np.empty(len(ends), np.int64)
    count = 0
    for i in range(first, len(ends)):
        a = start if i == first else ends[i-1]
        b = ends[i]
        if states[i] == 1:
            if b-a >= free_cap:
                anchor = max(anchor, b-tau)
        elif i > first+1 and i < len(ends)-1 and b-a >= tau:
            p = ends[i-2]
            if b-p < free_cap:
                values[count] = p-anchor
                count += 1
    return values[:count]


def calibrate_age(data, free_cap, tau=60):
    if not 0 < tau <= free_cap <= 300:
        raise ValueError('Invalid pause/target bound')
    rows = []
    for w in range(len(data.starts)):
        lo, hi = data.offsets[w:w+2]
        ages = critical_ages_window(data.ends[lo:hi], data.states[lo:hi], data.starts[w], tau, free_cap)
        for age in ages:
            rows.append({'window_index': w, 'window_id': data.window_ids[w],
                         'bay': int(data.bays[data.bay_indexes[w]]), 'critical_age_seconds': int(age)})
    threshold = max([300]+[row['critical_age_seconds'] for row in rows])
    return {'long_pause_seconds': free_cap, 'required_age_seconds': threshold,
            'risky_pairs': len(rows), 'pairs': rows,
            'maximum_support_bays': sorted({row['bay'] for row in rows if row['critical_age_seconds'] == threshold})}


@njit(cache=True)
def replay_window(ends, states, start, kind, long_pause, age_threshold):
    totals = np.zeros(N_STATS, np.int64)
    hist = np.zeros(301, np.int64)
    first = np.searchsorted(ends, start, side='right')
    sample = start
    held = -1
    run = start
    totals[0] = ends[-1]-start
    for i in range(first, len(ends)):
        a = start if i == first else ends[i-1]
        b = ends[i]
        state = states[i]
        wrong = max(0, min(sample, b)-a)
        if held != state:
            totals[2 if state == 1 else 3] += wrong
        seen = False
        delay = 0
        while sample < b:
            if not seen:
                delay = sample-a
            seen = True
            if state != held:
                run = sample
            held = state
            age = sample-run
            bound = b
            if kind == 0:
                pause = 60
            elif state == 1:
                pause = 30 if kind == 1 and age < 300 else 60
                if kind == 1 and age < 300:
                    bound = min(bound, run+300)
            elif age >= age_threshold:
                pause = long_pause
            else:
                pause = 30 if kind == 1 and age < 300 else 45
                bound = min(bound, run+age_threshold)
                if kind == 1 and age < 300:
                    bound = min(bound, run+300)
            # Batch only decisions with the same source state AND same action.
            # The action at the first sample >= a decision boundary is recomputed.
            count = max(1, (bound-sample+pause-1)//pause)
            totals[1] += count
            sample += count*pause
        if state == 0 and i > first and i < len(ends)-1:
            if seen:
                totals[5] += 1
                totals[6] += delay
                hist[delay] += 1
            for k in range(5):
                if b-a >= THRESHOLDS[k]:
                    totals[7+k] += 1
                    totals[12+k] += int(not seen)
    return totals, hist


@njit(cache=True)
def replay_bundle(ends, states, offsets, starts, bay_indexes, initial, n_bays, kind, long_pause, age_threshold):
    by = np.zeros((n_bays, initial.shape[1], N_STATS), np.int64)
    hist = np.zeros(301, np.int64)
    for w in range(len(starts)):
        lo, hi = offsets[w:w+2]
        for rep in range(initial.shape[1]):
            raw, h = replay_window(ends[lo:hi], states[lo:hi], starts[w]+initial[w, rep], kind, long_pause, age_threshold)
            by[bay_indexes[w], rep] += raw
            hist += h
    return by, hist


def evaluate(data, schedule, repetitions):
    initial, _ = data.phases(repetitions)
    return replay_bundle(data.ends, data.states, data.offsets, data.starts, data.bay_indexes,
                         initial, len(data.bays), schedule.kind, schedule.long_pause, schedule.age_threshold)
