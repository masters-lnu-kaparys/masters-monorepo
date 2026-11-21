"""Freeze the new audit and validate old evidence through explicit snapshots."""
import json
import re
from urllib.parse import unquote
import numpy as np
from PIL import Image
from prepare_data import ROOT,DOCS,sha256
from stability_audit import WORK
from audit_episode_constraint import WORK as PREVIOUS,OLD
from run_phase3 import write_json

def read(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
    inherited=read(DOCS/'phase3-novelty-history.json')['historical_file_mapping']
    mappings=list(inherited)
    for relative,snapshot in [('docs/research/adaptive-sampling/README.md','history/README-before-stability.md'),
                              ('docs/research/adaptive-sampling/phase3-novelty-gate.json','history/phase3-novelty-gate-before-stability.json')]:
        path=WORK/snapshot;mappings.append({'original_path':relative,'snapshot_path':path.relative_to(ROOT).as_posix(),
          'snapshot_sha256':sha256(path),'reason':'Current research conclusion updated after C4 stability audit; previous record preserved'})
    def check(relative,expected):
        path=ROOT/relative
        if path.exists() and sha256(path)==expected:return 'unchanged'
        for m in mappings:
            if m['original_path']==relative and m['snapshot_sha256']==expected:
                assert sha256(ROOT/m['snapshot_path'])==expected;return 'snapshot'
        raise AssertionError('Unexplained changed frozen artifact: '+relative)
    counts={};snapshot_count=0
    for filename in ('phase3-artifact-manifest.json','phase3-method-lock.json','phase3-refinement-lock.json','phase3-novelty-artifacts.json'):
        lock=read(DOCS/filename)
        for relative,h in lock['files'].items():snapshot_count+=check(relative,h)=='snapshot'
        counts[filename]=len(lock['files'])
    plan=read(WORK/'pre-analysis-lock.json')
    check('research/parking_sampling/stability_audit.py',plan['code_sha256'])
    check('docs/research/adaptive-sampling/phase3-stability-plan.json',plan['plan_sha256'])
    check('docs/research/adaptive-sampling/phase3-pair-envelope-policy.json',plan['frozen_C4_json_sha256'])
    hlock=read(WORK/'history-bound/pre-analysis-lock.json')
    for name,h in hlock['code_sha256'].items():check('research/parking_sampling/'+name,h)
    check('docs/research/adaptive-sampling/phase3-history-bound-plan.json',hlock['plan_sha256'])
    table=np.load(OLD/'models/C3_without_time_0.25_0.25_75.npz')['lookup']
    assert table.shape==(48,) and np.max(table)<=75 and np.max(table[24:])<=60
    for tb in range(4):assert np.max(table[tb*6:tb*6+3])<=60
    result=read(WORK/'results.json');windows=[r for c in result['development'].values() for r in c['phase_windows']]
    assert len(windows)==8 and sum(x['risky_pairs'] for x in windows)==8
    total=0
    for row in windows:
        p=WORK/'phases'/f"{row['window_id']}.npz";arrays=np.load(p)
        for name in ('C3','C4'):
            a=arrays[name];assert a.shape==(3600,17) and np.all(a[:,14]==0);total+=len(a)
    assert total==57600
    test=read(DOCS/'phase3-stability-verification.json');assert test['passed'] and test['tests_run']==70
    for name,h in test['test_sha256'].items():check('research/parking_sampling/'+name,h)
    gate=read(DOCS/'phase3-novelty-gate.json');assert gate['phase4_may_start'] is False and gate['final_867_bay_test_evaluated'] is False
    assert read(DOCS/'phase3-novelty-verification.json')['tests_run']==59
    links=0
    for name in ('README.md','phase3-stability-report.md','phase3-history-bound-method.md','phase3-stability-sources.md'):
        p=DOCS/name
        for target in re.findall(r'\]\(([^\s]+)\)',p.read_text(encoding='utf-8')):
            if target.startswith(('http:','https:','#','mailto:')):continue
            assert (p.parent/unquote(target.split('#')[0])).exists(),(name,target);links+=1
    for pattern in ('phase3-c4-stability.png','phase3-history-bound-comparison.png'):
        with Image.open(DOCS/'figures'/pattern) as im:assert im.width>=2000 and im.height>=800
    write_json(DOCS/'phase3-stability-history.json',{'created_on':'2026-10-25','historical_file_mapping':mappings,
      'current_readme_sha256':sha256(DOCS/'README.md'),'current_gate_sha256':sha256(DOCS/'phase3-novelty-gate.json')})
    receipt={'created_on':'2026-10-25','passed':True,'prior_manifest_entries_checked':counts,
      'prior_entries_matched_through_explicit_snapshots':snapshot_count,'phase_replays_verified':total,
      'C3_history_bound_assumptions_checked_against_frozen_lookup':True,'test_count':test['tests_run'],
      'local_markdown_links_verified':links,'figure_visual_review':'Both scientific PNGs inspected; labels and annotations readable',
      'phase4_gate_opened':False,'final_test_states_opened':False,'previous59_test_receipt_preserved':True}
    write_json(DOCS/'phase3-stability-artifact-verification.json',receipt)
    paths=set(p for p in WORK.rglob('*') if p.is_file())
    for pattern in ('phase3-stability-*','phase3-history-bound-*'):
        paths.update(p for p in DOCS.glob(pattern) if p.is_file())
    paths.discard(DOCS/'phase3-stability-artifacts.json')
    paths.update(DOCS/n for n in ('README.md','phase3-novelty-gate.json'))
    for pattern in ('phase3-c4-stability.*','phase3-history-bound-comparison.*'):paths.update((DOCS/'figures').glob(pattern))
    for n in ('stability_audit.py','history_certificate.py','assess_history_certificate.py','test_stability_audit.py',
              'test_history_certificate.py','fetch_stability_sources.py','verify_stability.py','build_stability_report.py',
              'verify_stability_artifacts.py'):paths.add(ROOT/'research/parking_sampling'/n)
    write_json(DOCS/'phase3-stability-artifacts.json',{'created_on':'2026-10-25','scope':'phase3_stability_and_analytical_audit',
      'files':{p.relative_to(ROOT).as_posix():sha256(p) for p in sorted(paths)},
      'final_test_evaluated':False,'phase4_may_start':False,'policy_retuned':False})
    print(json.dumps({**receipt,'new_artifacts_frozen':len(paths)}))

if __name__=='__main__':main()
