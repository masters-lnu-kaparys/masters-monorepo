import unittest
import numpy as np
from analytic_certificate import reset_certificate,exact_maximum_misses,count_witness_misses
from history_certificate import history_bound
from simulation import reference_simulate


class AnalyticCertificateTests(unittest.TestCase):
    def test_endpoint_reset_strictly_improves_legacy_anchor(self):
        e=[6,14,15,19,22];s=[1,0,1,0,1]
        c=reset_certificate(e,s,0,4,6,8)
        self.assertEqual([c[k] for k in ('adjacent_pair','legacy_history','end_reset','recursive_reset')],[1,1,0,0])
        self.assertEqual(exact_maximum_misses(e,s,0,4,6,8)['maximum_missed'],0)

    def test_recursive_reset_strictly_improves_end_only_anchor(self):
        e=[6,12,16,22,23,27,30];s=[1,0,1,0,1,0,1]
        c=reset_certificate(e,s,0,4,6,8)
        self.assertEqual([c[k] for k in ('adjacent_pair','legacy_history','end_reset','recursive_reset')],[1,1,1,0])
        self.assertEqual(exact_maximum_misses(e,s,0,4,6,8)['maximum_missed'],0)

    def test_positive_bound_is_not_an_attainable_miss_count(self):
        e=[1,2,5,6,9,10];s=[0,1,0,1,0,1]
        c=reset_certificate(e,s,0,3,5,0);x=exact_maximum_misses(e,s,0,3,5,0)
        self.assertEqual(c['recursive_reset'],2);self.assertEqual(x['maximum_missed'],1)
        self.assertEqual(count_witness_misses(e,s,0,3,x['witness']),1)

    def test_equality_boundaries_and_initial_occupied_short_run(self):
        # B+D=G is excluded, and initial occupied is always observed.
        self.assertEqual(reset_certificate([1,2,6,8],[0,1,0,1],0,4,5,0)['adjacent_pair'],0)
        c=reset_certificate([1,5,6,10,12],[1,0,1,0,1],0,4,6,8)
        self.assertEqual(c['recursive_reset'],0)
        self.assertEqual(exact_maximum_misses([1,5,6,10,12],[1,0,1,0,1],0,4,6,8)['maximum_missed'],0)

    def test_legacy_count_unchanged_and_ordered(self):
        rng=np.random.default_rng(20261025)
        for _ in range(100):
            ends=np.cumsum(rng.integers(1,10,size=9));states=(np.arange(9)+int(rng.integers(2)))%2
            start=int(rng.integers(ends[-3]));c=reset_certificate(ends,states,start,3,5,8)
            old=history_bound(ends,states,start,3,5,8)
            self.assertEqual(c['legacy_history'],old['history_conditioned_bound'])
            self.assertLessEqual(c['recursive_reset'],c['end_reset'])
            self.assertLessEqual(c['end_reset'],c['legacy_history'])

    def test_maximum_witness_is_legal_and_replayable(self):
        e=[4,5,9,10,15,20];s=[0,1,0,1,0,1]
        x=exact_maximum_misses(e,s,0,3,5,2);choices={r[0]:r[3] for r in x['witness']}
        raw,h,decisions=reference_simulate(e,s,0,lambda o:(choices[o.time],False))
        self.assertEqual([list(r[:4]) for r in decisions],x['witness'])
        self.assertEqual(count_witness_misses(e,s,0,3,x['witness']),x['maximum_missed'])
        for t,state,run,pause in x['witness']:
            self.assertLessEqual(pause,3 if state or t-run<2 else 5)

    def test_required_caps_cannot_be_removed(self):
        # Breaking the occupied cap can hide the first target episode.
        r,_,d=reference_simulate([1,3,7],[1,0,1],0,lambda o:(4,False))
        self.assertEqual(reset_certificate([1,3,7],[1,0,1],0,2,4,0)['recursive_reset'],0)
        self.assertEqual(count_witness_misses([1,3,7],[1,0,1],0,2,[list(x[:4]) for x in d]),1)
        # The recursive reset also relies on early-free pauses<=tau.
        choices={0:4,4:2,6:4,10:6,16:5,21:6,27:3}
        e=[6,12,16,22,23,27,30];s=[1,0,1,0,1,0,1]
        _,_,d=reference_simulate(e,s,0,lambda o:(choices[o.time],False))
        self.assertEqual(count_witness_misses(e,s,0,4,[list(x[:4]) for x in d]),1)

    def test_invalid_input_and_large_exact_search_rejected(self):
        for args in (([3,4],[0,0],0,2,3,1),([3,4],[0,1],0,4,3,1),([3,4],[0,1],0,2,3,-1)):
            with self.assertRaises(ValueError):reset_certificate(*args)
        with self.assertRaises(ValueError):exact_maximum_misses([1000],[0],0,2,3,1)


if __name__=='__main__':unittest.main()
