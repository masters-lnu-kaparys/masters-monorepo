"""Verify data integrity and separation; deliberately computes no policy metrics."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime,timezone
import hashlib
import json
from itertools import islice
from pathlib import Path

import duckdb
from prepare_data import ROOT,START,END,quote,sha256

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workdir',type=Path,required=True)
    args=parser.parse_args()
    work=args.workdir.resolve()
    prepared=work/'prepared'
    data=json.loads((prepared/'data-manifest.json').read_text(encoding='utf-8'))
    con=duckdb.connect()
    con.execute("SET memory_limit='1GB'")
    con.execute('SET threads=2')
    con.execute(f"CREATE VIEW windows AS SELECT * FROM read_parquet({quote((prepared/'windows.parquet').as_posix())})")
    checks={
      'zip_crc_passed':data['zip_crc_verified'],
      'year_grid_complete':sum(v['seconds'] for v in data['quality_year_grid'])==data['valid_after_clipping']['bays']*(END-START),
      'enough_final_test_bays':data['planned_minimum_final_test_bays_met'],
      'no_final_policy_metrics':data['final_policy_metrics_evaluated'] is False,
      'no_seen_bays_in_final':con.execute("SELECT count(*) FROM windows WHERE split_role='quarantine_final_test' AND previously_inspected").fetchone()[0]==0,
      'no_reserved_bays_in_validation':con.execute("SELECT count(*) FROM windows WHERE split_role='validation_development' AND reserved").fetchone()[0]==0,
      'unique_window_ids':con.execute('SELECT count(*)=count(DISTINCT window_id) FROM windows').fetchone()[0],
      'valid_window_lengths':con.execute('SELECT bool_and(b-a>=86400 AND is_primary=(b-a>=7*86400)) FROM windows').fetchone()[0],
    }
    receipt=json.loads((work/'parsed-receipt.json').read_text(encoding='utf-8'))
    checks['parsed_cache_hash_matches_receipt']=sha256(work/'parsed.parquet')==receipt['parsed_sha256']
    evidence=json.loads((ROOT/'docs/research/adaptive-sampling/phase1-evidence.json').read_text(encoding='utf-8'))
    old_prefix=ROOT/evidence['pilot_prefix']['path']
    source_manifest=json.loads((work/'source/source-manifest.json').read_text(encoding='utf-8'))
    with old_prefix.open(encoding='utf-8-sig',newline='') as old, (work/'source'/source_manifest['csv_path']).open(encoding='utf-8-sig',newline='') as new:
        same=True;matched=0
        for old_row,new_row in zip(csv.DictReader(old),islice(csv.DictReader(new),evidence['pilot_prefix']['rows']),strict=True):
            matched+=1
            if old_row!=new_row:
                same=False
                break
    checks['old_prefix_matches_current_full_source']=same and matched==evidence['pilot_prefix']['rows']
    per_file={}
    for role,info in data['files'].items():
        path=ROOT/info['path']
        con.execute(f'CREATE OR REPLACE VIEW current_intervals AS SELECT * FROM read_parquet({quote(path.as_posix())})')
        result={
          'sha256_matches':sha256(path)==info['sha256'],
          'row_count_matches':con.execute('SELECT count(*) FROM current_intervals').fetchone()[0]==info['interval_rows'],
          'intervals_positive_within_window':con.execute('SELECT bool_and(end_local_seconds>start_local_seconds AND start_local_seconds>=window_start AND end_local_seconds<=window_end AND state IN (0,1)) FROM current_intervals').fetchone()[0],
          'exact_coverage_and_no_overlap':con.execute('''WITH lagged AS (
            SELECT *,lag(end_local_seconds) OVER (PARTITION BY window_id ORDER BY start_local_seconds) prev_end,
              lag(state) OVER (PARTITION BY window_id ORDER BY start_local_seconds) prev_state FROM current_intervals
          ), summary AS (
            SELECT window_id,min(start_local_seconds) a,max(end_local_seconds) b,
              min(window_start) wa,max(window_end) wb,sum(end_local_seconds-start_local_seconds) covered,
              bool_and(prev_end IS NULL OR prev_end=start_local_seconds) continuous,
              bool_and(prev_state IS NULL OR prev_state<>state) merged
            FROM lagged GROUP BY window_id
          ) SELECT bool_and(a=wa AND b=wb AND covered=wb-wa AND continuous AND merged) FROM summary''').fetchone()[0],
          'manifest_membership':con.execute(f'''SELECT count(*) FROM current_intervals i
            LEFT JOIN windows w USING (window_id)
            WHERE w.window_id IS NULL OR w.split_role<>{quote(role)} OR w.bay<>i.bay OR w.a<>i.window_start OR w.b<>i.window_end''').fetchone()[0]==0,
        }
        per_file[role]=result
        print(f'verified {role}: {all(result.values())}',flush=True)
    assignments=list(con.execute('SELECT DISTINCT bay,reserved,previously_inspected FROM windows').fetchall())
    checks['hash_assignment_rule']=all(
      reserved == (not inspected and int(hashlib.sha256(f'masters-parking-v1:{bay}'.encode()).hexdigest(),16)%5==0)
      for bay,reserved,inspected in assignments)
    ranges={
      'train_development':('train',), 'quarantine_train_reserved':('train',),
      'validation_development':('validation',),'quarantine_validation_unused':('validation',),
      'exploratory_late_development':('late',),'quarantine_final_test':('late',),
    }
    checks['calendar_roles_match']=all(con.execute(f'SELECT count(*) FROM windows WHERE split_role={quote(role)} AND period<>{quote(period[0])}').fetchone()[0]==0 for role,period in ranges.items())
    report={'verified_at_utc':datetime.now(timezone.utc).isoformat(),'all_passed':all(checks.values()) and all(all(v.values()) for v in per_file.values()),'checks':checks,'per_file':per_file,'no_sampling_policy_executed':True}
    (prepared/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    raise SystemExit(0 if report['all_passed'] else 1)

if __name__=='__main__':
    main()
