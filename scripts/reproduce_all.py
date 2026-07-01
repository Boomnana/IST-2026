"""Reproduce all tables and figures from the CHECKABILITY replication artifact.

This script runs the full analysis pipeline on the vendored data and caches,
producing every CSV table and figure that appears in the paper.

Usage:
  cd artifact
  python scripts/reproduce_all.py

Prerequisites:
  - Python 3.10+ with pandas, matplotlib (pip install pandas matplotlib)
  - All cache JSONL files present in caches/

Output:
  outputs/tables/*.csv  — all result CSVs (paper tables)
  outputs/figures/*.pdf + *.png  — construct-relativity figure
"""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # artifact/
SCPT = ROOT / 'scripts'

scripts = [
    # Phase 1: asset validation
    ('00_assets_check.py', 'Validate all vendored assets (19 checks)'),
    # Phase 2: RQ analysis
    ('10_rq1_spectrum.py',           'RQ1: checkability spectrum + held-out H1'),
    ('11_rq1_gate_sensitivity.py',   'RQ1: gate sensitivity sweep'),
    ('30_rq3_info_layers.py',        'RQ3: carrier x information layer crossing'),
    ('40_construct_relativity.py',   'RQ4: construct swap + survival'),
    ('80_human_anchored_checkability.py', 'RQ2: human-anchored split'),
    ('87_rq2_with_C.py',            'RQ2: silent split under channel set C'),
    ('88_silent_split_cross_backbone.py', 'RQ2: cross-backbone silent split'),
    ('94_kappa_and_rq4control.py',   'IAA kappa + RQ4 control'),
    ('95_corpus_distribution.py',    'Corpus distribution stats'),
    ('96_temperature_ablation.py',   'Temperature robustness (reads caches)'),
    ('99_escalation_policy.py',      'Escalation policy evaluation'),
    # Phase 3: result consolidation
    ('50_make_results_tables.py',    'Generate all result CSVs from RQ outputs'),
    ('60_make_figures.py',           'Generate construct-relativity figure'),
    # Phase 4: verification
    ('70_verify_results_md.py',      'Verify every number in RESULTS.md against CSVs'),
]

print('=' * 70)
print('CHECKABILITY Replication Artifact — reproduce_all.py')
print('=' * 70)
print()

fails = []
for script, desc in scripts:
    print(f'>>> {script}: {desc}')
    result = subprocess.run(
        [sys.executable, str(SCPT / script)],
        cwd=str(ROOT),
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f'  FAILED (exit {result.returncode})')
        print(result.stderr[-500:] if result.stderr else '')
        fails.append(script)
    else:
        # Print last 3 lines of output as summary
        lines = result.stdout.strip().split('\n')
        for line in lines[-3:]:
            print(f'  {line}')
    print()

print('=' * 70)
if fails:
    print(f'COMPLETED with {len(fails)} FAILURES: {fails}')
else:
    print('ALL SCRIPTS PASSED — replication complete.')
print('=' * 70)
print()
print('Tables produced:')
for f in sorted((ROOT / 'outputs/tables').glob('*.csv')):
    print(f'  {f.name}')
print('Figures produced:')
for f in sorted((ROOT / 'outputs/figures').glob('*.pdf')):
    print(f'  {f.name}')
