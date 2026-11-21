"""Independent small-case checks of data semantics before the full data run."""
from datetime import datetime
import hashlib
import json
import random
import unittest

import duckdb

from prepare_data import DOCS, END, START, build_quality_tables, build_windows, local_second

class PreparationTests(unittest.TestCase):
    def prepare(self, rows):
        con = duckdb.connect()
        self.addCleanup(con.close)
        con.execute('CREATE TABLE parsed(bay BIGINT,a BIGINT,b BIGINT,state TINYINT)')
        con.executemany('INSERT INTO parsed VALUES (?,?,?,?)',rows)
        build_quality_tables(con)
        return con

    def test_consistent_overlap_and_adjacent_rows_merge(self):
        t=START+86400
        con=self.prepare([(1,t,t+20,0),(1,t+10,t+30,0),(1,t+30,t+40,0)])
        self.assertEqual(con.execute('SELECT bay,a,b,state FROM clean_intervals ORDER BY a').fetchall(),[(1,t,t+40,0)])

    def test_conflicting_overlap_is_unknown(self):
        t=START+86400
        con=self.prepare([(1,t,t+20,0),(1,t+10,t+30,1)])
        self.assertEqual(con.execute('SELECT a,b,state FROM clean_intervals ORDER BY a').fetchall(),[(t,t+10,0),(t+20,t+30,1)])
        self.assertEqual(con.execute("SELECT sum(b-a) FROM spans WHERE quality='conflict'").fetchone()[0],10)

    def test_gap_splits_segments_without_forward_fill(self):
        t=START+86400
        con=self.prepare([(1,t,t+10,0),(1,t+20,t+30,0)])
        self.assertEqual(con.execute('SELECT count(*) FROM segments').fetchone()[0],2)
        self.assertEqual(con.execute("SELECT sum(b-a) FROM spans WHERE quality='internal_gap'").fetchone()[0],10)

    def test_invalid_records_are_excluded_and_year_is_clipped(self):
        con=self.prepare([(1,START-20,START+20,1),(1,START+30,START+30,0),(None,START,START+40,0),(1,START,START+40,None),(1,END-20,END+20,0)])
        self.assertEqual(con.execute('SELECT count(*) FROM valid').fetchone()[0],2)
        self.assertEqual(con.execute('SELECT min(a),max(b) FROM valid').fetchone(),(START,END))

    def test_dst_day_is_masked_and_splits_continuity(self):
        t=local_second('2019-04-06')
        con=self.prepare([(1,t,t+3*86400,1)])
        self.assertEqual(con.execute('SELECT a,b FROM segments ORDER BY a').fetchall(),[(t,t+86400),(t+2*86400,t+3*86400)])

    def test_sweep_matches_brute_force_on_random_overlaps(self):
        rng=random.Random(20261018)
        t=START+86400
        for _ in range(20):
            rows=[]
            for _ in range(15):
                a=rng.randrange(100);b=a+rng.randrange(1,30)
                rows.append((1,t+a,t+b,rng.randrange(2)))
            con=self.prepare(rows)
            intervals=con.execute('SELECT a,b,state FROM clean_intervals ORDER BY a').fetchall()
            for second in range(130):
                active={s for bay,a,b,s in rows if a<=t+second<b}
                expected=next(iter(active)) if len(active)==1 else None
                got=next((s for a,b,s in intervals if a<=t+second<b),None)
                self.assertEqual(got,expected)

    def test_half_open_boundaries(self):
        t=START+86400
        con=self.prepare([(1,t,t+10,0),(1,t+10,t+20,1)])
        state=con.execute('SELECT state FROM clean_intervals WHERE a<=? AND b>?',[t+10,t+10]).fetchone()[0]
        self.assertEqual(state,1)

    def test_reserved_split_and_calendar_clipping(self):
        protocol=json.loads((DOCS/'protocol.json').read_text(encoding='utf-8'))
        bays=[b for b in range(1000,1100) if int(hashlib.sha256(f'masters-parking-v1:{b}'.encode()).hexdigest(),16)%5==0][:2]
        rows=[]
        for bay in bays:
            rows.extend([(bay,local_second('2019-06-01'),local_second('2019-08-01'),0),
                         (bay,local_second('2019-10-10'),local_second('2019-10-20'),1)])
        con=self.prepare(rows)
        reserved=build_windows(con,protocol,{str(bays[0])})
        self.assertNotIn(bays[0],reserved)
        self.assertIn(bays[1],reserved)
        self.assertEqual(con.execute("SELECT count(*) FROM windows WHERE reserved AND split_role='validation_development'").fetchone()[0],0)
        self.assertEqual(con.execute("SELECT count(*) FROM windows WHERE previously_inspected AND split_role='quarantine_final_test'").fetchone()[0],0)
        self.assertEqual(con.execute("SELECT min(a),max(b) FROM windows WHERE period='train'").fetchone(),(local_second('2019-06-01'),local_second('2019-07-01')))

if __name__=='__main__':
    unittest.main(verbosity=2)
