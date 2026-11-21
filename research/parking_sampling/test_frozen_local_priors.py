import unittest
import numpy as np
from local_risk import ACTIONS,estimates
from frozen_local_priors import shared_priors,apply_frozen_priors


class FrozenPriorTests(unittest.TestCase):
    def test_appending_preserves_exact_original_supported_estimates(self):
        rng=np.random.default_rng(20261025);n=rng.integers(0,1000,size=(4,48));cost=rng.random((4,48,len(ACTIONS)))*n[:,:,None]*ACTIONS
        state,context=shared_priors(n,cost);expected,_=estimates(n,cost,'bay_full_alpha500')
        np.testing.assert_array_equal(apply_frozen_priors(n,cost,state,context),expected)

    def test_new_bay_cannot_change_existing_priors_or_estimates(self):
        n=np.full((2,48),100.);c=n[:,:,None]*np.broadcast_to(ACTIONS,(2,48,len(ACTIONS)))*.01
        state,context=shared_priors(n,c);a=apply_frozen_priors(n,c,state,context)
        newn=np.concatenate((n,np.zeros((1,48))));newc=np.concatenate((c,np.zeros((1,48,len(ACTIONS)))))
        b=apply_frozen_priors(newn,newc,state,context)
        np.testing.assert_array_equal(a,b[:2]);np.testing.assert_array_equal(b[-1],context)


if __name__=='__main__':unittest.main()
