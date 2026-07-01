"""(1) Independently compute inter-annotator agreement (Cohen's kappa + raw + adjudication rate)
for the outcome_label and claim_intent_label fields from the A/B IAA xlsx, to put real numbers in
the paper instead of citing [mibv]. (2) RQ4 carrier-controlled check: is 'verifier redundancy
predicts construct-robustness' independent of delete-vacuous, or collinear with it? zero-API."""
import json, sys, collections
from pathlib import Path
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
import pandas as pd
from _paths import XP, LEG, MB, ORS, RES

def cohen(pairs):
    pairs=[(str(a).strip().upper(),str(b).strip().upper()) for a,b in pairs
           if str(a).strip() not in ('','NAN','NONE') and str(b).strip() not in ('','NAN','NONE')]
    n=len(pairs)
    if not n: return 0,0,0
    po=sum(1 for a,b in pairs if a==b)/n
    ca=collections.Counter(a for a,b in pairs); cb=collections.Counter(b for a,b in pairs)
    cats=set(ca)|set(cb)
    pe=sum((ca[c]/n)*(cb[c]/n) for c in cats)
    k=(po-pe)/(1-pe) if pe<1 else 1.0
    return po,k,n
def bink(pairs,pos):  # binarize: label==pos vs not
    return cohen([(1 if str(a).strip().upper()==pos else 0, 1 if str(b).strip().upper()==pos else 0) for a,b in pairs])

A=pd.read_excel(ORS/'inputs/iaa/iaa_sample_annotator_A_complete.xlsx').set_index('record_id')
B=pd.read_excel(ORS/'inputs/iaa/iaa_sample_annotator_B_complete.xlsx').set_index('record_id')
common=[r for r in A.index if r in B.index]
print('='*72); print(f'(1) INTER-ANNOTATOR AGREEMENT  (A,B both present: {len(common)})'); print('='*72)
for fld in ('outcome_label','claim_intent_label'):
    pairs=[(A.loc[r,fld],B.loc[r,fld]) for r in common]
    po,k,n=cohen(pairs)
    print(f'\n  [{fld}]  n={n}  raw-agreement={po:.3f}  Cohen-kappa={k:.3f}')
    print(f'     value set A={dict(collections.Counter(str(A.loc[r,fld]).strip().upper() for r in common))}')
    if fld=='outcome_label':
        po2,k2,n2=bink(pairs,'NOT_COMPLETED'); print(f'     binary NC-vs-not: raw={po2:.3f} kappa={k2:.3f}')
    if fld=='claim_intent_label':
        po2,k2,n2=bink(pairs,'UNHEDGED_SUCCESS'); print(f'     binary UNHEDGED_SUCCESS-vs-not: raw={po2:.3f} kappa={k2:.3f}')
    adj=sum(1 for a,b in pairs if str(a).strip().upper()!=str(b).strip().upper())
    print(f'     disagreement(adjudication) rate = {adj}/{n} = {100*adj/n:.1f}%')

# ---- AUTHORITATIVE label-quality kappa = inter-annotator agreement on the RECONCILED reference labels.
# These are the paper's reported numbers. Source = reconciled IAA files, worksheet 'annotation'
# (NOT the default summary sheet, and NOT the pre-reconciliation _complete files which give the raw
# 0.69/0.70/0.65 printed above). Matches RACER 05_recompute_data_label_quality.py exactly. ----
def _recon(fname): return pd.read_excel(ORS/'inputs/iaa'/fname, sheet_name='annotation').set_index('record_id')
Ar=_recon('iaa_sample_annotator_A_reconciled_kappa075plus.xlsx')
Br=_recon('iaa_sample_annotator_B_reconciled_kappa075plus.xlsx')
rids=sorted(set(Ar.index)&set(Br.index))
def _kap(av,bv): po,k,_=cohen(list(zip(av,bv))); return po,k
po_o,k_o=_kap([Ar.loc[r,'outcome_label'] for r in rids],[Br.loc[r,'outcome_label'] for r in rids])
po_i,k_i=_kap([Ar.loc[r,'claim_intent_label'] for r in rids],[Br.loc[r,'claim_intent_label'] for r in rids])
def _dm(df,r): return 'DM' if (str(df.loc[r,'claim_intent_label']).strip().upper()=='UNHEDGED_SUCCESS'
                              and str(df.loc[r,'outcome_label']).strip().upper()=='NOT_COMPLETED') else 'NOT'
po_d,k_d=_kap([_dm(Ar,r) for r in rids],[_dm(Br,r) for r in rids])
print(f'\n[reconciled label-quality kappa (paper values)] n={len(rids)}  '
      f'outcome={k_o:.3f} intent={k_i:.3f} derived={k_d:.3f}  raw {100*po_o:.1f}/{100*po_i:.1f}/{100*po_d:.1f}%')
import csv as _csv
with open(RES/'rq_kappa.csv','w',newline='',encoding='utf-8') as f:
    w=_csv.writer(f); w.writerow(['label','raw_pct','kappa'])
    w.writerow(['outcome',f'{100*po_o:.1f}',f'{k_o:.3f}'])
    w.writerow(['intent', f'{100*po_i:.1f}',f'{k_i:.3f}'])
    w.writerow(['derived',f'{100*po_d:.1f}',f'{k_d:.3f}'])
print(f'-> wrote {RES/"rq_kappa.csv"} (authoritative reconciled label-quality kappa)')

# ---- (2) RQ4 carrier-controlled ----
print('\n'+'='*72); print('(2) RQ4 control: redundancy->robustness, with vs without delete-vacuous'); print('='*72)
def load(p):
    d={}
    for l in open(p,encoding='utf-8'):
        l=l.strip()
        if not l: continue
        r=json.loads(l)
        if r.get('_header'): continue
        d[r['record_id']]=r
    return d
def is_delete(r): t=r.split('__')[0].lower(); return any(k in t for k in ('delete','remove','clear','duplicate'))
v3=load(XP/'data/gold/final_labels_v3.jsonl'); U=set(v3)
old={}
for l in open(XP/'data/derived_gold_for_comparison/sampled_records.jsonl',encoding='utf-8'):
    l=l.strip()
    if l:
        r=json.loads(l)
        if r.get('record_id') in U: old[r['record_id']]=r
US={r for r in U if v3[r]['intent']=='UNHEDGED_SUCCESS'}
POS_c={r for r in US if v3[r]['outcome']=='NOT_COMPLETED'}
POS_e={r for r in US if old.get(r,{}).get('outcome_gold')=='NOT_COMPLETED'}
def mibv_v(s,c):
    if s=='UNKNOWN' or c=='UNCLEAR': return 'REVIEW'
    if s=='COMPLETED' and c=='SUCCESS': return 'PASS'
    if s=='NOT_COMPLETED' and c=='FAILURE_OR_INCOMPLETE': return 'PASS'
    return 'FLAG'
dsb=[load(LEG/f'experiments/rq1_2_baseline_judge_failure/outputs/deepseek_baseline_run{i}.jsonl') for i in range(1,6)]
dsm=[load(LEG/f'experiments/rq4_1_cross_model/outputs/deepseek_mibv_run{i}.jsonl') for i in range(1,6)]
dsc=load(LEG/'experiments/rq4_1_cross_model/outputs/deepseek_claim_conveyance_v2_run1.jsonl')
oc={r:sum(1 for x in dsb if x.get(r,{}).get('outcome_verdict')=='NOT_COMPLETED') for r in U}
ic={r:sum(1 for x in dsb if x.get(r,{}).get('claim_verdict')=='INCONSISTENT') for r in U}
mb={r:sum(1 for x in dsm if x.get(r,{}).get('completion') and dsc.get(r,{}).get('conveys') and mibv_v(x[r]['completion'],dsc[r]['conveys'])=='FLAG') for r in U}
bare={r:max(oc[r],ic[r]) for r in U}
def nindep(r): return (1 if bare[r]>=3 else 0)+(1 if mb[r]>=3 else 0)
def wilson(k,n,z=1.96):
    import math
    if n==0: return (0,0)
    p=k/n; den=1+z*z/n; c=(p+z*z/(2*n))/den; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den; return (c-h,c+h)
def surv(grp):
    s=sum(1 for r in grp if r in POS_e); n=len(grp); lo,hi=wilson(s,n)
    return s,n,(100*s/n if n else 0),100*lo,100*hi
for label,subset in (('ALL POS_c',POS_c),('non-delete-vacuous only',{r for r in POS_c if not is_delete(r)}),('delete-vacuous only',{r for r in POS_c if is_delete(r)})):
    hi=[r for r in subset if nindep(r)==2]; lo=[r for r in subset if nindep(r)<2]
    sh=surv(hi); sl=surv(lo)
    print(f'\n  [{label}]  (n={len(subset)})')
    print(f'    high-checkable(nindep=2): survive {sh[0]}/{sh[1]} = {sh[2]:.1f}% [{sh[3]:.1f},{sh[4]:.1f}]')
    print(f'    low-checkable (nindep<2): survive {sl[0]}/{sl[1]} = {sl[2]:.1f}% [{sl[3]:.1f},{sl[4]:.1f}]')
print('\nDONE.')
