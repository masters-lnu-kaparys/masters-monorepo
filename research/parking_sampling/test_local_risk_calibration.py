import unittest
import numpy as np
from local_risk_calibration import calibrate,realized_by_bay


class CalibrationTests(unittest.TestCase):
    def test_mixture_meets_full_schedule_risk_budgets(self):
        raw=np.zeros((4,2,17));raw[:,:,0]=1000;raw[:,0,1:4]=[50,20,20];raw[:,1,1:4]=[200,1,1]
        ref=np.zeros((4,17));ref[:,0]=1000;ref[:,1:4]=[100,10,10]
        answer=calibrate(raw,ref,.9)
        np.testing.assert_allclose(answer['expected_raw'][:,2:4],9)
        self.assertAlmostEqual(answer['weights'].sum(),1.)

    def test_zero_miss_constraint_cannot_average_positive_misses_away(self):
        raw=np.zeros((4,2,17));raw[:,:,0]=1000;raw[:,0,1:4]=[50,5,5];raw[:,1,1:4]=[100,10,10];raw[:,0,14]=1
        ref=raw[:,1,:].copy();answer=calibrate(raw,ref,1,True)
        self.assertAlmostEqual(answer['weights'][0],0)

    def test_realized_choice_uses_bay_and_seed_only(self):
        values=np.zeros((2,3,17));values[0,:,1]=1;values[1,:,1]=2
        a,choice=realized_by_bay(values,[1,2,3],['a','b'],{'a':.5,'b':.5})
        aa,c2=realized_by_bay(values[:,[2,0,1]], [3,1,2],['a','b'],{'b':.5,'a':.5})
        self.assertEqual(choice,[c2[1],c2[2],c2[0]])
        np.testing.assert_array_equal(a,aa[[1,2,0]])

    def test_invalid_exposure_rejected(self):
        r=np.ones((4,2,17));ref=np.ones((4,17));r[0,0,0]=2
        with self.assertRaises(ValueError):calibrate(r,ref)


if __name__=='__main__':unittest.main()
