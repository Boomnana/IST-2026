"""DEMO: RQ2 recomputed with annotator-C's INDEPENDENT evidence labels.
Cross-tabs the verifier-silent set (channel-set C, deepseek, 3-of-5 -- same loaders as 10_rq1_spectrum)
against C's evidence_sufficiency, and compares to the gold-annotator passive-uncheckable 5.
*** DEMO ONLY: annotator C here is an LLM simulation, NOT an independent human; this cannot be the
    paper's anchor (re-introduces circularity). For previewing the analysis shape only. ***
zero-API, stdlib. python scripts/87_rq2_with_C.py
"""
import json, csv
from collections import Counter
from _paths import XP, LEG, ROOT

def load(p):
    d = {}
    for l in open(p, encoding='utf-8'):
        l = l.strip()
        if not l: continue
        r = json.loads(l)
        if r.get('_header'): continue
        d[r['record_id']] = r
    return d

v3 = {json.loads(l)['record_id']: json.loads(l) for l in open(XP/'data/gold/final_labels_v3.jsonl', encoding='utf-8') if l.strip()}
U = set(v3)
POS = {r for r in U if v3[r]['intent'] == 'UNHEDGED_SUCCESS' and v3[r]['outcome'] == 'NOT_COMPLETED'}

def mibv_v(s, c):
    if s == 'UNKNOWN' or c == 'UNCLEAR': return 'REVIEW'
    if s == 'COMPLETED' and c == 'SUCCESS': return 'PASS'
    if s == 'NOT_COMPLETED' and c == 'FAILURE_OR_INCOMPLETE': return 'PASS'
    return 'FLAG'
def votes(runs, f, v): return {r: sum(1 for x in runs if x.get(r, {}).get(f) == v) for r in U}
def mvotes(runs, conv): return {r: sum(1 for x in runs if x.get(r, {}).get('completion') and conv.get(r, {}).get('conveys')
                                       and mibv_v(x[r]['completion'], conv[r]['conveys']) == 'FLAG') for r in U}

dsb = [load(LEG/f'experiments/rq1_2_baseline_judge_failure/outputs/deepseek_baseline_run{i}.jsonl') for i in range(1, 6)]
dsm = [load(LEG/f'experiments/rq4_1_cross_model/outputs/deepseek_mibv_run{i}.jsonl') for i in range(1, 6)]
dsc = load(LEG/'experiments/rq4_1_cross_model/outputs/deepseek_claim_conveyance_v2_run1.jsonl')
oNC = votes(dsb, 'outcome_verdict', 'NOT_COMPLETED'); iNC = votes(dsb, 'claim_verdict', 'INCONSISTENT')
bare = {r: max(oNC[r], iNC[r]) for r in U}
mibvb = mvotes(dsm, dsc)
silent = sorted(r for r in POS if bare[r] < 3 and mibvb[r] < 3)   # set C, 3-of-5
assert len(silent) == 18, f'verifier-silent={len(silent)} (expected 18) -- loaders out of sync'

# gold-annotator passive-uncheckable 5 (RQ2 footnote; verified record-ids by prefix)
PU_PREFIX = ['ExtAW005__mav3', 'ExtTH020__mav3', 'RecipeDeleteDuplicateRecipes', 'SimpleCalendarAddRepeatingEvent__mav3']
PU5 = sorted(r for r in silent if any(r.startswith(p) for p in PU_PREFIX))
assert len(PU5) == 5, f'matched passive-uncheckable={len(PU5)} (expected 5): {PU5}'
GAP13 = sorted(set(silent) - set(PU5))   # gold verifier-gap

C = {r['record_id']: r for r in csv.DictReader(open(ROOT/'labels/tec_sheet_C.csv', encoding='utf-8'))}
def suf(r): return C.get(r, {}).get('evidence_sufficiency', 'MISSING')

print('*** DEMO (annotator C = LLM sim, not human) ***')
print(f'verifier-silent (set C, 3-of-5, deepseek): {len(silent)}')
print(f'\n[C\'s independent evidence_sufficiency over the 18 silent]')
print(' ', dict(Counter(suf(r) for r in silent)))

# C-INDEPENDENT RQ2 split
C_unc = [r for r in silent if suf(r) == 'insufficient']
C_gap = [r for r in silent if suf(r) in ('sufficient', 'partial')]
print(f'\n[de-circularized RQ2 split by C alone]')
print(f'  verifier-gap (C: sufficient/partial)      : {len(C_gap)}')
print(f'  passive-uncheckable (C: insufficient)     : {len(C_unc)}')
print(f'  C-insufficient record_ids: {[r.split("__")[0] for r in C_unc]}')

# agreement vs gold-annotator split
print(f'\n[does C reproduce the gold-annotator split? gold: 13 gap / 5 passive-uncheckable]')
print(f'  of gold\'s 5 passive-uncheckable, C says: {dict(Counter(suf(r) for r in PU5))}')
for r in PU5: print(f'     {suf(r):12s}  {r.split("__")[0]}')
print(f'  of gold\'s 13 verifier-gap, C says: {dict(Counter(suf(r) for r in GAP13))}')
# concordance: treat C-insufficient == gold-PU as the positive class
tp = len(set(C_unc) & set(PU5)); fp = len(set(C_unc) - set(PU5)); fn = len(set(PU5) - set(C_unc))
print(f'\n[concordance of "uncheckable" label]  C∩gold={tp}  C-only={fp}  gold-only={fn}')
print('  (DEMO; a real independent human panel replaces C. This shows the analysis shape only.)')
