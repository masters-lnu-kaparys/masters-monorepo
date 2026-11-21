import unittest
import numpy as np
from local_risk import ACTIONS,collect_window,estimates,make_tables,align_tables,evaluate_local
from simulation import reference_simulate,context,Observation


class LocalRiskTests(unittest.TestCase):
    def test_training_integrals_match_independent_anchor_reconstruction(self):
        e=np.array([130,700,750,1100,1400,2200,2700]);s=np.array([0,1,0,1,0,1,0])
        for cadence in (30,60,300):
            n,cost=collect_window(e,s,0,cadence)
            expected_n=np.zeros(48,np.int64);expected_cost=np.zeros((48,len(ACTIONS)))
            _,_,decisions=reference_simulate(e,s,0,lambda o:(cadence,False))
            for t,state,run,_,_ in decisions:
                if t%900 or t+300>=e[-1]:continue
                ctx=context(Observation(t,state,run));expected_n[ctx]+=1
                for k,d in enumerate(ACTIONS):
                    expected_cost[ctx,k]+=sum(int(s[np.searchsorted(e,u,side='right')])!=state for u in range(t,t+int(d)))
            np.testing.assert_array_equal(n,expected_n);np.testing.assert_array_equal(cost,expected_cost)

    def statistics(self):
        n=np.ones((2,48))*100;cost=n[:,:,None]*np.broadcast_to(ACTIONS,(2,48,len(ACTIONS)))*.01
        cost[1]*=4
        return n,cost

    def test_pooled_estimates_identical_across_bays(self):
        n,c=self.statistics()
        for arm in ('pooled_state','pooled_clock_age'):
            risk,pool=estimates(n,c,arm);np.testing.assert_array_equal(risk[0],risk[1])

    def test_local_shrinkage_preserves_supported_bay_differences(self):
        n,c=self.statistics();risk,_=estimates(n,c,'bay_full_alpha50')
        self.assertTrue(np.all(risk[1]>risk[0]))
        raw,_=estimates(n,c,'bay_full_alpha0');np.testing.assert_allclose(raw,c/n[:,:,None])

    def test_missing_support_and_unseen_bay_use_nonzero_prior(self):
        n,c=self.statistics();n[0,0]=0;c[0,0]=0
        risk,pool=estimates(n,c,'bay_full_alpha0');self.assertTrue(np.all(risk[0,0]>0))
        tab=make_tables(risk,1,1);pt=make_tables(pool[None],1,1)[0]
        aligned,missing=align_tables([1,2],tab,[2,9],pt)
        self.assertEqual(missing,[9]);np.testing.assert_array_equal(aligned[1],pt)

    def test_constant_zero_cost_chooses_largest_pause(self):
        np.testing.assert_array_equal(make_tables(np.zeros((1,48,len(ACTIONS))),1,1),300)

    def test_local_replay_matches_independent_reference(self):
        e=np.array([130,700,750,1100,1400,2200,2700]);s=np.array([0,1,0,1,0,1,0])
        tables=np.tile(np.array([30,30,45,75,120,180,15,30,45,60,72,90]*4),(1,1))
        by,h=evaluate_local(e,s,np.array([0,len(e)]),np.array([0]),np.array([0]),np.array([[7]]),np.array([[1]],np.uint64),tables,1)
        raw,hh,_=reference_simulate(e,s,7,lambda o:(int(tables[0,context(o)]),False))
        np.testing.assert_array_equal(by[0,0],raw);np.testing.assert_array_equal(h,hh)

    def test_invalid_model_and_penalties(self):
        n,c=self.statistics()
        with self.assertRaises(ValueError):estimates(n,c[:,:,:2],'pooled_state')
        with self.assertRaises(ValueError):make_tables(c,0,1)


if __name__=='__main__':unittest.main()
