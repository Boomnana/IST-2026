"""把 checkability spectrum 锚到 human-on-trace ground truth(解 circularity + 坐实主贡献)。
用 mibv A/B 双标 per-record outcome_label(claim-blind,全 465)作"human 看 trace 能否判 NC"的外部标签:
- human-on-trace ceiling(复算 .897/.949)
- spectrum 层(set C) x human-catch 率: 验证 human-checkability 随 verifier 层单调(非循环,human 独立)
- residual(verifier 都漏)的 human 归因: passive-uncheckable(human 也漏)vs verifier-gap(human 抓到)
- dev/test holdout 分别报
zero-API; 读 xlsx 用 pandas。
"""
import json, sys, glob
from pathlib import Path
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
import pandas as pd
from _paths import XP, LEG, MB, ORS, RES
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
v3={json.loads(l)['record_id']:json.loads(l) for l in open(XP/'data/gold/final_labels_v3.jsonl',encoding='utf-8') if l.strip()}
U=set(v3); POS={r for r in U if v3[r]['intent']=='UNHEDGED_SUCCESS' and v3[r]['outcome']=='NOT_COMPLETED'}
# human labels (A/B complete, claim-blind outcome)
A=pd.read_excel(ORS/'inputs/iaa/iaa_sample_annotator_A_complete.xlsx').set_index('record_id')
B=pd.read_excel(ORS/'inputs/iaa/iaa_sample_annotator_B_complete.xlsx').set_index('record_id')
def hout(df,r): return str(df.loc[r,'outcome_label']).strip().upper() if r in df.index else None
def human_NC(r): return hout(A,r)=='NOT_COMPLETED' and hout(B,r)=='NOT_COMPLETED'   # both-agree (high-conf)
# verifier channels (deepseek, set C: bare + MIBVblind)
dsb=[load(LEG/f'experiments/rq1_2_baseline_judge_failure/outputs/deepseek_baseline_run{i}.jsonl') for i in range(1,6)]
dsm=[load(LEG/f'experiments/rq4_1_cross_model/outputs/deepseek_mibv_run{i}.jsonl') for i in range(1,6)]
dsc=load(LEG/'experiments/rq4_1_cross_model/outputs/deepseek_claim_conveyance_v2_run1.jsonl')
def mibv_v(s,c):
    if s=='UNKNOWN' or c=='UNCLEAR': return 'REVIEW'
    if s=='COMPLETED' and c=='SUCCESS': return 'PASS'
    if s=='NOT_COMPLETED' and c=='FAILURE_OR_INCOMPLETE': return 'PASS'
    return 'FLAG'
oc={r:sum(1 for x in dsb if x.get(r,{}).get('outcome_verdict')=='NOT_COMPLETED') for r in U}
ic={r:sum(1 for x in dsb if x.get(r,{}).get('claim_verdict')=='INCONSISTENT') for r in U}
mb_={r:sum(1 for x in dsm if x.get(r,{}).get('completion') and dsc.get(r,{}).get('conveys') and mibv_v(x.get(r,{}).get('completion'),dsc.get(r,{}).get('conveys'))=='FLAG') for r in U}
def nindep(r): return (1 if max(oc[r],ic[r])>=3 else 0)+(1 if mb_[r]>=3 else 0)
def layer(r):
    n=nindep(r); return 'redundant' if n==2 else ('silent' if n==0 else 'fragile')
# holdout split
split=json.loads((ORS/'outputs/rq3_4_holdout_split.json').read_text(encoding='utf-8'))
DEV=set(split['dev']); TEST=set(split['test'])

def prf(pred,pos):
    pred=pred&U; tp=len(pred&pos); fp=len(pred-pos); fn=len(pos-pred)
    p=tp/(tp+fp) if tp+fp else 0; r=tp/(tp+fn) if tp+fn else 0
    return p,r,(2*p*r/(p+r) if p+r else 0)

print('='*70); print('human-anchored checkability (deepseek set C, both-annotator human trace channel)'); print('='*70)
# 1) human-on-trace ceiling (sanity: should ~ .897/.949/.922)
print('\n[1] human-on-trace ceiling (claim-blind human outcome as detector)')
for name,df in (('A',A),('B',B)):
    Dh={r for r in U if v3[r]['intent']=='UNHEDGED_SUCCESS' and hout(df,r)=='NOT_COMPLETED'}
    p,r,f=prf(Dh,POS); print(f'  annotator {name}: P={p:.3f} R={r:.3f} F1={f:.3f}')
both={r for r in U if v3[r]['intent']=='UNHEDGED_SUCCESS' and human_NC(r)}
p,r,f=prf(both,POS); print(f'  both-agree: P={p:.3f} R={r:.3f} F1={f:.3f}')

# 2) spectrum layer x human-catch (independence: human is NOT a verifier channel)
print('\n[2] human-catch rate by verifier layer (human-checkability INDEPENDENT of verifier vote)')
def report_layers(scope,name):
    pos=POS&scope if scope else POS
    print(f'  -- {name} (POS={len(pos)}) --')
    for L in ('redundant','fragile','silent'):
        rs=[r for r in pos if layer(r)==L]
        if not rs: print(f'     {L:10s}: n=0'); continue
        hc=sum(1 for r in rs if human_NC(r))
        print(f'     {L:10s}: n={len(rs):3d}  human-catch {hc}/{len(rs)} = {100*hc/len(rs):.1f}%')
report_layers(None,'ALL')
report_layers(DEV,'DEV'); report_layers(TEST,'TEST')

# 3) residual attribution: verifier-silent POS -> human catch (verifier-gap) vs human miss (passive-uncheckable)
print('\n[3] verifier-silent (set C nindep==0) residual -> human attribution')
def attr(scope,name):
    sil=[r for r in (POS&scope if scope else POS) if nindep(r)==0]
    vg=[r for r in sil if human_NC(r)]; pu=[r for r in sil if not human_NC(r)]
    print(f'  {name}: silent={len(sil)}  verifier-gap(human catches)={len(vg)}  PASSIVE-UNCHECKABLE(human also misses)={len(pu)}')
    return pu
attr(None,'ALL'); attr(DEV,'DEV'); pu_test=attr(TEST,'TEST')
pu_all=[r for r in POS if nindep(r)==0 and not human_NC(r)]
print(f'\n  ==> PASSIVE-UNCHECKABLE core (verifier-silent AND human-both also miss): {len(pu_all)}')
for r in sorted(pu_all): print(f'      {fam(r):8s} {r.split("__")[0]}')
# ---- write results csv ----
import csv as _csv
# RES imported from _paths (package-local)
rows=[]
for nm,df in (('A',A),('B',B)):
    Dh={r for r in U if v3[r]['intent']=='UNHEDGED_SUCCESS' and hout(df,r)=='NOT_COMPLETED'}
    p,r,f=prf(Dh,POS); rows.append(['ceiling',nm,'',round(p,3),round(r,3),round(f,3)])
p,r,f=prf(both,POS); rows.append(['ceiling','both','',round(p,3),round(r,3),round(f,3)])
for sc,scope in (('ALL',None),('DEV',DEV),('TEST',TEST)):
    pos=POS&scope if scope else POS
    for L in ('redundant','fragile','silent'):
        rs=[x for x in pos if layer(x)==L]; hc=sum(1 for x in rs if human_NC(x))
        rows.append(['human_catch',sc,L,len(rs),hc,round(100*hc/len(rs),1) if rs else 0])
    sil=[x for x in pos if nindep(x)==0]; vg=sum(1 for x in sil if human_NC(x))
    rows.append(['residual',sc,'silent/verifier-gap/passive-uncheckable',len(sil),vg,len(sil)-vg])
with open(RES/'rq_human_anchored.csv','w',newline='',encoding='utf-8') as fp:
    w=_csv.writer(fp); w.writerow(['block','scope','key','n_or_P','catch_or_R','pct_or_F1']); w.writerows(rows)
with open(RES/'rq_human_anchored_core.csv','w',newline='',encoding='utf-8') as fp:
    w=_csv.writer(fp); w.writerow(['record_id','family'])
    for x in sorted(pu_all): w.writerow([x,fam(x)])
print('wrote results/rq_human_anchored.csv + _core.csv')
print('\nDONE human-anchored.')
