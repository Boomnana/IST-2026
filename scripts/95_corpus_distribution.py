"""Q0 corpus-distribution table (zero-API, from vendored inputs via _paths).
Records/POS per agent family and per task source, plus trace-length (step-count) quartiles.
Prints the numbers and writes results/corpus_distribution.csv. Every value reproducible from cache."""
import json, csv, statistics as st
from collections import defaultdict, Counter
from _paths import XP, RES

def loadl(p):
    out = []
    for l in open(p, encoding='utf-8'):
        l = l.strip()
        if not l: continue
        r = json.loads(l)
        if isinstance(r, dict) and r.get('_header'): continue
        out.append(r)
    return out

v3 = {r['record_id']: r for r in loadl(XP / 'data/gold/final_labels_v3.jsonl')}
U = set(v3)
POS = {r for r in U if v3[r]['intent'] == 'UNHEDGED_SUCCESS' and v3[r]['outcome'] == 'NOT_COMPLETED'}

def fam(r):
    q = r.split('__')
    return q[1] if len(q) > 1 and q[1] in ('appagent', 'mav3') else 'other'

def source(r):
    tok = r.split('__')[0]
    for pre, name in (('ExtAW', 'AndroidWorld'), ('OrigAW', 'AndroidWorld'),
                      ('ExtTH', 'Themis'), ('ExtAA', 'AppAgent-X')):
        if tok.startswith(pre): return name
    # non-opaque task names (verbs) -> infer source bucket
    return 'AndroidWorld' if any(k in tok for k in ('Recipe','Calendar','Simple','Markor','Clock','Expense','Tasks','Audio','Camera','Files','Browser','Contacts','Sms','System','Turn','Open')) else 'other/named'

# trace lengths from judge_inputs (step count per record)
steps = {}
for r in loadl(XP / 'data/raw_compact/judge_inputs.jsonl'):
    rid = r.get('record_id')
    if rid in U:
        steps[rid] = len(r.get('steps') or [])

def quart(xs):
    xs = sorted(xs)
    if not xs: return (0, 0, 0, 0, 0)
    q = st.quantiles(xs, n=4) if len(xs) > 1 else [xs[0], xs[0], xs[0]]
    return (xs[0], round(q[0]), round(st.median(xs)), round(q[2]), xs[-1])

print('=== by agent family ===')
rows = []
for f in ('appagent', 'mav3'):
    n = sum(1 for r in U if fam(r) == f)
    p = sum(1 for r in POS if fam(r) == f)
    sl = [steps[r] for r in U if fam(r) == f and r in steps]
    mn, q1, med, q3, mx = quart(sl)
    print(f'  {f:9s} N={n:3d}  POS={p:3d} ({100*p/n:4.1f}%)  steps med={med} IQR[{q1},{q3}] range[{mn},{mx}]  (n_steps={len(sl)})')
    rows.append([f, n, p, f'{100*p/n:.1f}', med, q1, q3, mn, mx])
nU, nP = len(U), len(POS)
slall = [steps[r] for r in U if r in steps]
mn, q1, med, q3, mx = quart(slall)
print(f'  {"TOTAL":9s} N={nU}  POS={nP} ({100*nP/nU:4.1f}%)  steps med={med} IQR[{q1},{q3}] range[{mn},{mx}]')
rows.append(['TOTAL', nU, nP, f'{100*nP/nU:.1f}', med, q1, q3, mn, mx])

print('\n=== by inferred task source (POS-side) ===')
src_all = Counter(source(r) for r in U)
src_pos = Counter(source(r) for r in POS)
for s in sorted(src_all):
    print(f'  {s:14s} N={src_all[s]:3d}  POS={src_pos.get(s,0):3d}')

print(f'\n=== coverage: trace-length available for {len(steps)}/{len(U)} records ===')

(RES).mkdir(parents=True, exist_ok=True)
with open(RES / 'corpus_distribution.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(['family', 'N', 'POS', 'POS_rate_%', 'steps_median', 'steps_Q1', 'steps_Q3', 'steps_min', 'steps_max'])
    w.writerows(rows)
print(f'-> wrote {RES / "corpus_distribution.csv"}')

# ---- data pipeline: claim-intent / outcome distribution, gold provenance, screenshot coverage ----
intent = Counter(v3[r]['intent'] for r in U)
outc   = Counter(v3[r]['outcome'] for r in U)
prov   = Counter(v3[r].get('source', '?') for r in U)
img_root = XP / 'data/raw_with_img'
idx_path = RES / 'screenshot_index.txt'   # per-record screenshot availability; lets the released
def _has_shot(rid):                        # package report coverage without shipping the 6.7GB images
    d = img_root / rid
    return d.exists() and any(f.suffix.lower() in ('.png', '.jpg', '.jpeg') for f in d.rglob('*') if f.is_file())
if img_root.exists():
    have = sorted(r for r in U if _has_shot(r))
    idx_path.write_text('\n'.join(have), encoding='utf-8')
    shots = len(have)
elif idx_path.exists():
    have = set(idx_path.read_text(encoding='utf-8').split())
    shots = sum(1 for r in U if r in have)
else:
    shots = 0
prows = [
    ['universe', len(U)],
    ['unhedged_success_claims', intent.get('UNHEDGED_SUCCESS', 0)],
    ['hedged_success', intent.get('HEDGED_SUCCESS', 0)],
    ['failure', intent.get('FAILURE', 0)],
    ['unclear', intent.get('UNCLEAR', 0)],
    ['outcome_completed', outc.get('COMPLETED', 0)],
    ['outcome_not_completed', outc.get('NOT_COMPLETED', 0)],
    ['outcome_unsure', outc.get('UNSURE', 0)],
    ['gold_by_agreement', prov.get('agreement', 0)],
    ['gold_by_adjudication', prov.get('adjudicated', 0)],
    ['dangerous_misreports', sum(1 for r in U if v3[r]['intent'] == 'UNHEDGED_SUCCESS' and v3[r]['outcome'] == 'NOT_COMPLETED')],
    ['screenshot_coverage', shots],
]
with open(RES / 'data_pipeline.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['stage', 'count']); w.writerows(prows)
print('-> wrote data_pipeline.csv:', {k: v for k, v in prows})
