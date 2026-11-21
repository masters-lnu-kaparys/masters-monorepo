import unittest
import numpy as np
from local_risk_calibration import calibrate as previous
from local_risk_calibration_v3 import calibrate


class ExactExposureTests(unittest.TestCase):
    def test_invariant_exposure_preserved_without_altering_allocation_or_costs(self):
        raw=np.zeros((4,3,17));raw[:,:,0]=1943271987;raw[:,0,1:4]=[50,20,20];raw[:,1,1:4]=[200,1,1];raw[:,2,1:4]=[100,10,10]
        ref=raw[:,2].copy();old=previous(raw,ref);new=calibrate(raw,ref)
        np.testing.assert_array_equal(old['weights'],new['weights'])
        np.testing.assert_array_equal(old['expected_raw'][:,1:],new['expected_raw'][:,1:])
        np.testing.assert_array_equal(new['expected_raw'][:,0],ref[:,0])

    def test_same_strict_constraint_solution_as_preserved_version(self):
        raw=np.zeros((4,2,17));raw[:,:,0]=1000;raw[:,0,1:4]=[50,5,5];raw[:,1,1:4]=[100,10,10];raw[:,0,14]=1
        ref=raw[:,1].copy()
        np.testing.assert_array_equal(previous(raw,ref,1,True)['weights'],calibrate(raw,ref,1,True)['weights'])


if __name__=='__main__':unittest.main()
