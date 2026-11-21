import itertools
import unittest
import numpy as np
from episode_pair_certificate import pair_bound,calibrated_free_cap
from episode_certificate import verify_policy_certificate
from simulation import context,reference_simulate
from fit_pair_envelope import select_cap,apply_cap,training_pair_sums
from data_access import Bundle
from assess_pair_envelope_controls import control_tables

class PairCertificateTests(unittest.TestCase):
    def test_sharper_bound_excludes_long_free_runs_despite_short_predecessor(self):
        ends=[1,10,200,300];states=[0,1,0,1]
        coarse=verify_policy_certificate(ends,states,0,lambda o:(75 if o.state==0 else 60,False),60,15)
        self.assertEqual(coarse['short_preceding_occupied_episodes'],1)
        self.assertEqual(pair_bound(ends,states,0,60,75)['risky_adjacent_pairs'],0)

    def test_strict_pair_boundary_is_necessary(self):
        self.assertEqual(pair_bound([1,15,75,150],[0,1,0,1],0,60,75)['risky_adjacent_pairs'],1)
        self.assertEqual(pair_bound([1,16,76,150],[0,1,0,1],0,60,75)['risky_adjacent_pairs'],0)

    def test_initial_occupied_run_cannot_create_a_hidden_full_free_episode(self):
        self.assertEqual(pair_bound([1,61,100],[1,0,1],0,60,75)['risky_adjacent_pairs'],0)

    def test_bound_for_exhaustive_short_traces_and_all_initial_states(self):
        for lengths in itertools.product((1,14,15,60,74),repeat=4):
            ends=np.cumsum(lengths)
            for initial in (0,1):
                states=(np.arange(4)+initial)%2
                for free_cap in (60,75,90):
                    raw=reference_simulate(ends,states,0,lambda o:(free_cap if o.state==0 else 60,False))[0]
                    self.assertLessEqual(raw[14],pair_bound(ends,states,0,60,free_cap)['risky_adjacent_pairs'])

    def test_bound_for_history_dependent_random_policies(self):
        rng=np.random.default_rng(991)
        for free_cap in (45,60,75,90,150):
            for _ in range(80):
                ends=np.cumsum(rng.integers(1,150,size=30));states=(np.arange(30)+int(rng.integers(2)))%2
                start=int(rng.integers(ends[-4]));table=rng.integers(1,61,size=48);table[:24]=rng.integers(1,free_cap+1,size=24)
                raw=reference_simulate(ends,states,start,lambda o:(int(table[context(o)]),False))[0]
                self.assertLessEqual(raw[14],pair_bound(ends,states,start,60,free_cap)['risky_adjacent_pairs'])

    def test_empirical_calibration_respects_strict_endpoint_and_budget(self):
        sums=[61,75,75,100]
        self.assertEqual(calibrated_free_cap(sums,[60,61,62,75,76,100],0),61)
        self.assertEqual(calibrated_free_cap(sums,[60,61,62,75,76,100],.25),75)
        with self.assertRaises(ValueError):calibrated_free_cap([], [60],0)
        with self.assertRaises(ValueError):calibrated_free_cap([61], [62],0)

    def test_training_cap_is_the_smallest_pair_sum_with_conservative_empty_fallback(self):
        self.assertEqual(select_cap([80,72,90]),72)
        self.assertEqual(select_cap([130,140]),120)
        self.assertEqual(select_cap([]),60)
        with self.assertRaises(ValueError):select_cap([60])

    def test_author_change_only_replaces_the_long_free_plateau(self):
        template=np.r_[np.tile([30,30,45,75,75,75],4),np.tile([30,30,60,60,60,60],4)]
        changed=apply_cap(template,72)
        np.testing.assert_array_equal(changed[24:],template[24:])
        np.testing.assert_array_equal(changed[:24][template[:24]!=75],template[:24][template[:24]!=75])
        self.assertTrue(np.all(changed[:24][template[:24]==75]==72))
        self.assertTrue(np.any(template==75))

    def test_training_pairs_exclude_censored_edges_and_short_targets(self):
        data=Bundle(np.array([1,15,75,90,120,200]),np.array([0,1,0,1,0,1]),
            np.array([0,6]),np.array([0]),np.array([0]),np.array([1]),('w',),{})
        np.testing.assert_array_equal(training_pair_sums(data),[74])

    def test_simpler_controls_preserve_the_frozen_initial_rule_and_occupied_cap(self):
        original=np.r_[np.tile([45,45,45,75,75,75],4),np.full(24,60)]
        tables=control_tables(original,72)
        np.testing.assert_array_equal(tables['simple75'],original)
        self.assertTrue(np.all(tables['simple72'][24:]==60))
        np.testing.assert_array_equal(tables['simple72'][:6],[45,45,45,72,72,72])
        self.assertTrue(np.all(tables['state_only72'][:24]==72))
        self.assertTrue(np.all(tables['state_only72'][24:]==60))

if __name__=='__main__':unittest.main(verbosity=2)
