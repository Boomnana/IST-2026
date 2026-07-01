"""RQ1/RQ2 NEW §construct-relativity (V2)。zero-API stdlib。
固定 unhedged-claim,把 gold 从 causal(final_labels_v3.outcome) 换成 end-state(sampled_records.outcome_gold):
正类重排多少? lost 群是否富集 delete-vacuous? verifier redundancy 是否预测 gold-鲁棒性? 谱是否被洗白?
"""
import json, sys, collections
from pathlib import Path
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
from _paths import XP, LEG
def load(p):
    d={}
    for l in open(p,encoding='utf-8'):
        l=l.strip()
        if not l: continue
        r=json.loads(l)
        if r.get('_header'): continue
        d[r['record_id']]=r
    return d
def fam(r):
    q=r.split('__'); return q[1] if len(q)>1 and q[1] in ('appagent','mav3') else 'other'
def is_delete(r): t=r.split('__')[0].lower(); return any(k in t for k in ('delete','remove','clear','duplicate'))
v3={json.loads(l)['record_id']:json.loads(l) for l in open(XP/'data/gold/final_labels_v3.jsonl',encoding='utf-8') if l.strip()}
U=set(v3)
old={}
for l in open(XP/'data/derived_gold_for_comparison/sampled_records.jsonl',encoding='utf-8'):
    l=l.strip()
    if l:
        r=json.loads(l)
        if r.get('record_id') in U: old[r['record_id']]=r
US={r for r in U if v3[r]['intent']=='UNHEDGED_SUCCESS'}
POS_c={r for r in US if v3[r]['outcome']=='NOT_COMPLETED'}
POS_e={r for r in US if old.get(r,{}).get('outcome_gold')=='NOT_COMPLETED'}
stable=POS_c&POS_e; lost=POS_c-POS_e; gained=POS_e-POS_c
jac=len(stable)/len(POS_c|POS_e)
print('='*72); print('§construct-relativity: causal vs end-state gold (unhedged claim fixed)'); print('='*72)
print(f'\n|unhedged-claim US|={len(US)}   POS_causal={len(POS_c)}  POS_endstate={len(POS_e)}')
print(f'stable={len(stable)}  lost(causal-only)={len(lost)}  gained(endstate-only)={len(gained)}  Jaccard={jac:.3f}  survive={len(stable)/len(POS_c)*100:.1f}%')
print(f'\n[lost group carrier enrichment]  delete-vacuous in lost {sum(1 for r in lost if is_delete(r))}/{len(lost)}  vs  in stable {sum(1 for r in stable if is_delete(r))}/{len(stable)}')
print(f'  lost family={dict(collections.Counter(fam(r) for r in lost))}  gained family={dict(collections.Counter(fam(r) for r in gained))}')

# spectrum (set C: bare + MIBVblind, deepseek) under both positive classes
def mibv_v(s,c):
    if s=='UNKNOWN' or c=='UNCLEAR': return 'REVIEW'
    if s=='COMPLETED' and c=='SUCCESS': return 'PASS'
    if s=='NOT_COMPLETED' and c=='FAILURE_OR_INCOMPLETE': return 'PASS'
    return 'FLAG'
def votes(runs,f,v): return {r:sum(1 for x in runs if x.get(r,{}).get(f)==v) for r in U}
def mvotes(runs,conv): return {r:sum(1 for x in runs if x.get(r,{}).get('completion') and conv.get(r,{}).get('conveys') and mibv_v(x.get(r,{}).get('completion'),conv.get(r,{}).get('conveys'))=='FLAG') for r in U}
dsb=[load(LEG/f'experiments/rq1_2_baseline_judge_failure/outputs/deepseek_baseline_run{i}.jsonl') for i in range(1,6)]
dsm=[load(LEG/f'experiments/rq4_1_cross_model/outputs/deepseek_mibv_run{i}.jsonl') for i in range(1,6)]
dsc=load(LEG/'experiments/rq4_1_cross_model/outputs/deepseek_claim_conveyance_v2_run1.jsonl')
oc=votes(dsb,'outcome_verdict','NOT_COMPLETED'); ic=votes(dsb,'claim_verdict','INCONSISTENT'); mb=mvotes(dsm,dsc)
bare={r:max(oc[r],ic[r]) for r in U}
def nindep(r): return (1 if bare[r]>=3 else 0)+(1 if mb[r]>=3 else 0)
def spec(pos):
    n={r:nindep(r) for r in pos}
    red=sum(1 for r in pos if n[r]==2); sil=sum(1 for r in pos if n[r]==0); fra=len(pos)-red-sil
    return red,fra,sil
rc=spec(POS_c); re=spec(POS_e)
print(f'\n[spectrum set-C under each gold]  (redundant/fragile/silent)')
print(f'  causal   ({len(POS_c)}): {rc[0]}/{rc[1]}/{rc[2]} = {100*rc[0]/len(POS_c):.1f}/{100*rc[1]/len(POS_c):.1f}/{100*rc[2]/len(POS_c):.1f}%')
print(f'  endstate ({len(POS_e)}): {re[0]}/{re[1]}/{re[2]} = {100*re[0]/len(POS_e):.1f}/{100*re[1]/len(POS_e):.1f}/{100*re[2]/len(POS_e):.1f}%  <- redundant share inflated by discarding hard cases')

# redundancy predicts survival under gold swap
print(f'\n[does verifier redundancy predict survival to the gold swap?]  (among causal POS)')
for nv in (0,1,2):
    grp=[r for r in POS_c if nindep(r)==nv]
    surv=sum(1 for r in grp if r in POS_e)
    print(f'  nindep={nv}: survive {surv}/{len(grp)} = {100*surv/len(grp) if grp else 0:.1f}%')
hi=[r for r in POS_c if nindep(r)>=2]; lo=[r for r in POS_c if nindep(r)<2]
print(f'  high-checkable(nindep==2) survive {sum(1 for r in hi if r in POS_e)}/{len(hi)}={100*sum(1 for r in hi if r in POS_e)/len(hi):.1f}%  vs  low survive {sum(1 for r in lo if r in POS_e)}/{len(lo)}={100*sum(1 for r in lo if r in POS_e)/len(lo):.1f}%')
print('\nDONE construct-relativity.')
