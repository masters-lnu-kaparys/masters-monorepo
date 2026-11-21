"""Scientific correctness checks, independent reference and analytical fixtures."""
import dataclasses
import json
import random
import unittest
import numpy as np

from simulation import (Observation,reference_simulate,context,random_step,AGES,ACTIONS,THRESHOLDS)
from kernels import simulate_window,grid_transition_counts,risk_training_window
from markov_baseline import age_cost,verify_published_examples,solve_occupation_lp
from data_access import load_bundle
from training import smooth_tables
from policies import risk_policy
from policies import constant_policy
from run_phase3 import strict_select,resource_select

def fast(ends,states,start=0,kind=0,delays=(60,60),lookup=None,flags=(True,True),cdf=None,seed=123):
    return simulate_window(np.asarray(ends,np.int64),np.asarray(states,np.int8),start,kind,np.array(delays,np.int64),
      np.full(48,60,np.int64) if lookup is None else lookup,np.zeros(48,np.int64),*flags,
      np.tile([.2,.5,1.],(2,1)) if cdf is None else cdf,np.array([5,30,120],np.int64),np.uint64(seed))

class MethodTests(unittest.TestCase):
    def test_strict_selection_rejects_one_extra_long_missed_vacancy(self):
        p=constant_policy(120);p.family='candidate'
        reference=np.zeros(17,np.int64);reference[[0,1,2,3]]=[86400,1440,100,100]
        candidate=reference.copy();candidate[1]=1000;candidate[14]=1
        selected=strict_select([p],{'fixed_60':reference,p.name:candidate},'candidate')
        self.assertTrue(selected['fallback']);self.assertEqual(selected['policy'],'fixed_60')

    def test_strict_selection_minimizes_calls_then_errors(self):
        a=constant_policy(120);b=constant_policy(300);a.family=b.family='candidate'
        reference=np.zeros(17,np.int64);reference[[0,1,2,3]]=[86400,1440,100,100]
        x=reference.copy();x[1]=1000;x[2]=99
        y=x.copy();y[2]=98
        chosen=strict_select([a,b],{'fixed_60':reference,a.name:x,b.name:y},'candidate')
        self.assertEqual(chosen['policy'],b.name)

    def test_resource_comparison_keeps_reference_with_boundary_overhead(self):
        p=constant_policy(60);raw=np.zeros(17,np.int64);raw[0]=86401;raw[1]=1441
        chosen=resource_select([p],{'fixed_60':raw},'fixed',1440)
        self.assertEqual(chosen['policy'],'fixed_60')

    def test_s2_resource_point_retains_nominal_policy_and_reports_overshoot(self):
        raw=np.zeros(17,np.int64);raw[0]=86400;raw[1]=722
        chosen=resource_select([],{'S2_720':raw},'S2',720)
        self.assertEqual(chosen['policy'],'S2_720');self.assertTrue(chosen['realized_exceeds_nominal_budget'])

    def test_hand_computed_errors_and_delay(self):
        values,hist=fast([20,40,100,130,200],[0,1,0,1,0])
        self.assertEqual((values[0],values[1],values[2],values[3]),(200,4,40,50))
        self.assertEqual((values[5],values[6],hist[20]),(1,20,1))
        self.assertEqual(values[9],1);self.assertEqual(values[14],0)

    def test_episode_ending_at_measurement_is_missed(self):
        values,_=fast([10,30,90,121],[0,1,0,1],delays=(90,90))
        self.assertEqual(values[9],1);self.assertEqual(values[14],1)

    def test_first_and_last_episodes_censored(self):
        values,_=fast([100,200,400],[0,1,0],delays=(300,300))
        self.assertTrue(np.all(values[7:17]==0))

    def test_constant_state_has_no_error_and_zero_event_denominators(self):
        values,_=fast([1000],[1],delays=(120,120))
        self.assertEqual(values[1],9);self.assertTrue(np.all(values[2:4]==0));self.assertTrue(np.all(values[7:17]==0))

    def test_observation_has_no_trace_or_future(self):
        self.assertEqual({f.name for f in dataclasses.fields(Observation)},{'time','state','observed_run_start'})
        with self.assertRaises(dataclasses.FrozenInstanceError):Observation(0,0,0).state=1

    def test_common_prefix_decisions_do_not_depend_on_future(self):
        def choose(o):return (15 if o.state==0 else 60),False
        a=reference_simulate([100,200,300],[0,1,0],0,choose)[2]
        b=reference_simulate([100,160,300],[0,1,0],0,choose)[2]
        self.assertEqual([x for x in a if x[0]<160],[x for x in b if x[0]<160])

    def test_fast_and_reference_match_random_traces(self):
        rng=random.Random(20261018)
        for trial in range(100):
            durations=[rng.randint(1,100) for _ in range(rng.randint(3,35))]
            ends=np.cumsum(durations,dtype=np.int64);states=(np.arange(len(ends))+rng.randrange(2)).astype(np.int8)%2
            start=rng.randrange(min(50,int(ends[-1])-1))
            for mode in range(3):
                lookup=np.array([rng.choice([5,15,30,60,120,300]) for _ in range(48)],np.int64)
                delays=np.array([rng.choice([5,30,120]),rng.choice([5,30,120])],np.int64)
                random_state=123
                def choose(o):
                    nonlocal random_state
                    if mode==0:return int(delays[o.state]),False
                    if mode==1:return int(lookup[context(o)]),False
                    random_state,u=random_step(random_state)
                    return [5,30,120][int(np.searchsorted([.2,.5,1.],u,side='right'))],False
                expected=reference_simulate(ends,states,start,choose)
                got=fast(ends,states,start,kind=mode,delays=delays,lookup=lookup)
                np.testing.assert_array_equal(got[0],expected[0],err_msg=f'{trial}/{mode}')
                np.testing.assert_array_equal(got[1],expected[1],err_msg=f'{trial}/{mode}')

    def test_time_and_run_boundaries_and_ablations(self):
        ends=np.array([30000,50000,100000],np.int64);states=np.array([0,1,0],np.int8)
        lookup=np.array([5,15,30,60,120,300]*8,np.int64)
        for flags in [(True,True),(False,True),(True,False),(False,False)]:
            expected=reference_simulate(ends,states,21599,lambda o:(int(lookup[context(o,*flags)]),False))
            got=fast(ends,states,21599,kind=1,lookup=lookup,flags=flags)
            np.testing.assert_array_equal(got[0],expected[0]);np.testing.assert_array_equal(got[1],expected[1])

    def test_training_matches_explicit_teacher_observations(self):
        rng=np.random.default_rng(7)
        ends=np.cumsum(rng.integers(1,90,size=50)).astype(np.int64);states=(np.arange(50)%2).astype(np.int8)
        cadence=30;anchor=300
        expected=[np.zeros((48,6),np.int64),np.zeros((48,6)),np.zeros((48,6)),np.zeros((48,6,5))]
        held=-1;run=0
        for t in range(0,int(ends[-1])-300,cadence):
            i=int(np.searchsorted(ends,t,side='right'));state=int(states[i])
            if state!=held:run=t
            held=state
            if t%anchor:continue
            ctx=context(Observation(t,state,run))
            for k,d in enumerate(ACTIONS):
                expected[0][ctx,k]+=1;occupied=0
                for second in range(t,t+int(d)):
                    occupied+=int(states[np.searchsorted(ends,second,side='right')])
                expected[1][ctx,k]+=occupied/int(d) if state==0 else 0
                expected[2][ctx,k]+=(int(d)-occupied)/int(d) if state==1 else 0
                for j in range(1,len(ends)):
                    a=int(ends[j-1]);b=int(ends[j])
                    if states[j]==0 and t<a and b<=t+d:
                        for q,tau in enumerate(THRESHOLDS):expected[3][ctx,k,q]+=int(b-a>=tau)
        got=risk_training_window(ends,states,0,cadence,anchor,True,True)
        for a,b in zip(got,expected):np.testing.assert_allclose(a,b,rtol=0,atol=1e-10)

    def test_training_horizon_excludes_future_outside_window(self):
        ends=np.array([60,300],np.int64);states=np.array([0,1],np.int8)
        self.assertEqual(risk_training_window(ends,states,0,30,300,True,True)[0].sum(),0)

    def test_training_label_includes_episode_ending_at_next_measurement(self):
        ends=np.array([10,30,60,121,500],np.int64);states=np.array([0,1,0,1,0],np.int8)
        n,f,o,m=risk_training_window(ends,states,0,30,900,True,True)
        self.assertEqual(m[0,3,1],1)
        self.assertAlmostEqual(f[0,3],20/60)

    def test_smoothing_and_feature_pooling(self):
        n=np.ones((48,6),np.int64);f=np.full((48,6),.1);o=np.full((48,6),.2);m=np.zeros((48,6,5))
        full=smooth_tables(n,f,o,m);no_time=smooth_tables(n,f,o,m,False,True);no_run=smooth_tables(n,f,o,m,True,False)
        self.assertTrue(np.all(full['n']==1));self.assertTrue(np.all(no_time['n']==4));self.assertTrue(np.all(no_run['n']==6))
        np.testing.assert_allclose(no_time['pf'],.1);np.testing.assert_allclose(no_run['po'],.2)

    def test_risk_rule_normalization_and_fallback(self):
        model={'n':np.full((48,6),100),'pf':np.zeros((48,6)),'po':np.zeros((48,6)),
          'pm':np.zeros((48,6,5)),'use_time':True,'use_run':True}
        model['pm'][:,:,0]=.1
        raw=risk_policy('raw','C1',model,.01,.01,.001)
        rate=risk_policy('rate','C2',model,.01,.01,.001,normalize_misses=True)
        self.assertTrue(np.all(raw.fallback==1));self.assertTrue(np.all(raw.lookup==5))
        self.assertTrue(np.all(rate.fallback==0));self.assertTrue(np.all(rate.lookup==300))

    def test_compressed_transition_counts_match_explicit_grid(self):
        ends=np.array([7,9,12,41,100],np.int64);states=np.array([0,1,0,1,0],np.int8)
        values=states[np.searchsorted(ends,np.arange(0,100,5),side='right')]
        expected=np.zeros((2,2),np.int64)
        for a,b in zip(values[:-1],values[1:]):expected[a,b]+=1
        np.testing.assert_array_equal(grid_transition_counts(ends,states,0,5),expected)

    def test_published_s2_example1_and_frequency(self):
        result=verify_published_examples()
        self.assertTrue(result['all_required_checks_passed'])
        self.assertFalse(result['example2_printed_probabilities_satisfy_d1'])

    def test_age_cost_matches_geometric_event_sum(self):
        for p in [0.,.05,.4,.95,1.]:
            for action in [1,2,7,60]:
                direct=sum((action-n)*(1-p)*p**(n-1) for n in range(1,action))
                self.assertAlmostEqual(age_cost(p,action),direct,places=10)

    def test_lp_constraints_and_deterministic_candidates(self):
        p=np.array([[.9,.1],[.6,.4]])
        result=solve_occupation_lp(p,[1,2,3,4,5,6],mean_interval_min=3)
        self.assertLess(result['max_flow_residual'],1e-8)
        self.assertGreaterEqual(result['mean_interval'],3-1e-8)
        self.assertAlmostEqual(np.array(result['occupation']).sum(),1)

    def test_final_partition_is_refused(self):
        with self.assertRaises(PermissionError):load_bundle(('quarantine_final_test',))
        with self.assertRaises(PermissionError):load_bundle(('quarantine_train_reserved',))

if __name__=='__main__':unittest.main(verbosity=2)
