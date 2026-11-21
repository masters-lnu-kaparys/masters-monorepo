# Fixed-policy coverage for arbitrary initialization

Phase3 supplementary diagnostic,2026-10-25. Unchanged C3/75 and C4/72, only previously inspected cohorts. No fit, new cohort, final-test evaluation, API or firmware changes.

```powershell
python research/parking_sampling/assess_start_reachability.py
python research/parking_sampling/report_start_reachability.py
python research/parking_sampling/verify_start_reachability.py
```

The first command validates the pre-analysis lock and retains completed outputs. The second produces the new report/CSVs/figure only. The third runs the existing95 plus9 new tests, preserves earlier status bytes, updates the live index/gate and verifies previous artifacts. Do not run old report scripts to overwrite historical outputs. Runtime dependencies match the prior research environment.

The backward test is episode-wise existential coverage, not simultaneous maximum misses or a probability. A finite free-run prefix followed by constant pause G permits exhaustive inspection of last sample times in[b-G,p) and plateau entry times t-qG. Integer source boundaries and pauses give a mathematical equivalence between integer starts and every real start with the same integer part. The first plateau sample of C3/C4 is at observed age930, although the threshold is900.

Independent validation enumerates1458 small trace/profile cases and300 seeded cases, every integer start and fractional offsets0.25/0.75. Source-data positive witnesses are replayed with the old independent simulator and the frozen policy tables, not the new forward recurrence. Saved witnesses stop after the target and one following source interval; their counters are local diagnostic counters, not whole-window performance results.

Outputs: `.codex-work/parking-start-reachability-20261025` and `docs/research/adaptive-sampling/phase3-start-reachability-*`. New exact counts refine positive R.3 bounds but do not establish improved online scheduling, map accuracy, future coverage or academic novelty. Main and sensitivity criteria overlap. Phase4 remains closed.
