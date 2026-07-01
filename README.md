# CHECKABILITY — Replication Artifact

## Paper
**When Is a Mobile GUI-Agent Self-Report Checkable?**
*A Protocol-Relative Study of Passive Trace Verification for Mobile GUI Agents*

Target journal: Information and Software Technology (IST, Elsevier)

## One-command reproduction

```bash
cd artifact
python scripts/reproduce_all.py
```

This runs the full pipeline: asset validation → RQ analysis → table generation →
figure generation → headline number verification (29-gate check).

**Prerequisites**: Python 3.10+, pandas, matplotlib (`pip install pandas matplotlib`)

## What gets reproduced

| Output | Source script | Paper section |
|--------|--------------|---------------|
| `outputs/tables/rq1_spectrum.csv` | `10_rq1_spectrum.py` | §RQ1 (checkability spectrum) |
| `outputs/tables/rq1_channel_discrimination.csv` | `10_rq1_spectrum.py` | §RQ1 (gate results) |
| `outputs/tables/rq1_heldout_h1.csv` | `10_rq1_spectrum.py` | §RQ1 (held-out H1) |
| `outputs/tables/rq1_silent.csv` | `10_rq1_spectrum.py` | §RQ1 (silent counts) |
| `outputs/tables/rq1_gate_sensitivity.csv` | `11_rq1_gate_sensitivity.py` | §RQ1 (sensitivity) |
| `outputs/tables/rq_human_anchored.csv` | `80_human_anchored_checkability.py` | §RQ2 (human anchor) |
| `outputs/tables/rq_human_anchored_core.csv` | `80_human_anchored_checkability.py` | §RQ2 (core) |
| `outputs/tables/rq2_cross_backbone_split.csv` | `88_silent_split_cross_backbone.py` | §RQ2 (cross-backbone) |
| `outputs/tables/rq3_info_layers_overall.csv` | `30_rq3_info_layers.py` | §RQ3 (info layers) |
| `outputs/tables/rq3_carrier_crossing.csv` | `30_rq3_info_layers.py` | §RQ3 (carrier × layer) |
| `outputs/tables/rq4_construct_relativity.csv` | `40_construct_relativity.py` | §RQ4 (construct swap) |
| `outputs/tables/rq_kappa.csv` | `94_kappa_and_rq4control.py` | §labels (IAA) |
| `outputs/tables/rq_typology.csv` | `93_typology.py` | §typology |
| `outputs/tables/rq_forward_guidance.csv` | `90_forward_guidance.py` | §implications |
| `outputs/tables/rq_forward_corrected.csv` | `91_forward_corrected.py` | §implications |
| `outputs/tables/rq_escalation_policy.csv` | `99_escalation_policy.py` | §implications |
| `outputs/figures/fig3_construct.pdf/.png` | `60_make_figures.py` | Figure 2 (construct relativity) |
| `outputs/figures/fig4_frontier.pdf/.png` | `92_forward_figure.py` | Figure 3 (recall–FAR frontier) |

**Validation**: `python scripts/validate_headlines.py` runs the 29-gate check
that verifies every headline number in the paper against the cached CSVs.

## Artifact structure

```
artifact/
  README.md                    — this file
  data/
    records_465.csv            — study frame: 465 records with gold labels
    positives_180.csv          — dangerous misreports: 180 POS with carrier proxy
    per_record_results.csv     — per-record: vote counts, nindep, layer, human_NC
    dev_test_split_seed42.csv  — dev(232)/test(233) holdout split
    annotation_annotator_A_raw.csv — annotator A raw labels
    annotation_annotator_B_raw.csv — annotator B raw labels
    annotation_adjudicated.csv     — reconciled adjudicated labels
    final_labels_v3.jsonl      — gold labels (source JSONL)
    judge_inputs.jsonl         — 465 trace inputs for LLM judges
    holdout_split_seed42.json  — dev/test split (source JSON)
  prompts/
    bare_judge.txt             — dual-axis claim-aware LLM judge (outcome + claim)
    bare_outcome_claim_blind.txt — claim-blind outcome-only LLM judge
    claim_conveyance.txt       — hedge-aware claim conveyance classifier
    trace_state_estimator.txt  — MIBV v2: task-type-aware 4-guard state estimator
    conservative_prompt.txt    — conservative dual-axis judge (biased toward flag)
    vision_judge.txt           — AER vision: screenshot-based success/failure judge
  caches/
    deepseek_v4_flash/         — deepseek-v4-flash judge outputs (5 runs × channel)
    qwen3_5_flash/             — qwen3.5-flash judge outputs (5 runs × channel)
    temperature_rerun/         — T=0.3 and T=0.7 ablation runs (5 each)
  scripts/
    _paths.py                  — centralized artifact-relative paths
    reproduce_all.py           — one-command full pipeline
    make_tables.py             — generate result CSVs
    make_figures.py            — generate figures
    validate_headlines.py      — 29-gate number verification
    00_assets_check.py         — asset validation
    10_rq1_spectrum.py         — RQ1 spectrum
    11_rq1_gate_sensitivity.py — RQ1 sensitivity
    30_rq3_info_layers.py      — RQ3 info layers
    40_construct_relativity.py — RQ4 construct swap
    50_make_results_tables.py  — result CSV consolidation
    60_make_figures.py          — figure generation
    70_verify_results_md.py    — number verification
    80_human_anchored_checkability.py — RQ2 human anchor
    87_rq2_with_C.py           — RQ2 under set C
    88_silent_split_cross_backbone.py — RQ2 cross-backbone
    94_kappa_and_rq4control.py — IAA kappa
    95_corpus_distribution.py  — corpus stats
    96_temperature_ablation.py — temperature robustness
    99_escalation_policy.py    — escalation policy
  protocol/
    annotation_codebook.md     — IAA annotation protocol v3
    verifier_gate_spec.md      — channel discrimination gate specification
    carrier_proxy_rules.md     — success-criterion carrier classification rules
  outputs/
    tables/                    — result CSVs (pre-computed; reproduce_all regenerates)
    figures/                   — PDF/PNG figures (pre-computed; reproduce_all regenerates)
```

## Key constants (locked)

- **Universe**: U = 465 records
- **Positive class**: POS = 180 (UNHEDGED_SUCCESS ∧ NOT_COMPLETED)
- **Base rate**: 0.387 (180/465)
- **Agent families**: appagent 177 (90 POS) / mav3 288 (90 POS)
- **Primary channel set**: C = {bare-judge, trace-state estimator}
- **Majority protocol**: 5-run 3-of-5 @ T=0

## Backbone models

| Backbone | Provider | Class | Role |
|----------|----------|-------|------|
| deepseek-v4-flash | DeepSeek | flash (economic) | Primary |
| qwen3.5-flash | Alibaba/Qwen | flash (economic) | Cross-vendor replication |

## Citation

```bibtex
@article{checkability2026,
  title   = {When Is a Mobile GUI-Agent Self-Report Checkable?},
  author  = {[ANONYYMIZED FOR REVIEW]},
  journal = {Information and Software Technology},
  note    = {Under review},
  year    = {2026}
}
```

## License

This artifact is provided for academic replication purposes only.
All LLM judge outputs were generated using paid API access; the raw
trace data (AndroidWorld + extended suite) originates from publicly
available benchmark datasets.
