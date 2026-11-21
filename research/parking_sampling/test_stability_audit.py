import unittest
import numpy as np
from data_access import Bundle
from stability_audit import (PAIR_DTYPE,extract_pairs,minimum_diagnostics,temporal_diagnostics,
    timing_diagnostics,replay_all_starts,civil_seconds)
from simulation import reference_simulate,context

class StabilityAuditTests(unittest.TestCase):
    def test_pair_extraction_uses_complete_adjacent_durations_and_censors_edges(self):
        d=Bundle(np.array([1,15,75,90,120,200]),np.array([0,1,0,1,0,1]),np.array([0,6]),
          np.array([0]),np.array([0]),np.array([7]),('w',),{})
        values=extract_pairs(d)
        self.assertEqual(len(values),1)
        self.assertEqual(tuple(values[0][n] for n in ('bay','p','a','b','B','D','sum')),(7,1,15,75,14,60,74))

    def test_minimum_influence_distinguishes_unique_and_duplicated_support(self):
        x=np.zeros(3,dtype=PAIR_DTYPE);x['sum']=[72,73,75];x['bay']=[1,2,3];x['window']=[0,1,2]
        unique=minimum_diagnostics(x,np.array([1,2,3]),100)
        self.assertEqual(unique['minimum_support_bays'],[1])
        self.assertEqual(unique['leave_one_pair_out_changed_count'],1)
        self.assertEqual(unique['leave_group_out']['bay']['changed_removals'],[{'removed':1,'cap_seconds':73}])
        x['sum'][1]=72
        tied=minimum_diagnostics(x,np.array([1,2,3]),100)
        self.assertEqual(tied['leave_one_pair_out_changed_count'],0)
        self.assertEqual(tied['leave_group_out']['bay']['changed_removals'],[])

    def test_temporal_calibration_never_reads_the_next_month_for_its_cap(self):
        x=np.zeros(3,dtype=PAIR_DTYPE);x['D']=60;x['sum']=[75,72,70]
        x['p']=[civil_seconds(2019,1)+10,civil_seconds(2019,2)+10,civil_seconds(2019,3)+10];x['b']=x['p']+x['sum']
        values=temporal_diagnostics(x)
        self.assertEqual(values[0]['cap_seconds'],75)
        self.assertEqual(values[0]['following_risky_pairs'],1)
        self.assertEqual(values[1]['cap_seconds'],72)
        # A pair ending exactly at the cutoff cannot calibrate the prefix.
        x['b'][0]=civil_seconds(2019,2)
        self.assertEqual(temporal_diagnostics(x)[0]['cap_seconds'],60)

    def test_timing_diagnostic_expands_target_eligibility_and_preserves_strictness(self):
        x=np.zeros(3,dtype=PAIR_DTYPE);x['D']=[60,58,60];x['sum']=[72,73,74];x['bay']=[1,2,3]
        rows=timing_diagnostics(x)
        self.assertEqual(rows[0]['candidate_risky_pairs'],0)
        self.assertEqual(rows[1]['candidate_risky_pairs'],2)
        self.assertFalse(rows[1]['actual_misses_inferred'])

    def test_enumerated_phase_replay_matches_independent_simulator(self):
        rng=np.random.default_rng(144)
        for _ in range(5):
            ends=np.cumsum(rng.integers(1,350,size=20));states=(np.arange(20)+int(rng.integers(2)))%2
            table=np.r_[np.tile([30,30,45,75,75,75],4),np.tile([30,30,60,60,60,60],4)]
            values=replay_all_starts(ends,states,0,table,count=30)
            for phase in range(30):
                expected=reference_simulate(ends,states,phase,lambda o:(int(table[context(o,False,True)]),False))[0]
                np.testing.assert_array_equal(values[phase],expected)

if __name__=='__main__':unittest.main(verbosity=2)
