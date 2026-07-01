"""Checkability-Boundary 资产校验门（规划 §1.6）。复现第一步：全 PASS 才进 RQ。
只读 X_paper / mibv / (NEW-IDEA 回退)；派生 labels/record_id_action_type.csv。zero-API 纯标准库。
"""
import json, csv
from pathlib import Path
from collections import defaultdict

from _paths import XP, LEG, MB, NEW, HERE
(HERE/'labels').mkdir(parents=True, exist_ok=True)

def loadl(p):
    out=[]
    if not Path(p).exists(): return out
    for l in open(p,encoding='utf-8'):
        l=l.strip()
        if not l: continue
        r=json.loads(l)
        if isinstance(r,dict) and r.get('_header'): continue
        out.append(r)
    return out
def load(p): return {r['record_id']:r for r in loadl(p)}
def fam(r):
    q=str(r).split('__'); return q[1] if len(q)>1 and q[1] in ('appagent','mav3') else 'other'

PASS=[]; FAIL=[]; NOTE=[]
def chk(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('  [PASS] ' if cond else '  [FAIL] ')+f'{name}'+(f'  | {detail}' if detail else ''))
def note(name, detail): NOTE.append((name,detail)); print(f'  [note] {name}  | {detail}')

print('='*70); print('00 ASSETS CHECK'); print('='*70)

# ---- 1. gold + caliber ----
print('\n[1] gold & caliber constants')
v3 = load(XP/'data/gold/final_labels_v3.jsonl')
U = set(v3); POS = {r for r in U if v3[r]['intent']=='UNHEDGED_SUCCESS' and v3[r]['outcome']=='NOT_COMPLETED'}
chk('U == 465', len(U)==465, f'{len(U)}')
chk('POS == 180', len(POS)==180, f'{len(POS)}')
uf = {f:sum(1 for r in U if fam(r)==f) for f in ('appagent','mav3')}
pf = {f:sum(1 for r in POS if fam(r)==f) for f in ('appagent','mav3')}
chk('U family 177/288', uf=={'appagent':177,'mav3':288}, str(uf))
chk('POS family 90/90', pf=={'appagent':90,'mav3':90}, str(pf))

# ---- 2. verifier caches: exist / in-U coverage / key non-null ----
print('\n[2] verifier caches')
CACHES = {
 'baseline':      ([LEG/f'experiments/rq1_2_baseline_judge_failure/outputs/deepseek_baseline_run{i}.jsonl' for i in range(1,6)], ('outcome_verdict','claim_verdict')),
 'mibv_state':    ([LEG/f'experiments/rq4_1_cross_model/outputs/deepseek_mibv_run{i}.jsonl' for i in range(1,6)], ('completion',)),
 'conveyance':    ([LEG/'experiments/rq4_1_cross_model/outputs/deepseek_claim_conveyance_v2_run1.jsonl'], ('conveys','hedged')),
 'conservative':  ([XP/f'experiments/rq4_conservative_baseline/outputs/conservative_dpsk_run{i}.jsonl' for i in range(1,6)], ('outcome_verdict',)),
 'action_verify': ([XP/f'experiments/rq7_action_audit/outputs/verify_run{i}.jsonl' for i in range(1,6)], ('verdict',)),
 'vision_qwenvl': ([LEG/'experiments/rq2_2_modern_baselines/outputs/aer_vision_qwenvl_run1.jsonl'], ('aer_alarm',)),
 'vision_235b':   ([LEG/'experiments/rq2_2_modern_baselines/outputs/aer_vision_qwen3vl235b_run1.jsonl'], ('aer_alarm',)),
 'qwen_baseline': ([LEG/f'experiments/rq1_2_baseline_judge_failure/outputs/qwen_baseline_run{i}.jsonl' for i in range(1,6)], ('outcome_verdict',)),
 'qwen_mibv':     ([LEG/f'experiments/rq2_1_mibv_main/outputs/qwen_mibv_run{i}.jsonl' for i in range(1,6)], ('completion',)),
 'qwen_conv':     ([LEG/'experiments/rq4_1_cross_model/outputs/qwen_claim_conveyance_v2_run1.jsonl'], ('conveys',)),
}
for name,(paths,keys) in CACHES.items():
    miss=[p for p in paths if not Path(p).exists()]
    if miss: chk(f'{name} files exist', False, f'missing {len(miss)}: {miss[0].name}'); continue
    d0=load(paths[0]); inU=len(set(d0)&U)
    nonnull={k: sum(1 for r in U if d0.get(r,{}).get(k) not in (None,'')) for k in keys}
    chk(f'{name} exist+inU', inU==465, f'{len(paths)} runs, run1 in-U={inU}, nonnull={nonnull}')

# ---- 3. reasoning asymmetry ----
print('\n[3] reasoning asymmetry in judge inputs')
def reason_rate(p):
    rows=loadl(p); per=defaultdict(lambda:[0,0])
    for r in rows:
        rid=r.get('record_id');
        if rid not in U: continue
        for s in (r.get('steps') or []):
            rs=s.get('agent_reasoning'); per[fam(rid)][0]+=1; per[fam(rid)][1]+= rs not in (None,'',[])
    return {f:(round(100*c[1]/c[0]) if c[0] else None) for f,c in per.items()}
jc=reason_rate(XP/'data/raw_compact/judge_inputs.jsonl')
jr=reason_rate(MB/'experiments/oracle_separation/inputs/judge_inputs_reasoning.jsonl')
chk('judge_inputs: appagent 100% / mav3 0%', jc.get('appagent')==100 and jc.get('mav3')==0, str(jc))
chk('judge_inputs_reasoning: mav3 >=95%', (jr.get('mav3') or 0)>=95, str(jr))

# ---- 4. same-source baseline (100%) + record MIBV estimator rate ----
print('\n[4] cross-repo same-source')
def agree(A,B,field):
    ag=tot=0
    for i in range(min(len(A),len(B))):
        for r in (set(A[i])&set(B[i])&U):
            a=A[i][r].get(field); b=B[i][r].get(field)
            if a and b: tot+=1; ag+=(a==b)
    return ag,tot
xb=[load(LEG/f'experiments/rq1_2_baseline_judge_failure/outputs/deepseek_baseline_run{i}.jsonl') for i in range(1,6)]
mb_b=[load(MB/f'experiments/rq1_2_baseline_judge_failure/outputs/deepseek_baseline_run{i}.jsonl') for i in range(1,6)]
ag,tot=agree(xb,mb_b,'outcome_verdict')
chk('baseline cross-repo 100% same-source', tot>0 and ag==tot, f'{ag}/{tot}')
xm=[load(LEG/f'experiments/rq4_1_cross_model/outputs/deepseek_mibv_run{i}.jsonl') for i in range(1,6)]
mb_bl=[load(MB/f'experiments/oracle_separation/outputs/separated_blind_deepseek_run{i}.jsonl') for i in range(1,6)]
ag2,tot2=agree(xm,mb_bl,'completion')
note('MIBV estimator same-source rate (proxy caveat)', f'{ag2}/{tot2} = {100*ag2/tot2 if tot2 else 0:.1f}% (expect ~87.9%)')

# ---- 5. raw signals: screenshots + action_resolved ----
print('\n[5] raw signal assets')
RAW = XP/'data/raw_with_img'
if RAW.exists():
    pngs=list(RAW.rglob('screenshot.png'))
    chk('screenshots > 5000', len(pngs)>5000, f'{len(pngs)} screenshot.png')
    ar=list(RAW.rglob('action_resolved.json'))
    ar_recs={p.parts[len(RAW.parts)] for p in ar}
    app_recs={r for r in U if fam(r)=='appagent'}
    cov=len(ar_recs & {r for r in U})
    note('action_resolved.json', f'{len(ar)} files across {len(ar_recs)} run-dirs; appagent POS-side coverage downstream')
else:
    chk('raw_with_img exists', False, 'MISSING')

# ---- 6. derive record_id_action_type.csv ----
print('\n[6] derive action_type table')
out=HERE/'labels/record_id_action_type.csv'
src_csv = NEW/'data/record_id_action_type.csv'
rows=[]
if src_csv.exists():
    with open(src_csv,encoding='utf-8') as f:
        rd=csv.DictReader(f)
        for row in rd:
            rid=row.get('record_id')
            if rid in U: rows.append((rid, row.get('action_type') or row.get('action') or 'unknown', 'NEW-IDEA-csv'))
    note('action_type source', f'copied {len(rows)} from NEW-IDEA csv')
if len(rows) < len(U):
    have={r[0] for r in rows}
    for r in U:
        if r in have: continue
        # fallback: derive a coarse class from the task-name token of record_id
        tok=r.split('__')[0]
        lt=tok.lower()
        cls=('delete' if 'delete' in lt else 'create' if any(k in lt for k in ('create','add','new')) else
             'toggle' if any(k in lt for k in ('toggle','enable','disable','turn')) else
             'send' if any(k in lt for k in ('send','share','email','sms','message')) else
             'media' if any(k in lt for k in ('camera','photo','record','audio','video')) else
             'query' if any(k in lt for k in ('open','search','find','navigate','view')) else 'other')
        rows.append((r, cls, 'recordid-heuristic'))
with open(out,'w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(['record_id','action_type','source_of_type']); w.writerows(sorted(rows))
chk('action_type derived for all U', len({x[0] for x in rows})==len(U), f'{len(rows)} -> {out}')
from collections import Counter
note('action_type dist', str(dict(Counter(x[1] for x in rows))))

# ---- summary ----
print('\n'+'='*70)
print(f'RESULT: {len(PASS)} PASS / {len(FAIL)} FAIL / {len(NOTE)} notes')
if FAIL: print('FAILS:', FAIL)
print('='*70)
