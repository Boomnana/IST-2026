"""RQ2 enrichment: the verifier-gap vs passive-uncheckable split is CROSS-BACKBONE ROBUST.

Extends the missed-vs-absent split from DeepSeek's 18 verifier-silent records to Qwen's silent set
and the cross-model (robustly-silent) intersection, all anchored on the SAME full-coverage
human-on-trace labels (annotators A & B label all 465 records; all 180 POS covered -- verified here).

This grows the demonstrated n (18 -> 54 across vendors) and adds a robustness axis WITHOUT new data
collection: it is pure recomputation from the frozen judge caches. It does NOT make the human anchor
independent (A & B are the same two annotators throughout) -- that remains a stated threat; what it
shows is robustness of the split to the VERIFIER backbone, plus a vendor-invariant hard core.

Read-only on all inputs. Writes ONE new package-local CSV (results/rq2_cross_backbone_split.csv);
touches no gold and no other frozen result. zero-API.

Built-in sanity ASSERTIONS (abort on drift, no write): reproduce the locked silent counts
18 / 54 / 16 (cf. rq1_silent.csv) and the current 13/5 DeepSeek split, and verify the 5-record
passive-uncheckable hard core is backbone-invariant.
"""
import json, sys, csv as _csv
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
import pandas as pd
from _paths import XP, LEG, ORS, RES

def load(p):
    d = {}
    for l in open(p, encoding='utf-8'):
        l = l.strip()
        if not l: continue
        r = json.loads(l)
        if r.get('_header'): continue
        d[r['record_id']] = r
    return d
def fam(r):
    q = r.split('__'); return q[1] if len(q) > 1 and q[1] in ('appagent', 'mav3') else 'other'

# ---- universe + positive class (gold; read-only) ----
v3 = {json.loads(l)['record_id']: json.loads(l) for l in open(XP/'data/gold/final_labels_v3.jsonl', encoding='utf-8') if l.strip()}
U = set(v3); POS = {r for r in U if v3[r]['intent'] == 'UNHEDGED_SUCCESS' and v3[r]['outcome'] == 'NOT_COMPLETED'}

# ---- human-on-trace anchor (A & B claim-blind outcome; full corpus) ----
A = pd.read_excel(ORS/'inputs/iaa/iaa_sample_annotator_A_complete.xlsx').set_index('record_id')
B = pd.read_excel(ORS/'inputs/iaa/iaa_sample_annotator_B_complete.xlsx').set_index('record_id')
def hout(df, r): return str(df.loc[r, 'outcome_label']).strip().upper() if r in df.index else None
def covered(r): return (r in A.index) and (r in B.index)
def human_NC(r): return hout(A, r) == 'NOT_COMPLETED' and hout(B, r) == 'NOT_COMPLETED'

# ---- verifier set C, both backbones (definitions identical to 10_rq1_spectrum / 80_human_anchored) ----
dsb = [load(LEG/f'experiments/rq1_2_baseline_judge_failure/outputs/deepseek_baseline_run{i}.jsonl') for i in range(1, 6)]
dsm = [load(LEG/f'experiments/rq4_1_cross_model/outputs/deepseek_mibv_run{i}.jsonl') for i in range(1, 6)]
dsc = load(LEG/'experiments/rq4_1_cross_model/outputs/deepseek_claim_conveyance_v2_run1.jsonl')
qwb = [load(LEG/f'experiments/rq1_2_baseline_judge_failure/outputs/qwen_baseline_run{i}.jsonl') for i in range(1, 6)]
qwm = [load(LEG/f'experiments/rq2_1_mibv_main/outputs/qwen_mibv_run{i}.jsonl') for i in range(1, 6)]
qwc = load(LEG/'experiments/rq4_1_cross_model/outputs/qwen_claim_conveyance_v2_run1.jsonl')

def mibv_v(s, c):
    if s == 'UNKNOWN' or c == 'UNCLEAR': return 'REVIEW'
    if s == 'COMPLETED' and c == 'SUCCESS': return 'PASS'
    if s == 'NOT_COMPLETED' and c == 'FAILURE_OR_INCOMPLETE': return 'PASS'
    return 'FLAG'
def v_out(runs, r): return sum(1 for x in runs if x.get(r, {}).get('outcome_verdict') == 'NOT_COMPLETED')
def v_claim(runs, r): return sum(1 for x in runs if x.get(r, {}).get('claim_verdict') == 'INCONSISTENT')
def v_mibv(runs, conv, r):
    return sum(1 for x in runs if x.get(r, {}).get('completion') and conv.get(r, {}).get('conveys')
               and mibv_v(x[r]['completion'], conv[r]['conveys']) == 'FLAG')
def nindep_C(runsb, runsm, conv, r):
    bare = max(v_out(runsb, r), v_claim(runsb, r)); mb = v_mibv(runsm, conv, r)
    return (1 if bare >= 3 else 0) + (1 if mb >= 3 else 0)

silent_DS = {r for r in POS if nindep_C(dsb, dsm, dsc, r) == 0}
silent_QW = {r for r in POS if nindep_C(qwb, qwm, qwc, r) == 0}
silent_INT = silent_DS & silent_QW
silent_UNION = silent_DS | silent_QW

def split(S):
    cov = [r for r in S if covered(r)]; unc = [r for r in S if not covered(r)]
    vg = {r for r in cov if human_NC(r)}; pu = {r for r in cov if not human_NC(r)}
    return cov, unc, vg, pu

sets = {'deepseek': silent_DS, 'qwen': silent_QW, 'intersection': silent_INT, 'union': silent_UNION}
res = {k: split(v) for k, v in sets.items()}

# ============================ SANITY ASSERTIONS (abort on drift) ============================
errs = []
def expect(label, got, want):
    ok = got == want; print(f'  {"OK  " if ok else "FAIL"} {label}: got {got} want {want}')
    if not ok: errs.append(label)
print('=== sanity assertions (must reproduce locked numbers; abort on any FAIL) ===')
expect('DS silent n', len(silent_DS), 18)
expect('QW silent n', len(silent_QW), 54)
expect('INT silent n', len(silent_INT), 16)
expect('UNION silent n', len(silent_UNION), 56)
expect('DS split (vg,pu)', (len(res['deepseek'][2]), len(res['deepseek'][3])), (13, 5))
expect('QW split (vg,pu)', (len(res['qwen'][2]), len(res['qwen'][3])), (39, 15))
expect('INT split (vg,pu)', (len(res['intersection'][2]), len(res['intersection'][3])), (11, 5))
# coverage: every silent record in every set must have a human label (else 'miss' would be a coverage gap)
for k in sets:
    expect(f'{k} fully covered (no uncovered)', len(res[k][1]), 0)
# hard core: DeepSeek PU == intersection PU, and DeepSeek PU subset of Qwen PU
pu_ds, pu_qw, pu_int = res['deepseek'][3], res['qwen'][3], res['intersection'][3]
expect('hard core: PU_DS == PU_INT', pu_ds == pu_int, True)
expect('hard core: PU_DS subset of PU_QW', pu_ds <= pu_qw, True)
if errs:
    raise SystemExit(f'\nABORT: {len(errs)} assertion(s) failed: {errs} -- NOT writing CSV (numbers drifted).')
print('  all assertions passed.\n')

# ============================ report + write CSV ============================
print('=== cross-backbone verifier-gap / passive-uncheckable split ===')
rows = []
for k in ('deepseek', 'qwen', 'intersection', 'union'):
    cov, unc, vg, pu = res[k]; n = len(sets[k]); pr = round(100 * len(pu) / n, 1)
    print(f'  {k:13s} n={n:2d}  verifier-gap={len(vg):2d}  passive-uncheckable={len(pu):2d}  PU-share={pr}%')
    rows.append([k, n, len(vg), len(pu), pr])

print('\n  vendor-invariant hard core (passive-uncheckable in BOTH DS and INT):')
for r in sorted(pu_ds): print(f'     {fam(r):8s} {r.split("__")[0]}')
print(f'  PU share: DS {rows[0][4]}% and QW {rows[1][4]}% (both 27.8); INT {rows[2][4]}%')

with open(RES/'rq2_cross_backbone_split.csv', 'w', newline='', encoding='utf-8') as fp:
    w = _csv.writer(fp)
    w.writerow(['silent_set', 'n', 'verifier_gap', 'passive_uncheckable', 'pu_rate_pct'])
    w.writerows(rows)
print(f'\n-> wrote {RES/"rq2_cross_backbone_split.csv"}')
print('DONE 88_silent_split_cross_backbone.')
