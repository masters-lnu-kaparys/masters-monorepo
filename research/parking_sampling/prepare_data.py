"""Build quality-controlled interval windows without evaluating sampling policies.

All times are seconds on the source's naive local civil calendar, not UTC.
The two DST-change dates are masked as specified by protocol v0.1.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import duckdb

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / 'docs/research/adaptive-sampling'
START = int((datetime(2019, 1, 1) - datetime(1970, 1, 1)).total_seconds())
END = int((datetime(2020, 1, 1) - datetime(1970, 1, 1)).total_seconds())

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def quote(value):
    return "'" + str(value).replace("'", "''") + "'"

def records(con, sql):
    result = con.execute(sql)
    keys = [v[0] for v in result.description]
    return [dict(zip(keys, row)) for row in result.fetchall()]

def local_second(value):
    return int((datetime.fromisoformat(value) - datetime(1970, 1, 1)).total_seconds())

def build_quality_tables(con, table='parsed'):
    """Shared exact sweep implementation, also used by small independent tests."""
    con.execute(f'''CREATE OR REPLACE TABLE valid AS
        SELECT bay, greatest(a, {START})::BIGINT a, least(b, {END})::BIGINT b, state
        FROM {table}
        WHERE bay > 0 AND a IS NOT NULL AND b IS NOT NULL AND state IS NOT NULL
          AND b > a AND a < {END} AND b > {START}''')
    con.execute('CREATE OR REPLACE TABLE bay_bounds AS SELECT bay,min(a) first_a,max(b) last_b FROM valid GROUP BY bay')
    points = [START, END]
    for day in ('2019-04-07', '2019-10-06'):
        t = local_second(day)
        points.extend([t, t + 86400])
    point_sql = ','.join(f'({t})' for t in points)
    con.execute(f'''CREATE OR REPLACE TABLE events AS
        SELECT bay,t,sum(d0)::BIGINT d0,sum(d1)::BIGINT d1 FROM (
          SELECT bay,a t, CASE WHEN state=0 THEN 1 ELSE 0 END d0, CASE WHEN state=1 THEN 1 ELSE 0 END d1 FROM valid
          UNION ALL
          SELECT bay,b t, CASE WHEN state=0 THEN -1 ELSE 0 END d0, CASE WHEN state=1 THEN -1 ELSE 0 END d1 FROM valid
          UNION ALL
          SELECT bay,t,0,0 FROM bay_bounds CROSS JOIN (VALUES {point_sql}) marker(t)
        ) GROUP BY bay,t''')
    con.execute(f'''CREATE OR REPLACE TABLE spans AS
        WITH running AS (
          SELECT bay,t a,lead(t) OVER w b,
            sum(d0) OVER (PARTITION BY bay ORDER BY t ROWS UNBOUNDED PRECEDING) n0,
            sum(d1) OVER (PARTITION BY bay ORDER BY t ROWS UNBOUNDED PRECEDING) n1
          FROM events WINDOW w AS (PARTITION BY bay ORDER BY t)
        ), labeled AS (
          SELECT r.*,CASE
            WHEN (a >= {local_second('2019-04-07')} AND a < {local_second('2019-04-08')})
              OR (a >= {local_second('2019-10-06')} AND a < {local_second('2019-10-07')}) THEN 'dst_mask'
            WHEN n0>0 AND n1>0 THEN 'conflict'
            WHEN n0=0 AND n1=0 AND (a<first_a OR a>=last_b) THEN 'outside_observed_span'
            WHEN n0=0 AND n1=0 THEN 'internal_gap'
            ELSE 'known' END quality
          FROM running r JOIN bay_bounds USING (bay) WHERE b>a
        )
        SELECT bay,a,b,n0,n1,quality,
          CASE WHEN quality='known' AND n0>0 THEN 0 WHEN quality='known' AND n1>0 THEN 1 ELSE NULL END::TINYINT state
        FROM labeled''')
    con.execute('''CREATE OR REPLACE TABLE clean_intervals AS
        WITH known AS (SELECT bay,a,b,state FROM spans WHERE quality='known'),
        change AS (
          SELECT *, CASE WHEN lag(b) OVER w = a AND lag(state) OVER w = state THEN 0 ELSE 1 END changed
          FROM known WINDOW w AS (PARTITION BY bay ORDER BY a)
        ), grouped AS (
          SELECT *, sum(changed) OVER (PARTITION BY bay ORDER BY a ROWS UNBOUNDED PRECEDING) group_id FROM change
        ) SELECT bay,min(a)::BIGINT a,max(b)::BIGINT b,state FROM grouped GROUP BY bay,group_id,state''')
    con.execute('''CREATE OR REPLACE TABLE segments AS
        WITH change AS (
          SELECT *, CASE WHEN lag(b) OVER (PARTITION BY bay ORDER BY a)=a THEN 0 ELSE 1 END changed FROM clean_intervals
        ), grouped AS (
          SELECT *,sum(changed) OVER (PARTITION BY bay ORDER BY a ROWS UNBOUNDED PRECEDING) segment_id FROM change
        ) SELECT bay,segment_id,min(a)::BIGINT a,max(b)::BIGINT b,count(*) intervals FROM grouped GROUP BY bay,segment_id''')

def build_windows(con, protocol, inspected_bays):
    all_bays = [v[0] for v in con.execute('SELECT bay FROM bay_bounds ORDER BY bay').fetchall()]
    reserved = {bay for bay in all_bays if str(bay) not in inspected_bays and int(hashlib.sha256(f'masters-parking-v1:{bay}'.encode()).hexdigest(), 16) % 5 == 0}
    con.execute('CREATE OR REPLACE TABLE assignments(bay BIGINT, previously_inspected BOOLEAN, reserved BOOLEAN)')
    con.executemany('INSERT INTO assignments VALUES (?,?,?)', [(b, str(b) in inspected_bays, b in reserved) for b in all_bays])
    ranges = [('train', protocol['data']['train_range']), ('validation', protocol['data']['validation_range']), ('late', protocol['data']['final_test_range'])]
    values = ','.join(f"({quote(name)},{local_second(lo)},{local_second(hi)})" for name,(lo,hi) in ranges)
    con.execute(f'''CREATE OR REPLACE TABLE windows AS
        WITH clipped AS (
          SELECT s.bay,s.segment_id,greatest(s.a,p.lo)::BIGINT a,least(s.b,p.hi)::BIGINT b,
            p.period,x.previously_inspected,x.reserved
          FROM segments s JOIN assignments x USING (bay)
          CROSS JOIN (VALUES {values}) p(period,lo,hi)
          WHERE s.b>p.lo AND s.a<p.hi
        ) SELECT *,b-a >= {int(protocol['data']['minimum_continuous_window_days'])*86400} is_primary,
          CASE WHEN reserved AND period='late' THEN 'quarantine_final_test'
               WHEN reserved AND period='train' THEN 'quarantine_train_reserved'
               WHEN reserved AND period='validation' THEN 'quarantine_validation_unused'
               WHEN period='late' THEN 'exploratory_late_development'
               ELSE period || '_development' END split_role,
          substr(sha256(bay::VARCHAR || ':' || a::VARCHAR || ':' || b::VARCHAR || ':' || period),1,24) window_id
        FROM clipped WHERE b-a >= 86400''')
    return reserved

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workdir', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, default=DOCS/'protocol.json')
    parser.add_argument('--bay-batch-size',type=int,default=32)
    args = parser.parse_args()
    work = args.workdir.resolve()
    source = json.loads((work/'source/source-manifest.json').read_text(encoding='utf-8'))
    protocol = json.loads(args.protocol.read_text(encoding='utf-8'))
    evidence = json.loads((DOCS/'phase1-evidence.json').read_text(encoding='utf-8'))
    inspected = set(evidence['pilot_prefix']['all_inspected_bay_ids'])
    out = work/'prepared'
    out.mkdir(exist_ok=True)
    temporary = work/'duckdb-temp'
    temporary.mkdir(exist_ok=True)
    con = duckdb.connect(str(work/'preparation.duckdb'))
    con.execute("SET memory_limit='1GB'")
    con.execute('SET threads=2')
    con.execute('SET preserve_insertion_order=false')
    con.execute(f'SET temp_directory={quote(temporary.as_posix())}')
    started = time.monotonic()
    parsed = work/'parsed.parquet'
    receipt_path=work/'parsed-receipt.json'
    receipt=json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {}
    parser_contract='explicit_comma_double_quote_strict_all_varchar_timestamp_mdy12h_v1'
    if not parsed.exists() or receipt.get('source_csv_sha256')!=source['csv_sha256'] or receipt.get('parser_contract')!=parser_contract:
        print('Parsing all CSV records into compact four-column Parquet', flush=True)
        csv_path = work/'source'/source['csv_path']
        parsed_stage=work/'parsed.partial.parquet'
        con.execute(f'''COPY (
          SELECT try_cast(trim(BayId) AS BIGINT) bay,
            epoch(try_strptime(trim(ArrivalTime),'%m/%d/%Y %I:%M:%S %p'))::BIGINT a,
            epoch(try_strptime(trim(DepartureTime),'%m/%d/%Y %I:%M:%S %p'))::BIGINT b,
            CASE lower(trim(VehiclePresent)) WHEN 'true' THEN 1 WHEN 'false' THEN 0 ELSE NULL END::TINYINT state
          FROM read_csv({quote(csv_path.as_posix())},header=true,all_varchar=true,strict_mode=true,parallel=true,delim=',',quote='"',escape='"')
        ) TO {quote(parsed_stage.as_posix())} (FORMAT PARQUET,COMPRESSION ZSTD)''')
        parsed_stage.replace(parsed)
        receipt_path.write_text(json.dumps({'source_csv_sha256':source['csv_sha256'],'parser_contract':parser_contract,'parsed_sha256':sha256(parsed)},indent=2)+'\n',encoding='utf-8')
    con.execute(f'CREATE OR REPLACE VIEW parsed AS SELECT * FROM read_parquet({quote(parsed.as_posix())})')
    raw = records(con,f'''SELECT count(*) source_rows,count(DISTINCT bay) distinct_nonnull_bays,
      count(*) FILTER (WHERE bay IS NULL OR bay<=0) invalid_bay_rows,
      count(*) FILTER (WHERE a IS NULL OR b IS NULL) invalid_timestamp_rows,
      count(*) FILTER (WHERE state IS NULL) invalid_state_rows,
      count(*) FILTER (WHERE b<=a) nonpositive_interval_rows,
      count(*) FILTER (WHERE b>a AND b-a<60) positive_raw_intervals_under_60s,
      count(*) FILTER (WHERE b>a AND (a<{START} OR b>{END})) positive_intervals_requiring_year_clip,
      count(*) FILTER (WHERE b>a AND (b<={START} OR a>={END})) positive_intervals_outside_year
      FROM parsed''')[0]
    print(json.dumps({'raw_parse':raw,'elapsed_seconds':round(time.monotonic()-started,1)}),flush=True)
    print('Exact interval sweep: conflicts and gaps remain unknown',flush=True)
    # Bays are independent: batching bounds memory without changing the sweep.
    con.execute(f'''CREATE OR REPLACE TABLE valid_all AS
      SELECT bay,greatest(a,{START})::BIGINT a,least(b,{END})::BIGINT b,state FROM parsed
      WHERE bay>0 AND a IS NOT NULL AND b IS NOT NULL AND state IS NOT NULL
        AND b>a AND a<{END} AND b>{START} ORDER BY bay,a''')
    bay_ids=[v[0] for v in con.execute('SELECT DISTINCT bay FROM valid_all ORDER BY bay').fetchall()]
    con.execute('CREATE OR REPLACE TABLE clean_intervals_all(bay BIGINT,a BIGINT,b BIGINT,state TINYINT)')
    con.execute('CREATE OR REPLACE TABLE segments_all(bay BIGINT,segment_id BIGINT,a BIGINT,b BIGINT,intervals BIGINT)')
    con.execute('''CREATE OR REPLACE TABLE quality_all(bay BIGINT,quality VARCHAR,atomic_spans BIGINT,
      seconds_value BIGINT,consistent_overlap_seconds BIGINT)''')
    size=args.bay_batch_size
    if size<=0:
        raise ValueError('bay-batch-size must be positive')
    for begin in range(0,len(bay_ids),size):
        group=bay_ids[begin:begin+size]
        con.execute(f'CREATE OR REPLACE VIEW parsed_chunk AS SELECT * FROM valid_all WHERE bay BETWEEN {group[0]} AND {group[-1]}')
        build_quality_tables(con,'parsed_chunk')
        con.execute('INSERT INTO clean_intervals_all SELECT * FROM clean_intervals')
        con.execute('INSERT INTO segments_all SELECT * FROM segments')
        con.execute('''INSERT INTO quality_all SELECT bay,quality,count(*),sum(b-a)::BIGINT,
          sum(CASE WHEN quality='known' AND (n0>1 OR n1>1) THEN b-a ELSE 0 END)::BIGINT
          FROM spans GROUP BY bay,quality''')
        if begin//size % 8==0 or begin+size>=len(bay_ids):
            print(f'sweep bays {min(begin+size,len(bay_ids))}/{len(bay_ids)}, elapsed={time.monotonic()-started:.1f}s',flush=True)
            con.execute('CHECKPOINT')
    con.execute('DROP VIEW parsed_chunk')
    for name in ('valid','clean_intervals','segments'):
        con.execute(f'DROP TABLE {name}')
        con.execute(f'ALTER TABLE {name}_all RENAME TO {name}')
    con.execute('CREATE OR REPLACE TABLE bay_bounds AS SELECT bay,min(a) first_a,max(b) last_b FROM valid GROUP BY bay')
    quality = records(con,'SELECT quality,sum(atomic_spans)::BIGINT atomic_spans,sum(seconds_value)::BIGINT AS "seconds" FROM quality_all GROUP BY quality ORDER BY quality')
    source_coverage = records(con,'''SELECT count(*) valid_interval_rows,count(DISTINCT bay) bays FROM valid''')[0]
    same_overlap = records(con,'SELECT sum(consistent_overlap_seconds)::BIGINT AS "seconds" FROM quality_all')[0]
    con.execute(f'''COPY (SELECT bay,quality,seconds_value AS "seconds" FROM quality_all ORDER BY bay,quality)
      TO {quote((out/'quality-by-bay.csv').as_posix())} (HEADER,DELIMITER ',')''')
    reserved = build_windows(con,protocol,inspected)
    con.execute(f'''COPY (SELECT * FROM assignments ORDER BY bay) TO {quote((out/'bay-assignments.csv').as_posix())} (HEADER,DELIMITER ',')''')
    con.execute(f'''COPY (SELECT * FROM windows ORDER BY split_role,bay,a) TO {quote((out/'windows.parquet').as_posix())} (FORMAT PARQUET,COMPRESSION ZSTD)''')
    window_summary = records(con,'''SELECT split_role,is_primary,count(*) AS "windows",count(DISTINCT bay) bays,sum(b-a)::BIGINT AS "seconds"
      FROM windows GROUP BY split_role,is_primary ORDER BY split_role,is_primary''')
    files = {}
    for (role,) in con.execute('SELECT DISTINCT split_role FROM windows ORDER BY split_role').fetchall():
        dest = out / f'{role}.parquet'
        print(f'Writing {role}; no policy metrics',flush=True)
        con.execute(f'''COPY (
          SELECT w.bay,w.window_id,w.a window_start,w.b window_end,w.is_primary,
            greatest(c.a,w.a)::BIGINT start_local_seconds,least(c.b,w.b)::BIGINT end_local_seconds,c.state
          FROM clean_intervals c JOIN windows w ON c.bay=w.bay AND c.b>w.a AND c.a<w.b
          WHERE w.split_role={quote(role)} ORDER BY w.bay,w.a,c.a
        ) TO {quote(dest.as_posix())} (FORMAT PARQUET,COMPRESSION ZSTD)''')
        n = con.execute(f'SELECT count(*) FROM read_parquet({quote(dest.as_posix())})').fetchone()[0]
        files[role] = {'path':dest.relative_to(ROOT).as_posix(),'bytes':dest.stat().st_size,'sha256':sha256(dest),'interval_rows':n,
          'policy_results_opened':False,'quarantined':role.startswith('quarantine_')}
    report = {
      'prepared_at_utc':datetime.now(timezone.utc).isoformat(),'protocol_id':protocol['protocol_id'],
      'protocol_sha256':sha256(args.protocol),'preparation_code_sha256':sha256(Path(__file__)),
      'duckdb_version':duckdb.__version__,'time_basis':'naive local civil seconds since 1970-01-01; not UTC',
      'source_archive_sha256':source['archive_sha256'],'source_csv_sha256':source['csv_sha256'],
      'zip_crc_verified':source['csv_crc_verified'],'raw_parse':raw,'valid_after_clipping':source_coverage,
      'quality_year_grid':quality,'known_same_state_overlap_seconds':same_overlap['seconds'],
      'same_state_overlap_policy':'consistent overlapping observations merged; no claim every overlap is an exact duplicate',
      'reserved_bays':sorted(reserved),'inspected_bays_excluded':sorted(inspected,key=int),
      'window_summary':window_summary,'files':files,
      'window_manifest':{'path':(out/'windows.parquet').relative_to(ROOT).as_posix(),'sha256':sha256(out/'windows.parquet')},
      'assignments':{'path':(out/'bay-assignments.csv').relative_to(ROOT).as_posix(),'sha256':sha256(out/'bay-assignments.csv')},
      'final_policy_metrics_evaluated':False,'elapsed_seconds':round(time.monotonic()-started,2),
    }
    report['final_primary_test_bays'] = con.execute("SELECT count(DISTINCT bay) FROM windows WHERE split_role='quarantine_final_test' AND is_primary").fetchone()[0]
    report['planned_minimum_final_test_bays_met'] = report['final_primary_test_bays']>=protocol['data']['minimum_final_test_bays_for_planned_group_analysis']
    con.execute('CHECKPOINT')
    con.close()
    (out/'data-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('reserved_bays','inspected_bays_excluded')},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':
    main()
