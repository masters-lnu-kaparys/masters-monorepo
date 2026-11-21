import unittest
from calibrated_schedule import CalibratedSchedule
from simulation import Observation


class RuntimeTests(unittest.TestCase):
    def payload(self):
        return {'schema_version':1,'allocation_seed':20261025,'observed_run_edges_seconds':[60,300,900,3600,14400],
          'component_weights':{'a':1.},'components':{'a':{'pooled_fallback':[60]*48,'bay_tables':{'2':list(range(1,49))}}}}

    def test_paid_history_selects_the_correct_clock_age_state_context(self):
        p=CalibratedSchedule(self.payload())
        self.assertEqual(p.next_pause(2,Observation(21600+900,1,21600)),(1*4+1)*6+3+1)

    def test_new_bay_fallback_and_stable_known_id_assignment(self):
        p=CalibratedSchedule(self.payload());self.assertEqual(p.next_pause(99,Observation(0,0,0)),60)
        self.assertEqual(p.component_for_bay(2),p.component_for_bay(2))

    def test_invalid_table_and_history_are_rejected(self):
        cfg=self.payload();cfg['components']['a']['pooled_fallback'][0]=0
        with self.assertRaises(ValueError):CalibratedSchedule(cfg)
        p=CalibratedSchedule(self.payload())
        with self.assertRaises(ValueError):p.next_pause(2,Observation(0,1,1))


if __name__=='__main__':unittest.main()
