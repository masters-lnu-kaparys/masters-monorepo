"""Pre-test safeguards and counter/analysis equivalence on synthetic histories."""
import tempfile
import unittest
from pathlib import Path
import numpy as np
from phase4_pipeline import frozen_arm,select_component,aggregate_components,evaluate_component,validate_frozen
from phase4_analysis import paired_intervals,success_gate,metric_summary
from local_risk import estimates
from frozen_local_priors import shared_priors
from local_risk_calibration_v3 import realized_by_bay
from simulation import reference_simulate,Observation,BASE_ACTIONS,AGES
from prepare_data import sha256


class FinalPipelineTests(unittest.TestCase):
    def test_frozen_priors_reproduce_all_control_formulas(self):
        rng=np.random.default_rng(41);n=rng.integers(0,100,(7,48));cost=rng.random((7,48,11))*n[:,:,None]
        state,context=shared_priors(n,cost)
        for arm in ('pooled_state','pooled_clock_age','bay_state_alpha50','bay_full_alpha0','bay_full_alpha500'):
            expected,_=estimates(n,cost,arm)
            np.testing.assert_array_equal(frozen_arm(n,cost,state,context,arm),expected)

    def test_hash_allocation_matches_development(self):
        weights={'z':.2,'a':.7,'m':.1};names=list(weights);bays=np.arange(1,50)
        values=np.arange(3*len(bays)*17).reshape(3,len(bays),17)
        for seed in range(20261025,20261035):
            _,choices=realized_by_bay(values,bays,names,weights,seed)
            self.assertEqual(choices,[select_component(b,weights,seed) for b in bays])

    def test_whole_policy_mixture_preserves_exposure_and_counts(self):
        values=np.zeros((2,3,17),dtype=np.int64);values[:,:,0]=86400
        values[0,:,1:4]=[100,2,4];values[1,:,1:4]=[200,6,8]
        hist=np.zeros((2,3,301),dtype=np.int64);hist[0,:,2]=1;hist[1,:,3]=2
        expected,eh,actual,ah,choices=aggregate_components(values,hist,[3,7,12],['a','b'],{'a':.25,'b':.75})
        np.testing.assert_array_equal(expected[:,0],[86400]*3)
        np.testing.assert_array_equal(expected[:,1:4],[[175,5,7]]*3)
        self.assertEqual(eh.sum(),5.25)
        for i,n in enumerate(choices):
            j=['a','b'].index(n);np.testing.assert_array_equal(actual[i],values[j,i]);np.testing.assert_array_equal(ah[i],hist[j,i])

    def test_compiled_per_bay_histograms_match_independent_reference(self):
        ends=np.array([20,70,130,200,230,290,360,400],dtype=np.int64);states=np.array([1,0,1,0,0,1,0,1],dtype=np.int8)
        offsets=np.array([0,4,8],dtype=np.int64);starts=np.array([0,200],dtype=np.int64);indexes=np.array([0,1],dtype=np.int64)
        initial=np.array([[0,7],[0,9]],dtype=np.int64);seeds=np.ones((2,2),dtype=np.uint64)
        tables=np.tile(np.array([15,30,45,60,72,90]*8,dtype=np.int64),(2,1));tables[1]=60
        by,h=evaluate_component(ends,states,offsets,starts,indexes,initial,seeds,tables,np.zeros((2,2,len(BASE_ACTIONS))),1,2)
        for w in range(2):
            expected_hist=np.zeros(301,dtype=np.int64);lo,hi=offsets[w:w+2]
            def choose(o):
                ctx=(o.state*4+int(o.time%86400//21600))*6+sum(o.time-o.observed_run_start>=a for a in AGES)
                return int(tables[w,ctx]),False
            for rep in range(2):
                raw,hist,_=reference_simulate(ends[lo:hi],states[lo:hi],int(starts[w]+initial[w,rep]),choose)
                np.testing.assert_array_equal(by[w,rep],raw);expected_hist+=hist
            np.testing.assert_array_equal(h[w],expected_hist)

    def test_bootstrap_keeps_exact_paired_ratio(self):
        ref=np.zeros((4,17));ref[:,0]=86400*np.arange(1,5);ref[:,1]=100*np.arange(1,5);ref[:,2:4]=10*np.arange(1,5)[:,None]
        candidate=ref.copy();candidate[:,1:4]*=.8
        ci=paired_intervals(candidate,ref,reps=100)
        np.testing.assert_allclose(ci['pointwise95']['calls_reduction_percent'],[20,20])
        np.testing.assert_allclose(ci['bonferroni_joint3_approx95']['F_difference_seconds_per_bay_day'],[-2,-2])
        gate=success_gate(candidate.sum(axis=0),ref.sum(axis=0),ci)
        self.assertTrue(gate['point_estimate_display_success']);self.assertTrue(gate['joint3_interval_support'])

    def test_joint_gate_does_not_confuse_point_estimate_with_interval(self):
        a=np.ones(17);b=np.ones(17);a[1]=.8;a[2:4]=.9
        ci={'bonferroni_joint3_approx95':{'calls_reduction_percent':[-1,30],
          'F_difference_seconds_per_bay_day':[-2,0],'O_difference_seconds_per_bay_day':[-2,-1]}}
        gate=success_gate(a,b,ci);self.assertTrue(gate['point_estimate_display_success']);self.assertFalse(gate['joint3_interval_support'])

    def test_locked_guard_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'frozen.txt';p.write_text('one',encoding='utf-8')
            lock={'phase3_complete':True,'phase4_may_start':True,'files':{'frozen.txt':sha256(p)},
              'package_versions':{},'allowed_roles':['quarantine_train_reserved','quarantine_final_test']}
            validate_frozen(lock,Path(t));p.write_text('two',encoding='utf-8')
            with self.assertRaises(PermissionError):validate_frozen(lock,Path(t))

    def test_locked_guard_rejects_unfrozen_or_reserved_validation(self):
        with self.assertRaises(PermissionError):validate_frozen({'phase3_complete':False})
        with self.assertRaises(PermissionError):validate_frozen({'phase3_complete':True,'phase4_may_start':True,
          'files':{},'package_versions':{},'allowed_roles':['quarantine_validation_unused']})

    def test_zero_eligible_vacancies_are_missing_not_zero(self):
        raw=np.zeros(17);raw[0]=86400;raw[1]=1440
        self.assertIsNone(metric_summary(raw)['vacancies']['60']['missed_fraction'])


if __name__=='__main__':unittest.main()
