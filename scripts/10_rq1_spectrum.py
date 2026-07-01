"""RQ1 正式版(对抗审查 V2 口径)。zero-API stdlib。
- per-channel x family 判别门(排除反信息通道)
- 合并 outcomeNC+claimINC = 单一 bare-judge;DROP action
- 谱按 3 个 defensible channel-set x 2 backbone 报(区间);merged not-redundantly-checkable + Wilson CI
- held-out confidence axis(conservative+MIBVaware,不在分层内)做可证伪 H1(非同向量恒等式)
- silent 三阈值(1/3/5-of-5) + cross-model intersection core
"""
import json, sys, math, collections
from pathlib import Path
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
from _paths import XP, LEG, MB
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
def wilson(k,n,z=1.96):
    if n==0: return (0.0,0.0)
    p=k/n; den=1+z*z/n; c=(p+z*z/(2*n))/den
    h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den; return (c-h,c+h)
def rankdata(a):
    order=sorted(range(len(a)),key=lambda i:a[i]); rk=[0.0]*len(a); i=0
    while i<len(a):
        j=i
        while j<len(a) and a[order[j]]==a[order[i]]: j+=1
        r=(i+j-1)/2+1
        for k in range(i,j): rk[order[k]]=r
        i=j
    return rk
def pearson(x,y):
    n=len(x); mx=sum(x)/n; my=sum(y)/n
    cov=sum((x[i]-mx)*(y[i]-my) for i in range(n))
    sx=math.sqrt(sum((v-mx)**2 for v in x)); sy=math.sqrt(sum((v-my)**2 for v in y))
    return cov/(sx*sy) if sx*sy else 0.0
def spearman(x,y): return pearson(rankdata(x),rankdata(y))

v3={json.loads(l)['record_id']:json.loads(l) for l in open(XP/'data/gold/final_labels_v3.jsonl',encoding='utf-8') if l.strip()}
U=set(v3); POS={r for r in U if v3[r]['intent']=='UNHEDGED_SUCCESS' and v3[r]['outcome']=='NOT_COMPLETED'}; NEG=U-POS
BASE=len(POS)/len(U)
def mibv_v(s,c):
    if s=='UNKNOWN' or c=='UNCLEAR': return 'REVIEW'
    if s=='COMPLETED' and c=='SUCCESS': return 'PASS'
    if s=='NOT_COMPLETED' and c=='FAILURE_OR_INCOMPLETE': return 'PASS'
    return 'FLAG'
def votes(runs,f,v): return {r:sum(1 for x in runs if x.get(r,{}).get(f)==v) for r in U}
def mvotes(runs,conv): return {r:sum(1 for x in runs if x.get(r,{}).get('completion') and conv.get(r,{}).get('conveys') and mibv_v(x.get(r,{}).get('completion'),conv.get(r,{}).get('conveys'))=='FLAG') for r in U}

# ---- deepseek channels ----
dsb=[load(LEG/f'experiments/rq1_2_baseline_judge_failure/outputs/deepseek_baseline_run{i}.jsonl') for i in range(1,6)]
dsm=[load(LEG/f'experiments/rq4_1_cross_model/outputs/deepseek_mibv_run{i}.jsonl') for i in range(1,6)]
dsc=load(LEG/'experiments/rq4_1_cross_model/outputs/deepseek_claim_conveyance_v2_run1.jsonl')
ver=[load(XP/f'experiments/rq7_action_audit/outputs/verify_run{i}.jsonl') for i in range(1,6)]
cons=[load(XP/f'experiments/rq4_conservative_baseline/outputs/conservative_dpsk_run{i}.jsonl') for i in range(1,6)]
awa=[load(MB/f'experiments/oracle_separation/outputs/separated_aware_deepseek_run{i}.jsonl') for i in range(1,6)]
D={'outcomeNC':votes(dsb,'outcome_verdict','NOT_COMPLETED'),'claimINC':votes(dsb,'claim_verdict','INCONSISTENT'),
   'MIBVblind':mvotes(dsm,dsc),'action':votes(ver,'verdict','ALARM'),
   'conservative':votes(cons,'outcome_verdict','NOT_COMPLETED'),'MIBVaware':mvotes(awa,dsc)}
D['bare']={r:max(D['outcomeNC'][r],D['claimINC'][r]) for r in U}
# ---- qwen channels ----
qwb=[load(LEG/f'experiments/rq1_2_baseline_judge_failure/outputs/qwen_baseline_run{i}.jsonl') for i in range(1,6)]
qwm=[load(LEG/f'experiments/rq2_1_mibv_main/outputs/qwen_mibv_run{i}.jsonl') for i in range(1,6)]
qwc=load(LEG/'experiments/rq4_1_cross_model/outputs/qwen_claim_conveyance_v2_run1.jsonl')
Q={'outcomeNC':votes(qwb,'outcome_verdict','NOT_COMPLETED'),'claimINC':votes(qwb,'claim_verdict','INCONSISTENT'),
   'MIBVblind':mvotes(qwm,qwc),'action':votes(ver,'verdict','ALARM')}
Q['bare']={r:max(Q['outcomeNC'][r],Q['claimINC'][r]) for r in U}

# ===== 1. per-channel x family discrimination gate =====
print('='*72); print(f'RQ1 spectrum (V2)   base rate POS/U={len(POS)}/{len(U)}={BASE:.3f}'); print('='*72)
print('\n[discrimination gate]  exclude if lift<=0 OR POSflag<=NEGflag OR cross-family ratio>2x')
def disc(V,k):
    A={r for r in U if V[k][r]>=3}; prec=len(A&POS)/len(A) if A else 0
    pf=len(A&POS)/len(POS); nf=len(A&NEG)/len(NEG)
    ra={f:len({r for r in A if r in POS and fam(r)==f})/90 for f in ('appagent','mav3')}
    ratio=max(ra.values())/min(ra.values()) if min(ra.values())>0 else float('inf')
    excl = prec<=BASE or pf<=nf or ratio>2
    return prec,pf,nf,ratio,excl
for k in ('outcomeNC','claimINC','bare','MIBVblind','action','conservative'):
    prec,pf,nf,ratio,excl=disc(D,k)
    print(f'  {k:12s} prec={prec:.3f} POSflag={pf:.3f} NEGflag={nf:.3f} fam-ratio={ratio:.2f}  {"EXCLUDE" if excl else "keep"}')

# ===== 2. spectra across channel-sets x backbone =====
SETS={'A v1 (4ch, +action)':('outcomeNC','claimINC','MIBVblind','action'),
      'B (bare+MIBV+action)':('bare','MIBVblind','action'),
      'C V2 (bare+MIBV, drop action)':('bare','MIBVblind')}
def nindep(V,ch,r): return sum(1 for k in ch if V[k][r]>=3)
def spectrum(V,ch):
    n={r:nindep(V,ch,r) for r in POS}; m=len(ch)
    red=sum(1 for r in POS if n[r]>=max(3,m) or (m<3 and n[r]==m))
    # for m>=3 redundant := >=3; for m==2 redundant := ==2
    red=sum(1 for r in POS if (n[r]>=3 if m>=3 else n[r]==m))
    sil=sum(1 for r in POS if n[r]==0); fra=len(POS)-red-sil
    return red,fra,sil,n
print('\n[spectrum: redundant / fragile / silent  (% of 180)]')
for name,ch in SETS.items():
    rd,fr,sl,_=spectrum(D,ch); rq,fq,sq,_=spectrum(Q,ch)
    print(f'  {name:34s} DS {rd:3d}/{fr:3d}/{sl:2d} = {100*rd/180:.1f}/{100*fr/180:.1f}/{100*sl/180:.1f}'
          f'   | QW {rq:3d}/{fq:3d}/{sq:2d} = {100*rq/180:.1f}/{100*fq/180:.1f}/{100*sq/180:.1f}')

# ===== 3. inferential headline: merged not-redundantly-checkable (range + Wilson) =====
print('\n[merged not-redundantly-checkable = fragile+silent  (range across sets x backbone, Wilson95)]')
vals=[]
for name,ch in SETS.items():
    for tag,V in (('DS',D),('QW',Q)):
        rd,fr,sl,_=spectrum(V,ch); nr=fr+sl; lo,hi=wilson(nr,180); vals.append(nr/180)
        print(f'  {tag} {name:34s} not-redund={nr}/180={100*nr/180:.1f}%  Wilson95[{100*lo:.1f},{100*hi:.1f}]')
print(f'  => RANGE across all defensible cuts: {100*min(vals):.1f}% – {100*max(vals):.1f}%')

# ===== 4. held-out confidence axis (NOT a same-vector identity) =====
print('\n[held-out H1: nindep(setC) vs confidence from EXCLUDED channels]')
chC=SETS['C V2 (bare+MIBV, drop action)']
nC=[nindep(D,chC,r) for r in POS]
# held-out mass = conservative + MIBVaware vote counts (neither in set C)
heldmass=[D['conservative'][r]+D['MIBVaware'][r] for r in POS]   # higher = more alarm (lower confident-pass)
nonalarm_heldmass=[(5-min(D['conservative'][r],5))+(5-min(D['MIBVaware'][r],5)) for r in POS]
within_mass=[(5-min(D['bare'][r],5))+(5-min(D['MIBVblind'][r],5)) for r in POS]  # same-vector (circular)
print(f'  CIRCULAR (within-set nonalarm mass vs nindep): rho={spearman(nC,within_mass):+.3f}  <- identity, do NOT report as evidence')
print(f'  HELD-OUT (conservative+MIBVaware nonalarm mass vs nindep): rho={spearman(nC,nonalarm_heldmass):+.3f}  <- falsifiable H1')
# vision held-out (adverse/underpowered) — load vision
visA=load(LEG/'experiments/rq2_2_modern_baselines/outputs/aer_vision_qwenvl_run1.jsonl')
visB=load(LEG/'experiments/rq2_2_modern_baselines/outputs/aer_vision_qwen3vl235b_run1.jsonl')
def vtruthy(x): return x not in (None,'',False,0,'false','False','NO','no','None')
vis_nonalarm=[2-(1 if vtruthy(visA.get(r,{}).get('aer_alarm')) else 0)-(1 if vtruthy(visB.get(r,{}).get('aer_alarm')) else 0) for r in POS]
print(f'  HELD-OUT vision (adverse): rho={spearman(nC,vis_nonalarm):+.3f}')

# ===== 5. silent at 3 thresholds (set C) + cross-model intersection core =====
print('\n[silent count at 1/3/5-of-5 thresholds, set C, per family]')
def silent_at(V,ch,thr):
    return {r for r in POS if all(V[k][r]<thr for k in ch)}
for thr in (1,3,5):
    s=silent_at(D,chC,thr); fc=collections.Counter(fam(r) for r in s)
    print(f'  thr={thr}-of-5: silent={len(s):2d}  family={dict(fc)}')
sd=silent_at(D,chC,3); sq=silent_at(Q,chC,3)
core=sorted(sd & sq)
print(f'\n[cross-model intersection silent core (set C, 3-of-5)] DS silent={len(sd)} QW silent={len(sq)} INTERSECTION={len(core)}')
for r in core: print(f'    {fam(r):8s} {r.split("__")[0]}')
print('\nDONE rq1 (V2).')
