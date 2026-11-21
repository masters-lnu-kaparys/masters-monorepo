import unittest
import numpy as np
from budget_comparison import definitions,choose_mixture
from budget_coverage_annex import extra_definitions,solve_covered


def raw(c,f,o,m=0):
    x=np.zeros(17);x[:4]=[86400,c,f,o];x[14]=m;return x


class CoverageAnnexTests(unittest.TestCase):
    def test_stronger_bank_gives_controls_the_same_cap(self):
        extras=extra_definitions();bank=definitions()+extras
        self.assertEqual(len(extras),57);self.assertEqual(len(bank),326)
        self.assertEqual(len({x.policy.name for x in bank}),326)
        self.assertEqual(sum('two_stage' in x.groups for x in extras),30)
        self.assertTrue(any(x.policy.name=='state_72_60' for x in extras))

    def test_zero_coverage_forbids_unsafe_component(self):
        c=np.array([[raw(1000,5,5,1),raw(1000,9,9,0)]])
        t=np.array([raw(1000,10,10,0)])
        self.assertAlmostEqual(choose_mixture(c,t,True)['max_error_ratio'],.5)
        answer=solve_covered(c,t,True)
        np.testing.assert_allclose(answer['weights'],[0,1]);self.assertAlmostEqual(answer['max_error_ratio'],.9)

    def test_positive_coverage_budget_is_linear(self):
        c=np.array([[raw(1000,5,5,2),raw(1000,9,9,0)]])
        t=np.array([raw(1000,10,10,1)])
        answer=solve_covered(c,t,True)
        np.testing.assert_allclose(answer['weights'],[.5,.5]);self.assertAlmostEqual(answer['max_error_ratio'],.7)

    def test_joint_resource_and_coverage_across_cells(self):
        c=np.array([[raw(1000,5,5),raw(2000,1,1)],
                    [raw(1000,5,5),raw(2000,1,1,1)]])
        t=np.array([raw(1500,10,10),raw(1500,10,10)])
        a=solve_covered(c,t)
        np.testing.assert_allclose(a['weights'],[1,0])
        self.assertAlmostEqual(a['max_error_ratio'],.5)

    def test_infeasible_or_unaligned_inputs_rejected(self):
        c=np.array([[raw(1000,5,5,1)]])
        with self.assertRaises(ValueError):solve_covered(c,np.array([raw(1000,10,10)]),True)
        c[0,0,0]=0
        with self.assertRaises(ValueError):solve_covered(c,np.array([raw(1000,10,10)]))


if __name__=='__main__':unittest.main()
