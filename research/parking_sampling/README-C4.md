# C4: training-derived pause envelope

Research candidate in **reopened phase 3**. The final 867-bay test remains closed.

See the Ukrainian [method and proof](../../docs/research/adaptive-sampling/phase3-pair-envelope-method.md), [full development report](../../docs/research/adaptive-sampling/phase3-novelty-audit.md) and [prior-art review](../../docs/research/adaptive-sampling/phase3-novelty-sources.md).

`fit_pair_envelope.py` keeps the C3 state/observed-run template and replaces only its long free-state pause. For target free duration `tau=60`, every missed target episode requires `B+D<G`, provided occupied-state pauses never exceed `tau`. `B` is its immediately preceding occupied duration and `D` its own free duration. The cap is `min(120, min_training(B+D))`, with an empty-training fallback of60. The actual132840 eligible complete training pairs give72.

The proof is for correctly and instantaneously observed **recorded** binary paths. A minimum in finite training data is not a physical bound on future vehicle activity. A positive pair count is an upper bound on missed events, not a prediction that they will be missed.

The compact [JSON rule](../../docs/research/adaptive-sampling/phase3-pair-envelope-policy.json) can be loaded by the existing `TrainedSchedule.load`; runtime receives only the paid observation and observed-run start. No future source interval is passed to it. Runtime equality with all48 inherited lookup positions is checked by `verify_novelty_artifacts.py`.

Reproduction, from repository root with the existing research dependencies:

```powershell
python research/parking_sampling/audit_episode_constraint.py
python research/parking_sampling/assess_cycle_certificate.py
python research/parking_sampling/assess_pair_certificate.py
python research/parking_sampling/fit_pair_envelope.py
python research/parking_sampling/assess_pair_envelope_controls.py
python research/parking_sampling/verify_novelty_audit.py
python research/parking_sampling/build_novelty_report.py
python research/parking_sampling/verify_novelty_artifacts.py
```

The report generator does not create a phase4 entry lock. The old Oct18 lock is retained as historical evidence and superseded by `phase3-novelty-gate.json` for current readiness. Previous source/method locks and test receipts are preserved.
