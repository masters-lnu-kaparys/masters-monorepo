import unittest
import numpy as np
from budget_comparison import definitions,choose_mixture,bootstrap_comparison
from simulation import reference_simulate,context
from kernels import simulate_window


def counter(samples,F,O):
    raw=np.zeros(17);raw[:4]=[86400,samples,F,O];return raw


class BudgetComparisonTests(unittest.TestCase):
    def test_declared_families_and_targets(self):
        bank=definitions()
        counts={g:sum(g in d.groups for d in bank) for g in ('fixed','state','two_stage','S2','pooled')}
        self.assertEqual(counts,{'fixed':13,'state':169,'two_stage':90,'S2':8,'pooled':267})
        self.assertEqual(len(bank),269)
        self.assertEqual(len({d.policy.name for d in bank}),269)
        simple=next(d.policy for d in bank if d.policy.name=='two_stage_F45_900_75_O60_300_60')
        self.assertTrue(np.all(simple.lookup[24:]==60))
        self.assertEqual(simple.lookup[:6].tolist(),[45,45,45,75,75,75])

    def test_exact_budget_linear_expectation(self):
        control=np.array([[counter(1000,4,8),counter(2000,2,4)]])
        target=np.array([counter(1500,10,10)])
        result=choose_mixture(control,target,True)
        np.testing.assert_allclose(result['weights'],[.5,.5])
        self.assertAlmostEqual(result['max_error_ratio'],.6)
        np.testing.assert_allclose(result['expected_raw'][0,:4],[86400,1500,3,6])

    def test_multi_cell_resource_caps_and_minimax(self):
        control=np.array([[counter(1000,4,8),counter(2000,2,4)],
                          [counter(1200,6,10),counter(1800,3,5)]])
        target=np.array([counter(1500,10,10),counter(1400,10,10)])
        r=choose_mixture(control,target)
        self.assertAlmostEqual(r['weights'][1],1/3)
        self.assertLessEqual(max(r['resource_ratios']),1+1e-8)
        self.assertAlmostEqual(r['max_error_ratio'],5/6)

    def test_alignment_and_infeasible_resource_rejected(self):
        controls=np.array([[counter(2000,4,8)]])
        with self.assertRaises(ValueError):choose_mixture(controls,np.array([counter(1500,10,10)]))
        controls[0,0,0]=5
        with self.assertRaises(ValueError):choose_mixture(controls,np.array([counter(1500,10,10)]))

    def test_bootstrap_keeps_bay_pairing(self):
        a=np.array([counter(1000,10,20),counter(2000,20,40)])
        b=a.copy();b[:,1]*=2;b[:,2:4]*=2
        ci=bootstrap_comparison(a,b,draws=100)
        np.testing.assert_allclose(ci['resource_difference_percent'],[-50,-50])
        self.assertLess(ci['F_difference_seconds_per_day'][1],0)
        with self.assertRaises(ValueError):bootstrap_comparison(a,b[:1])

    def test_two_stage_controls_match_independent_reference(self):
        rng=np.random.default_rng(25)
        bank=[d.policy for d in definitions() if 'two_stage' in d.groups]
        for p in bank[::7]:
            ends=np.cumsum(rng.integers(1,1900,size=25)).astype(np.int64)
            states=(np.arange(25)%2).astype(np.int8)
            raw,h,_=reference_simulate(ends,states,137,lambda o:(int(p.lookup[context(o,False,True)]),False))
            fast,fh=simulate_window(ends,states,137,1,p.delays,p.lookup,p.fallback,False,True,
                                    np.zeros((2,13)),np.array([60]),np.uint64(1))
            np.testing.assert_array_equal(raw,fast);np.testing.assert_array_equal(h,fh)


if __name__=='__main__':unittest.main()
