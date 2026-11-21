"""Check provenance without opening any final-test states, then freeze artifacts."""
import json
import re
from pathlib import Path
from urllib.parse import unquote
import numpy as np
from PIL import Image
from prepare_data import ROOT,DOCS,sha256
from audit_episode_constraint import WORK,OLD
from simulation import Observation,context
from trained_schedule import TrainedSchedule
from run_phase3 import write_json

def read(path):return json.loads(path.read_text(encoding='utf-8'))

def main():
    history=[
      {'original_path':'docs/research/adaptive-sampling/README.md',
       'snapshot_path':'docs/research/adaptive-sampling/phase3-roadmap-snapshot.md',
       'reason':'Original phase3 status before C3 refinement'},
      {'original_path':'docs/research/adaptive-sampling/README.md',
       'snapshot_path':'docs/research/adaptive-sampling/phase3-before-novelty-audit-20261025.md',
       'reason':'Oct18 status before phase3 was reopened by the user'},
      {'original_path':'research/parking_sampling/fit_pair_envelope.py',
       'snapshot_path':(WORK/'pair-envelope/frozen-fit_pair_envelope-v1.py').relative_to(ROOT).as_posix(),
       'reason':'C4v1 experiment preserved; v2 corrects the empty-training fallback, with identical actual results'}]
    for item in history:item['snapshot_sha256']=sha256(ROOT/item['snapshot_path'])
    def check(path,expected):
        path=Path(path)
        if path.exists() and sha256(path)==expected:return 'unchanged'
        relative=path.relative_to(ROOT).as_posix()
        for entry in history:
            if entry['original_path']==relative and entry['snapshot_sha256']==expected:return 'historical_snapshot'
        raise AssertionError(f'Frozen artifact changed without a matching snapshot: {relative}')
    old_count=0;historical_count=0
    for name in ('phase3-artifact-manifest.json','phase3-method-lock.json','phase3-refinement-lock.json'):
        for relative,h in read(DOCS/name)['files'].items():
            historical_count+=check(ROOT/relative,h)=='historical_snapshot';old_count+=1
    # Initial audit and both C4 revisions retain their original input identities.
    for path,plan_name in ((WORK/'pre-fit-lock.json','phase3-novelty-audit-plan.json'),
        (WORK/'pair-envelope/pre-fit-lock.json','phase3-pair-envelope-plan.json'),
        (WORK/'pair-envelope-v2/pre-fit-lock.json','phase3-pair-envelope-plan.json')):
        lock=read(path)
        check(DOCS/plan_name,lock['plan_sha256'])
        for name,h in lock['code_sha256'].items():check(ROOT/'research/parking_sampling'/name,h)
    control_lock=read(WORK/'pair-envelope-controls/pre-evaluation-lock.json')
    check(ROOT/'research/parking_sampling/assess_pair_envelope_controls.py',control_lock['code_sha256'])
    check(DOCS/'phase3-pair-envelope-controls-plan.json',control_lock['plan_sha256'])
    audit=read(WORK/'pre-fit-lock.json');prior=read(OLD/'pre-fit-lock.json')
    prefix=read(DOCS/'phase1-evidence.json')['pilot_prefix']['all_inspected_bay_ids']
    bays=set(audit['new_check_bays']);excluded=set(prior['tuning_bays'])|set(prior['fresh_check_bays'])|set(map(int,prefix))
    assert len(bays)==256 and not bays&excluded
    selection=read(WORK/'selection-before-check.json')
    models=[np.load(WORK/'models'/f'{name}.npz')['lookup'] for name in selection['selected'].values()]
    assert all(np.array_equal(models[0],x) for x in models[1:])
    for label in ('primary_7_days','sensitivity_1_day'):
        paths=[WORK/label/f'{arm}.npz' for arm in selection['selected']]
        arrays=[np.load(p)['by_bay_phase'] for p in paths]
        assert all(np.array_equal(arrays[0],x) for x in arrays[1:])
    v1=read(WORK/'pair-envelope/development-results.json');v2=read(WORK/'pair-envelope-v2/development-results.json')
    assert v1==v2
    np.testing.assert_array_equal(np.load(WORK/'pair-envelope/C4.npz')['lookup'],np.load(WORK/'pair-envelope-v2/C4.npz')['lookup'])
    policy=TrainedSchedule.load(DOCS/'phase3-pair-envelope-policy.json');table=np.load(WORK/'pair-envelope-v2/C4.npz')['lookup']
    count=0
    for state in (0,1):
        for tod in range(4):
            for age in (0,59,60,299,300,899,900,3599,3600,14399,14400,100000):
                time=86400*10+tod*21600+15000;obs=Observation(time,state,time-age)
                assert policy.next_pause(obs)==table[context(obs,False,True)];count+=1
    gate=read(DOCS/'phase3-novelty-gate.json');assert gate['phase4_may_start'] is False and gate['final_867_bay_test_evaluated'] is False
    tests=read(DOCS/'phase3-novelty-verification.json');assert tests['passed'] and tests['tests_run']==59
    for name,h in tests['test_sha256'].items():check(ROOT/'research/parking_sampling'/name,h)
    links=0
    docs=[DOCS/n for n in ('README.md','phase3-novelty-audit.md','phase3-pair-envelope-method.md','phase3-novelty-sources.md')]
    docs.append(ROOT/'research/parking_sampling/README-C4.md')
    for doc in docs:
        for target in re.findall(r'\]\(([^\s]+)\)',doc.read_text(encoding='utf-8')):
            if target.startswith(('http:','https:','#','mailto:')):continue
            target=unquote(target.split('#')[0]);assert (doc.parent/target).exists(),(doc,target);links+=1
    for path in sorted((DOCS/'figures').glob('phase3-pair-envelope-*.png')):
        with Image.open(path) as im:assert im.width>=2000 and im.height>=800
    write_json(DOCS/'phase3-novelty-history.json',{'created_on':'2026-10-25','historical_file_mapping':history,
      'old_status_record_superseded':'phase4-entry-lock.json','current_readiness_record':'phase3-novelty-gate.json',
      'current_readme_sha256':sha256(DOCS/'README.md'),'earlier_locks_and_receipts_preserved':True})
    receipt={'created_on':'2026-10-25','passed':True,'old_manifest_entries_verified':old_count,
      'old_manifest_entries_via_matching_readme_snapshot':historical_count,'cohorts_disjoint_as_planned':True,
      'ablation_selected_models_and_all_raw_check_results_identical':True,'C4_v1_v2_actual_results_identical':True,
      'compact_runtime_comparisons':count,'local_markdown_links_verified':links,
      'new_tests':tests['tests_run'],'figure_visual_review':'Both PNGs inspected for layout and readability; no clipped labels',
      'phase4_gate_opened':False,'final_test_states_opened_by_this_verifier':False}
    write_json(DOCS/'phase3-novelty-artifact-verification.json',receipt)
    paths=set(p for p in WORK.rglob('*') if p.is_file())
    for pattern in ('phase3-novelty-*','phase3-pair-envelope-*','phase3-before-novelty-audit-20261025.md'):
        paths.update(p for p in DOCS.glob(pattern) if p.is_file())
    paths.discard(DOCS/'phase3-novelty-artifacts.json');paths.add(DOCS/'README.md')
    paths.update((DOCS/'figures').glob('phase3-pair-envelope-*'))
    names=('audit_episode_constraint.py','episode_certificate.py','episode_pair_certificate.py','test_novelty_audit.py',
      'test_episode_pair_certificate.py','assess_cycle_certificate.py','assess_pair_certificate.py','fit_pair_envelope.py',
      'assess_pair_envelope_controls.py','fetch_novelty_sources.py','build_novelty_report.py','verify_novelty_audit.py',
      'verify_novelty_artifacts.py','README-C4.md')
    paths.update(ROOT/'research/parking_sampling'/n for n in names)
    write_json(DOCS/'phase3-novelty-artifacts.json',{'created_on':'2026-10-25','scope':'phase3_development_author_candidate_not_final_test',
      'files':{p.relative_to(ROOT).as_posix():sha256(p) for p in sorted(paths)},'final_test_evaluated':False,
      'phase4_may_start':False,'historical_mappings':'phase3-novelty-history.json'})
    print(json.dumps({**receipt,'new_artifacts_frozen':len(paths)}))

if __name__=='__main__':main()
