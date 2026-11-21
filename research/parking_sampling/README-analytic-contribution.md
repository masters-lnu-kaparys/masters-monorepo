# Analytical contribution audit, 2026-10-25

This supplements the frozen history certificate. It does not retune C3/C4, run a new scheduler search, read a new check cohort or evaluate the867-bay final test.

From the repository root using Python with numpy/numba/duckdb/scipy/matplotlib/pypdf:

```powershell
python research/parking_sampling/assess_analytic_contribution.py
python research/parking_sampling/report_analytic_contribution.py
python research/parking_sampling/verify_analytic_contribution.py
```

The first command checks the existing pre-analysis lock and retains completed result files. PDF downloads are separate scripts `fetch_analytic_sources.py` and `fetch_duration_source.py`; downloading is explicitly distinct from the read scope recorded in the source-evidence JSON.

`status_analytic_contribution.py` was run once to snapshot the preceding live README/gate and link this review. It is not part of the analysis replay. Older report/verification scripts must not be rerun to replace their historical status files.

`analytic_certificate.py` implements the linear count and a separate small integer-grid dynamic program. The latter considers every positive integer pause within the controller cap. Future source values are used for offline evaluation only. Its maximizing path can be implemented causally by following the saved observed history and choosing a safe pause on any other history; it is not a deployable predictor trained on future data.

Outputs are in `.codex-work/parking-analytic-contribution-20261025` and `docs/research/adaptive-sampling/phase3-analytic-*`. The source timestamps are naive local civil seconds. Full-window certificate counts are not multiplied by replay phases. Main and sensitivity window sets overlap.

The written real-time proof has additional non-accumulating-sample and initialization assumptions. Finite enumeration is falsification support, not a formal proof-assistant check. A positive upper count is conservative, not an exact reachability result. New and old history counts agree on all eight development cells. Phase4 remains closed; academic originality is qualified in the source comparison and supervisor brief.
