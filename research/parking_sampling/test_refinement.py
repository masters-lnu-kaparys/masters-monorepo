"""C3 correctness checks independent of the real-data policy outcomes."""
import unittest
from pathlib import Path
import numpy as np
from simulation import Observation,context,reference_simulate
from kernels import simulate_window
from refine_policy import total_replay,groups_for,objective,feasible,fit_table
from diagnose_schedule import attribute_window
from report_refinement import paired_intervals
from trained_schedule import TrainedSchedule

class RefinementTests(unittest.TestCase):
    def test_compact_runtime_matches_observed_run_table_at_boundaries(self):
        runtime=TrainedSchedule((300,900),(30,45,75),(30,60,60))
        table=np.tile(np.array([30,30,45,75,75,75]),4).tolist()+np.tile(np.array([30,30,60,60,60,60]),4).tolist()
        for state in (0,1):
            for age in (0,59,60,299,300,899,900,3599,3600,14399,14400,86400):
                observation=Observation(100000+age,state,100000)
                self.assertEqual(runtime.next_pause(observation),table[context(observation)])
        with self.assertRaises(ValueError):runtime.next_pause(Observation(0,0,1))

    def test_paired_intervals_keep_identical_policies_at_zero(self):
        data=np.ones((4,3,17),np.int64)*10;data[:,:,0]=86400
        values=paired_intervals(data,data,draws=50)
        for interval in values.values():np.testing.assert_array_equal(interval,[0,0])

    def test_paired_intervals_match_constant_bay_effect(self):
        ref=np.ones((4,3,17),np.int64)*100;ref[:,:,0]=86400
        candidate=ref.copy();candidate[:,:,1]=50;candidate[:,:,2]+=2;candidate[:,:,3]-=3
        values=paired_intervals(candidate,ref,draws=50)
        np.testing.assert_allclose(values['checks_reduction_percent'],[50,50]);np.testing.assert_allclose(values['F_difference_seconds_per_day'],[2,2]);np.testing.assert_allclose(values['O_difference_seconds_per_day'],[-3,-3])

    def test_new_action_grid_matches_independent_simulator(self):
        rng=np.random.default_rng(20261019)
        for trial in range(40):
            ends=np.cumsum(rng.integers(1,250,size=35)).astype(np.int64)
            states=(np.arange(len(ends))%2).astype(np.int8)
            table=rng.choice([15,30,45,60,75,90,120],size=48).astype(np.int64)
            table[24:]=rng.choice([15,30,45,60],size=24)
            start=int(rng.integers(0,ends[0]))
            for variant in ('full','without_time','without_run'):
                tflag=variant!='without_time';aflag=variant!='without_run'
                got=simulate_window(ends,states,start,1,np.array([60,60],np.int64),table,np.zeros(48,np.int64),tflag,aflag,np.zeros((2,13)),np.array([5,60,120],np.int64),np.uint64(123))
                ref=reference_simulate(ends,states,start,lambda o:(int(table[context(o,tflag,aflag)]),False))
                np.testing.assert_array_equal(got[0],ref[0]);np.testing.assert_array_equal(got[1],ref[1])

    def test_training_replay_totals_match_reference(self):
        ends=np.array([20,40,100,130,200,225,300,500],np.int64)
        states=(np.arange(8)%2).astype(np.int8);table=np.full(48,75,np.int64);table[24:]=45
        offsets=np.array([0,4,8],np.int64);starts=np.array([0,200],np.int64)
        initial=np.array([[0,5],[0,10]],np.int64);seeds=np.ones((2,2),np.uint64)
        expected=np.zeros(17,np.int64)
        for w in range(2):
            for rep in range(2):
                values=reference_simulate(ends[offsets[w]:offsets[w+1]],states[offsets[w]:offsets[w+1]],int(starts[w]+initial[w,rep]),lambda o:(int(table[context(o)]),False))[0]
                expected+=values
        actual=total_replay(ends,states,offsets,starts,initial,seeds,table,True,True)
        np.testing.assert_array_equal(actual,expected)

    def test_diagnostic_attribution_sums_to_independent_metrics(self):
        rng=np.random.default_rng(11)
        for _ in range(20):
            ends=np.cumsum(rng.integers(1,200,size=25)).astype(np.int64);states=(np.arange(25)%2).astype(np.int8)
            table=rng.choice([15,60,120,300],size=48).astype(np.int64)
            e,m=attribute_window(ends,states,0,table)
            values=reference_simulate(ends,states,0,lambda o:(int(table[context(o)]),False))[0]
            np.testing.assert_array_equal(e.sum(axis=0),values[2:4]);self.assertEqual(int(m.sum()),values[14])

    def test_ablation_groups_partition_table_without_hidden_feature(self):
        for variant,length in [('full',48),('without_time',12),('without_run',8)]:
            groups=groups_for(variant);self.assertEqual(len(groups),length)
            self.assertEqual(sorted(x for g in groups for x in g),list(range(48)))
            for ids in groups:
                self.assertEqual(len({x//24 for x in ids}),1)
                if variant=='without_time':self.assertEqual(len({x%6 for x in ids}),1)
                if variant=='without_run':self.assertEqual(len({(x%24)//6 for x in ids}),1)

    def test_objective_rejects_missed_long_episode_even_with_cheaper_schedule(self):
        ref=np.ones(17,np.int64)*100;ref[14]=0;candidate=ref.copy();candidate[1]=1;candidate[14]=1
        self.assertEqual(objective(candidate,ref,1,1),float('inf'));self.assertFalse(feasible(candidate,ref))

    def test_search_never_accepts_long_occupied_pauses_or_missing_episode_trade(self):
        class ToyReplay:
            def __call__(self,table,variant):
                x=np.zeros(17,np.int64);x[0]=86400;x[1]=int(1e5/np.mean(table));x[2]=x[3]=int(np.mean(table)*10)
                x[14]=int(np.any(table>90));return x
        config={'free_actions_seconds':[15,30,45,60,75,90,120],'occupied_actions_seconds':[15,30,45,60]}
        for variant in ('full','without_time','without_run'):
            table=fit_table(ToyReplay(),variant,.25,.25,config)
            self.assertLessEqual(table[24:].max(),60);self.assertLessEqual(table[:24].max(),90)
            if variant=='without_time':
                for state in range(2):
                    for age in range(6):self.assertEqual(len(set(table[(state*4+t)*6+age] for t in range(4))),1)

if __name__=='__main__':unittest.main(verbosity=2)
