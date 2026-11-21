"""Mechanism and analytical checks independent of measured policy improvements."""
import itertools
import unittest
import numpy as np
from audit_episode_constraint import allowed,guarded_objective,fit
from episode_certificate import (short_cycle_bound,verify_policy_certificate,
    duration_counterexample,count_bound_bundle)
from refine_policy import fit_table
from simulation import reference_simulate,context

class NoveltyAuditTests(unittest.TestCase):
    def test_matched_arms_only_change_declared_episode_constraint(self):
        ref=np.ones(17,np.int64)*100;ref[14]=0
        candidate=ref.copy();candidate[1:4]-=1;candidate[14]=1
        self.assertTrue(allowed(candidate,ref,None));self.assertTrue(allowed(candidate,ref,12))
        self.assertFalse(allowed(candidate,ref,14))
        self.assertTrue(np.isfinite(guarded_objective(candidate,ref,1,1,None)))
        self.assertTrue(np.isfinite(guarded_objective(candidate,ref,1,1,12)))
        self.assertEqual(guarded_objective(candidate,ref,1,1,14),float('inf'))
        candidate[12]+=1;self.assertFalse(allowed(candidate,ref,12))

    def test_protected_fit_exactly_reproduces_old_search(self):
        class Replay:
            def __call__(self,table,variant):
                x=np.zeros(17,np.int64);x[0]=86400;x[1]=int(1e6/np.mean(table))
                x[2]=int(np.sum(table[:24]**2));x[3]=int(np.sum(table[24:]**2))
                x[14]=int(np.any(table[:24]>90));return x
        config={'free_actions_seconds':[15,30,45,60,75,90,120],
                'occupied_actions_seconds':[15,30,45,60]}
        for lf,lo in itertools.product((.25,1,4),repeat=2):
            np.testing.assert_array_equal(fit(Replay(),lf,lo,14,config),
                                         fit_table(Replay(),'without_time',lf,lo,config))

    def test_duration_profile_is_not_determined_by_errors_or_total_misses(self):
        a,b=duration_counterexample()
        for name in ('samples','sampled_states','F_seconds','O_seconds','transitions','M0'):
            self.assertEqual(a[name],b[name],name)
        self.assertEqual((a['M60'],b['M60']),(0,1))

    def test_bound_is_tight_and_strict_at_the_preceding_duration_boundary(self):
        choose=lambda o:(75 if o.state==0 else 60,False)
        hit=verify_policy_certificate([1,15,75,150],[0,1,0,1],0,choose,60,15)
        self.assertEqual((hit['missed'],hit['short_preceding_occupied_episodes']),(1,1))
        edge=verify_policy_certificate([1,16,76,150],[0,1,0,1],0,choose,60,15)
        self.assertEqual((edge['missed'],edge['short_preceding_occupied_episodes']),(0,0))

    def test_certificate_on_exhaustive_short_traces(self):
        for lengths in itertools.product((1,15,30,60,75),repeat=4):
            ends=np.cumsum(lengths)
            for first in (0,1):
                states=(np.arange(4)+first)%2
                for pause0,pause1 in ((75,60),(60,60),(30,15)):
                    result=verify_policy_certificate(ends,states,0,
                        lambda o:(pause0 if o.state==0 else pause1,False),60,15)
                    self.assertTrue(result['bound_holds'],(lengths,first,pause0,pause1))

    def test_certificate_for_random_history_dependent_policies_and_censored_starts(self):
        rng=np.random.default_rng(20261025)
        for extension in (0,15,30,90):
            for _ in range(100):
                ends=np.cumsum(rng.integers(1,200,size=30));states=(np.arange(30)+int(rng.integers(2)))%2
                start=int(rng.integers(0,ends[-3]));table=rng.integers(1,61,size=48)
                table[:24]=rng.integers(1,61+extension,size=24)
                result=verify_policy_certificate(ends,states,start,
                    lambda o:(int(table[context(o)]),False),60,extension)
                self.assertTrue(result['bound_holds'])
                if extension==0:self.assertEqual(result['missed'],0)

    def test_violation_of_pause_envelope_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_policy_certificate([10,80,200],[0,1,0],0,lambda o:(76,False),60,15)
        with self.assertRaises(ValueError):
            verify_policy_certificate([10,80,200],[1,0,1],0,lambda o:(61,False),60,15)

    def test_bound_counts_use_same_censoring_and_initial_offsets_as_replay(self):
        ends=np.array([1,15,75,150,201,215,275,350]);states=np.tile([0,1,0,1],2)
        offsets=np.array([0,4,8]);starts=np.array([0,200]);initial=np.array([[0,20],[0,20]])
        result=count_bound_bundle(ends,states,offsets,starts,initial,np.array([0,0]),1,60,15)
        expected=np.zeros((1,2,2),np.int64)
        for w in range(2):
            for phase in range(2):
                v=short_cycle_bound(ends[offsets[w]:offsets[w+1]],states[offsets[w]:offsets[w+1]],
                                    starts[w]+initial[w,phase],60,15)
                expected[0,phase]=expected[0,phase]+list(v.values())
        np.testing.assert_array_equal(result,expected)

    def test_miss_accounting_by_gaps_includes_the_right_end(self):
        # A check exactly at the end of a free interval does not detect it.
        rng=np.random.default_rng(22)
        for _ in range(100):
            ends=np.cumsum(rng.integers(1,100,size=15));states=np.arange(15)%2
            raw,_,decisions=reference_simulate(ends,states,0,lambda o:(75,False))
            samples=[d[0] for d in decisions];nexts=samples[1:]+[int(ends[-1])]
            for k,tau in enumerate((0,30,60,120,300)):
                count=sum(1 for i in range(1,len(ends)-1) if states[i]==0 and ends[i]-ends[i-1]>=tau
                          for a,b in zip(samples,nexts) if a<ends[i-1] and ends[i]<=b)
                self.assertEqual(count,raw[12+k])

    def test_invalid_binary_or_unmerged_traces_rejected(self):
        for ends,states in (([10,10],[0,1]),([10,20],[0,0]),([10,20],[0,2]),([10.5,20],[0,1])):
            with self.assertRaises(ValueError):short_cycle_bound(ends,states,0,60,15)

if __name__=='__main__':unittest.main(verbosity=2)
