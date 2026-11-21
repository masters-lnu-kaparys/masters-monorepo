import unittest
from itertools import product
import numpy as np
from simulation import Observation, reference_simulate
from history_scheduler import HistorySchedule, critical_ages_window, replay_window
from history_certificate import history_bound
from kernels import simulate_window


class HistorySchedulerTests(unittest.TestCase):
    def test_runtime_boundaries(self):
        s = HistorySchedule('C3_shape', 90, 1811)
        self.assertEqual([s.next_pause(Observation(t, 0, 0)) for t in (0,299,300,1810,1811)], [30,30,45,45,90])
        self.assertEqual([s.next_pause(Observation(t, 1, 0)) for t in (299,300,1811)], [30,60,60])
        for bad in (('invalid',75,900), ('C3_shape',301,900), ('C3_shape',75,299)):
            with self.assertRaises(ValueError): HistorySchedule(*bad)
        with self.assertRaises(ValueError): s.next_pause(Observation(0,0,1))

    def test_independent_reference_random_traces(self):
        rng = np.random.default_rng(20261025)
        for trial in range(45):
            n = int(rng.integers(4,35))
            ends = np.cumsum(rng.integers(1,2200,size=n)).astype(np.int64)
            states = ((np.arange(n)+trial)%2).astype(np.int8)
            start = int(rng.integers(0,int(ends[-2])))
            for shape in ('C3_shape','simple_shape','fixed60'):
                s = HistorySchedule(shape, int(rng.choice([72,75,90,120])), int(rng.choice([300,901,1811,86400])))
                raw,h,_ = reference_simulate(ends,states,start,lambda o:(s.next_pause(o),False))
                got,gh = replay_window(ends,states,start,s.kind,s.long_pause,s.age_threshold)
                np.testing.assert_array_equal(got,raw)
                np.testing.assert_array_equal(gh,h)

    def test_c3_c4_equivalence_to_frozen_kernel(self):
        rng = np.random.default_rng(14)
        for cap in (72,75):
            table = np.tile([30,30,45,cap,cap,cap],4).tolist()+np.tile([30,30,60,60,60,60],4).tolist()
            for start in range(0,180,17):
                ends=np.cumsum(rng.integers(1,1400,size=30)).astype(np.int64)
                states=(np.arange(30)%2).astype(np.int8)
                old,h=simulate_window(ends,states,start,1,np.array([60,60]),np.array(table),np.zeros(48,np.int64),False,True,np.zeros((2,13)),np.array([60]),np.uint64(1))
                new,nh=replay_window(ends,states,start,1,cap,900)
                np.testing.assert_array_equal(old,new);np.testing.assert_array_equal(h,nh)

    def test_critical_age_matches_bound_strictness(self):
        # A long occupied interval forces a reset; the later B+D=70 is risky.
        ends=np.array([150,800,810,870,1200],np.int64)
        states=np.array([1,0,1,0,1],np.int8)
        ages=critical_ages_window(ends,states,0,60,75)
        np.testing.assert_array_equal(ages,[710]) # p800 - (d150-tau60)
        self.assertEqual(history_bound(ends,states,0,60,75,710)['history_conditioned_bound'],0)
        self.assertEqual(history_bound(ends,states,0,60,75,709)['history_conditioned_bound'],1)
        self.assertEqual(len(critical_ages_window(ends,states,0,60,70)),0)

    def test_constructed_threshold_all_starts_small_traces(self):
        for lengths in product((5,65,200), repeat=5):
            ends=np.cumsum(lengths).astype(np.int64)
            states=np.array([0,1,0,1,0],np.int8)
            ages=critical_ages_window(ends,states,0,60,120)
            threshold=max(300,int(ages.max()) if len(ages) else 0)
            s=HistorySchedule('C3_shape',120,threshold)
            self.assertEqual(history_bound(ends,states,0,60,120,threshold)['history_conditioned_bound'],0)
            for start in (0,1,int(ends[1])-1):
                raw,h,_=reference_simulate(ends,states,start,lambda o:(s.next_pause(o),False))
                self.assertEqual(raw[14],0)

    def test_runtime_has_no_unsampled_state_input(self):
        s=HistorySchedule('simple_shape',120,1800)
        o=Observation(2500,0,500)
        self.assertEqual(s.next_pause(o),120)
        self.assertEqual(s.next_pause(Observation(2500,1,500)),60)


if __name__ == '__main__': unittest.main()
