"""RQ1 gate / channel-set sensitivity (zero-API, stdlib only).

REUSES the exact loaders + spectrum logic of 10_rq1_spectrum.py verbatim
(load / fam / votes / mvotes / mibv_v / disc / spectrum / nindep) so every
number is bit-identical to the frozen RQ1 / Table 3.

For BOTH backbones (deepseek primary, qwen replication) it sweeps the
checkability spectrum (redundant / fragile / passive-silent counts and the
not-redundant share) across:
  - channel sets: {bare}, {bare+MIBVblind}=C, {bare+MIBV+conservative}=all-adm,
    {bare+MIBV+action}=B, {unmerged outcomeNC+claimINC+MIBV}
  - gate ratio thresholds: {1.5, 2.0, 2.5, inf}  (which channels are admitted)

MANDATORY anchor self-check: set C on deepseek MUST give not-redundant 88/180
= 48.9% and passive-silent == 18 (frozen Table 3). Printed explicitly.

Writes results/rq1_gate_sensitivity.csv.
"""
import json, sys, math, collections
from pathlib import Path
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
from _paths import XP, LEG, MB, RES

# ===================== verbatim block from 10_rq1_spectrum.py =====================
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

# discrimination gate (verbatim; ratio threshold parameterized below as `gate`)
def disc(V,k,gate=2):
    A={r for r in U if V[k][r]>=3}; prec=len(A&POS)/len(A) if A else 0
    pf=len(A&POS)/len(POS); nf=len(A&NEG)/len(NEG)
    ra={f:len({r for r in A if r in POS and fam(r)==f})/90 for f in ('appagent','mav3')}
    ratio=max(ra.values())/min(ra.values()) if min(ra.values())>0 else float('inf')
    excl = prec<=BASE or pf<=nf or ratio>gate
    return prec,pf,nf,ratio,excl

def nindep(V,ch,r): return sum(1 for k in ch if V[k][r]>=3)
def spectrum(V,ch):
    n={r:nindep(V,ch,r) for r in POS}; m=len(ch)
    # for m>=3 redundant := >=3 ; for m<3 redundant := ==m  (verbatim from 10_rq1_spectrum.py)
    red=sum(1 for r in POS if (n[r]>=3 if m>=3 else n[r]==m))
    sil=sum(1 for r in POS if n[r]==0); fra=len(POS)-red-sil
    return red,fra,sil,n
# =================== end verbatim block ===================

NP=len(POS)  # 180

# ---------- MANDATORY anchor self-check (must pass) ----------
print('='*74)
print(f'RQ1 GATE / CHANNEL-SET SENSITIVITY    POS/U={NP}/{len(U)}={BASE:.3f}')
print('='*74)
chC=('bare','MIBVblind')
rdC,frC,slC,_=spectrum(D,chC)
nrC=frC+slC
print('\n[ANCHOR SELF-CHECK]  set C = {bare, MIBVblind}  backbone=deepseek')
print(f'  redundant={rdC}  fragile={frC}  passive-silent={slC}  not-redundant={nrC}/180={100*nrC/NP:.1f}%')
ok_nr = (nrC==88 and abs(100*nrC/NP-48.9)<0.05)
ok_sil = (slC==18)
print(f'  CHECK not-redundant == 88/180 == 48.9% : {"PASS" if ok_nr else "FAIL"}')
print(f'  CHECK passive-silent == 18            : {"PASS" if ok_sil else "FAIL"}')
if not (ok_nr and ok_sil):
    print('  !!! ANCHOR FAILED — loader copy is wrong, aborting.'); sys.exit(1)
print('  >>> ANCHOR PASSED (matches frozen Table 3).')

# ---------- channel sets ----------
# (display name, tuple of channels, whether all channels exist for qwen)
SETS=[
  ('bare only',                 ('bare',)),
  ('bare+MIBVblind (set C)',    ('bare','MIBVblind')),
  ('bare+MIBV+conservative',    ('bare','MIBVblind','conservative')),   # all-admissible
  ('bare+MIBV+action (set B)',  ('bare','MIBVblind','action')),
  ('unmerged outcomeNC+claimINC+MIBV', ('outcomeNC','claimINC','MIBVblind')),
]
# conservative + MIBVaware are deepseek-only; qwen lacks 'conservative'.
def has_all(V,ch): return all(k in V for k in ch)

print('\n[SPECTRUM across channel-sets x backbone]  (counts are # of the {} POS)'.format(NP))
print(f'  {"channel set":35s} {"bb":3s} {"m":>1s}  {"red":>4s} {"frag":>4s} {"sil":>4s}   not-redund%')
rows=[]  # csv rows
for name,ch in SETS:
    for tag,V in (('DS',D),('QW',Q)):
        if not has_all(V,ch):
            print(f'  {name:35s} {tag:3s} {len(ch):>1d}   --  n/a (channel absent for this backbone)')
            rows.append(dict(section='spectrum',channel_set=name,channels='+'.join(ch),backbone=tag,
                             m=len(ch),redundant='',fragile='',silent='',not_redundant='',
                             not_redundant_pct='',silent_pct=''))
            continue
        rd,fr,sl,_=spectrum(V,ch); nr=fr+sl
        print(f'  {name:35s} {tag:3s} {len(ch):>1d}  {rd:>4d} {fr:>4d} {sl:>4d}   '
              f'{100*nr/NP:5.1f}%  (red {100*rd/NP:.1f} / frag {100*fr/NP:.1f} / sil {100*sl/NP:.1f})')
        rows.append(dict(section='spectrum',channel_set=name,channels='+'.join(ch),backbone=tag,
                         m=len(ch),redundant=rd,fragile=fr,silent=sl,not_redundant=nr,
                         not_redundant_pct=round(100*nr/NP,1),silent_pct=round(100*sl/NP,1)))

# not-redundant range on deepseek (for the paragraph)
ds_nr=[r['not_redundant_pct'] for r in rows if r['section']=='spectrum' and r['backbone']=='DS' and r['not_redundant_pct']!='']
ds_sil=[r['silent'] for r in rows if r['section']=='spectrum' and r['backbone']=='DS' and r['silent']!='']
print(f'\n  deepseek not-redundant% RANGE across sets: {min(ds_nr):.1f}% - {max(ds_nr):.1f}%   (silent always >0: min sil={min(ds_sil)})')

# ---------- gate ratio thresholds: which channels are admitted ----------
GATES=[1.5,2.0,2.5,float('inf')]
ALLCH_DS=['outcomeNC','claimINC','bare','MIBVblind','action','conservative']
print('\n[GATE-RATIO THRESHOLD x admitted channels]  (deepseek; channel admitted iff prec>base AND POSflag>NEGflag AND fam-ratio<=gate)')
# pre-compute disc once with inf gate to get the per-channel prec/pf/nf/ratio (ratio is gate-independent)
discinfo={k:disc(D,k,gate=float('inf')) for k in ALLCH_DS}
print('  per-channel: ' + ' | '.join(f'{k}(ratio={discinfo[k][3]:.2f},prec={discinfo[k][0]:.3f},pf={discinfo[k][1]:.3f},nf={discinfo[k][2]:.3f})' for k in ALLCH_DS))
for g in GATES:
    admitted=[]; excluded=[]
    for k in ALLCH_DS:
        prec,pf,nf,ratio,excl=disc(D,k,gate=g)
        (excluded if excl else admitted).append(k)
    gs='inf' if g==float('inf') else f'{g:.1f}'
    print(f'  gate<= {gs:>4s} : admitted={admitted}')
    print(f'              excluded={excluded}')
    rows.append(dict(section='gate',channel_set='',channels=';'.join(admitted),backbone='DS',
                     m=g if g!=float('inf') else 'inf',redundant='',fragile='',silent='',
                     not_redundant='excluded:'+';'.join(excluded),not_redundant_pct='',silent_pct=''))

# also report which channels are *ever* excluded by gate alone (ratio>gate) vs by prec/pf rules
print('\n[why each channel is excluded — gate vs precision/flag-rate]')
for k in ALLCH_DS:
    prec,pf,nf,ratio,_=disc(D,k,gate=float('inf'))  # gate=inf so only prec/pf/nf can exclude
    fail_prec = prec<=BASE
    fail_flag = pf<=nf
    fail_gate15 = ratio>1.5
    print(f'  {k:12s} ratio={ratio:.2f}  fails(prec<=base)={fail_prec}  fails(POSflag<=NEGflag)={fail_flag}  '
          f'fails(ratio>1.5)={fail_gate15}')

# ---------- write tidy csv ----------
RES.mkdir(parents=True, exist_ok=True)
out=RES/'rq1_gate_sensitivity.csv'
cols=['section','channel_set','channels','backbone','m','redundant','fragile','silent',
      'not_redundant','not_redundant_pct','silent_pct']
with open(out,'w',encoding='utf-8',newline='') as f:
    f.write(','.join(cols)+'\n')
    for r in rows:
        f.write(','.join(str(r.get(c,'')) for c in cols)+'\n')
print(f'\n[written] {out}')
print('\nDONE rq1 gate sensitivity.')
