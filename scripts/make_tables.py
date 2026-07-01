"""Generate all paper result tables from RQ analysis outputs.

Runs 50_make_results_tables.py. Equivalent to reproduce_all.py Phase 3.

Usage:
  cd artifact
  python scripts/make_tables.py
"""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
result = subprocess.run([sys.executable, str(ROOT / 'scripts/50_make_results_tables.py')],
                       cwd=str(ROOT), capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print(f'FAILED: {result.stderr}')
    sys.exit(1)
