"""Centralized paths for the replication artifact package.

All paths resolve relative to THIS artifact directory. The package is
self-contained: data/ holds gold labels, caches/ holds LLM judge outputs,
and scripts/ read from both. No external dependency required.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # artifact/ root

# Read-only inputs inside the artifact
DATA   = ROOT / 'data'
CACHE  = ROOT / 'caches'
PROMPT = ROOT / 'prompts'
PROTO  = ROOT / 'protocol'

# Cache subdirectories
DS_CACHE = CACHE / 'deepseek_v4_flash'
QW_CACHE = CACHE / 'qwen3_5_flash'
T_CACHE  = CACHE / 'temperature_rerun'

# Output directories
RES = ROOT / 'outputs' / 'tables'
FIG = ROOT / 'outputs' / 'figures'
for _d in (RES, FIG):
    _d.mkdir(parents=True, exist_ok=True)

# Convenience aliases matching original _paths variable names
XP   = DATA       # gold labels + judge_inputs
LEG  = DATA       # deepseek baseline/mibv caches (now flat in DS_CACHE)
MB   = DATA       # mibv oracle separation caches (now flat in DS_CACHE)
ORS  = DATA
NEW  = DATA
ANN  = DATA
BZ   = DATA
