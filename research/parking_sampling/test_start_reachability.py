import unittest
import numpy as np
from start_reachability import FreeProfile,c3_profile,episode_reachability,forward_missed_indices,forward_samples,late_free_witness


class StartReachabilityTests(unittest.TestCase):
    def test_frozen_C3_prefix_first_reaches_plateau_at_930(self):
        p=c3_profile(75)
        self.assertEqual(p.ages[-1],930)
        self.assertEqual(p.ages[:11],tuple(range(0,301,30)))
        self.assertEqual(p.free_pause(885),45);self.assertEqual(p.free_pause(930),75)

    def test_half_open_end_allows_next_measurement_exactly_at_episode_end(self):
        p=FreeProfile((),5,3)
        r=episode_reachability([1,2,5,8],[0,1,0,1],0,p)
        self.assertEqual(r['attainable_episodes'],1)
        self.assertEqual(r['risky_episodes'][0]['witness']['next_sample'],5)

    def test_equal_pair_length_cannot_be_missed(self):
        self.assertEqual(episode_reachability([1,3,6,8],[0,1,0,1],0,FreeProfile((),5,3))['attainable_episodes'],0)

    def test_reachable_late_state_may_require_an_earlier_plateau_entry(self):
        p=FreeProfile((2,2),5,2)
        # Entry at8 fails because root4 is occupied; entry at3/root-1 invalid.
        self.assertIsNone(late_free_witness([4,5,12],[0,1,0],0,8,p))
        # Entry at9/root5 fails (root5 occupied); earlier entry4/root0 works.
        w=late_free_witness([5,6,20],[0,1,0],0,9,p)
        self.assertEqual(w['initial_start'],0);self.assertEqual(w['sample_times_through_last_free'],[0,2,4,9])

    def test_constant_free_trace_supports_every_sufficiently_old_plateau(self):
        p=FreeProfile((2,2),5,2)
        self.assertIsNone(late_free_witness([30],[0],0,3,p))
        self.assertEqual(late_free_witness([30],[0],0,8,p)['initial_start'],4)

    def test_initial_busy_and_last_free_are_censored(self):
        p=FreeProfile((),5,3)
        self.assertEqual(episode_reachability([1,4,5],[1,0,1],0,p)['attainable_episodes'],0)
        self.assertEqual(episode_reachability([1,2,5],[0,1,0],0,p)['eligible'],0)

    def test_arbitrary_trace_starts_and_fractional_initializations_agree(self):
        rng=np.random.default_rng(20261025);p=FreeProfile((1,2),5,3)
        for _ in range(30):
            e=np.cumsum(rng.integers(1,7,size=7)).tolist();s=((np.arange(7)+int(rng.integers(2)))%2).tolist()
            start=int(rng.integers(e[-2]));r=episode_reachability(e,s,start,p)
            expected=set()
            for t in range(start,e[-1]):
                missed=forward_missed_indices(e,s,t,p);expected|=missed
                for f in (.25,.75):self.assertEqual(missed,forward_missed_indices(e,s,t+f,p))
            self.assertEqual({row['source_index'] for row in r['risky_episodes'] if row['attainable']},expected)

    def test_witness_is_complete_and_forward_reproducible(self):
        e=[10,11,15,20];s=[0,1,0,1];p=FreeProfile((1,2),5,3)
        r=episode_reachability(e,s,0,p)
        for row in r['risky_episodes']:
            if not row['attainable']:continue
            w=row['witness'];samples=forward_samples(e,s,w['initial_start'],p)
            self.assertEqual([t for t in samples if t<=w['last_free_sample']],w['sample_times_through_last_free'])
            self.assertIn(row['source_index'],forward_missed_indices(e,s,w['initial_start'],p))

    def test_invalid_profiles_and_trace_are_rejected(self):
        for args in (((0,),5,3),((4,),5,3),((),2,3),((),5.,3)):
            with self.assertRaises(ValueError):FreeProfile(*args)
        with self.assertRaises(ValueError):episode_reachability([3,4],[0,0],0,FreeProfile((),5,3))


if __name__=='__main__':unittest.main()
