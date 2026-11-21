import itertools
import unittest
import numpy as np
from history_certificate import history_bound
from episode_pair_certificate import pair_bound
from simulation import reference_simulate

class HistoryCertificateTests(unittest.TestCase):
    def test_early_pauses_exclude_pair_after_a_recent_forced_occupied_observation(self):
        # The generic count cannot exclude the short B=14,D=60 pair. A preceding
        # occupied interval >=75 forces a sufficiently recent history reset.
        ends=[200,1000,1014,1074,1400];states=[1,0,1,0,1]
        values=history_bound(ends,states,0,60,75,900)
        self.assertEqual(values['generic_pair_bound'],1)
        self.assertEqual(values['history_conditioned_bound'],0)
        choose=lambda o:(60 if o.state else (45 if o.time-o.observed_run_start<900 else 75),False)
        self.assertEqual(reference_simulate(ends,states,0,choose)[0][14],0)

    def test_without_an_age_guard_it_reduces_to_the_generic_bound(self):
        rng=np.random.default_rng(118)
        for _ in range(60):
            ends=np.cumsum(rng.integers(1,160,size=20));states=np.arange(20)%2
            start=int(rng.integers(0,ends[-3]))
            self.assertEqual(history_bound(ends,states,start,60,75,0)['history_conditioned_bound'],
                             pair_bound(ends,states,start,60,75)['risky_adjacent_pairs'])

    def test_bound_for_exhaustive_short_traces(self):
        for lengths in itertools.product((1,14,60,75),repeat=4):
            ends=np.cumsum(lengths)
            for initial in (0,1):
                states=(np.arange(4)+initial)%2
                for age in (0,30,90):
                    choose=lambda o:(60 if o.state else (30 if o.time-o.observed_run_start<age else 75),False)
                    raw=reference_simulate(ends,states,0,choose)[0];bound=history_bound(ends,states,0,60,75,age)
                    self.assertEqual(raw[9],bound['eligible'])
                    self.assertLessEqual(raw[14],bound['history_conditioned_bound'])

    def test_history_bound_for_random_policies_and_censored_starts(self):
        rng=np.random.default_rng(20261026)
        for _ in range(500):
            ends=np.cumsum(rng.choice([1,14,60,74,75,300,1000,3000],size=20));states=(np.arange(20)+int(rng.integers(2)))%2
            start=int(rng.integers(ends[-3]));age=int(rng.choice([0,30,300,900,1800]));cap=int(rng.choice([60,75,90,120]))
            short=int(rng.integers(1,61));long=int(rng.integers(1,cap+1));occupied=int(rng.integers(1,61))
            choose=lambda o:(occupied if o.state else (short if o.time-o.observed_run_start<age else long),False)
            raw=reference_simulate(ends,states,start,choose)[0];bound=history_bound(ends,states,start,60,cap,age)
            self.assertLessEqual(raw[14],bound['history_conditioned_bound'])
            self.assertLessEqual(bound['history_conditioned_bound'],bound['generic_pair_bound'])

    def test_unsampled_free_episode_is_not_an_episode_displayed_occupied(self):
        raw,_,decisions=reference_simulate([1,15,75,200],[0,1,0,1],0,lambda o:(75 if o.state==0 else 60,False))
        self.assertEqual(raw[14],1)
        self.assertEqual(raw[3],0)
        self.assertEqual(raw[2],14)
        self.assertEqual(decisions[0][1],0)

    def test_age_guard_cannot_exclude_a_genuine_counterexample(self):
        ends=[1101,1115,1175,1400];states=[0,1,0,1]
        choose=lambda o:(30 if o.state==1 else (30 if o.time-o.observed_run_start<300 else 45 if o.time-o.observed_run_start<900 else 75),False)
        raw=reference_simulate(ends,states,20,choose)[0]
        self.assertEqual(raw[14],1)
        self.assertEqual(history_bound(ends,states,20,60,75,900)['history_conditioned_bound'],1)

if __name__=='__main__':unittest.main(verbosity=2)
