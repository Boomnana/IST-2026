"""Validate every headline number against cached CSVs.

Runs 70_verify_results_md.py (29-gate check). Equivalent to reproduce_all.py Phase 4.

Usage:
  cd artifact
  python scripts/validate_headlines.py
"""
import subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
result = subprocess.run([sys.executable, str(ROOT / 'scripts/70_verify_results_md.py')],
                       cwd=str(ROOT), capture_output=True, text=True)
print(result.stdout)
if result.returncode != 0:
    print(f'FAILED: {result.stderr}')
    sys.exit(1)
