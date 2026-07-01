"""固化 RQ1/RQ3/RQ4 的权威 results/*.csv(复用 10/30/40 口径,V2)。zero-API stdlib。
输出: results/{rq1_channel_discrimination, rq1_spectrum, rq1_heldout_h1, rq1_silent,
rq3_info_layers_overall, rq3_carrier_crossing, rq4_construct_relativity}.csv
"""
import json, sys, math, csv, collections
from pathlib import Path
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
from _paths import XP, LEG, MB, RES
def load(p):
    d={}
    if not Path(p).exists(): return d
    for l in open(p,encoding='utf-8'):
        l=l.strip()
        if not l: continue
        r=json.loads(l)
        if r.get('_header'): continue
        d[r['record_id']]=r
    return d
def fam(r):
    q=r.split('__'); return q[1] if len(q)>1 and q[1] in ('appagent','mav3') else 'other'
def carrier(rid):
    t=rid.split('__')[0].lower()
    if any(k in t for k in ('camera','photo','audio','record','video')): return 'file-system'
    if any(k in t for k in ('sms','email','message','send','share','call','contact')): return 'external/comms'
    if any(k in t for k in ('delete','remove','clear','duplicate')): return 'delete-vacuous'
    if any(k in t for k in ('brightness','bluetooth','wifi','rotate','setting','volume','timer','alarm','clock','toggle')): return 'value/toggle'
    if any(k in t for k in ('recipe','calendar','event','note','markor','expense','task','draw','sketch','add','create','new')): return 'render/list'
    return 'other'
def wilson(k,n,z=1.96):
    if n==0: return (0,0)
    p=k/n; den=1+z*z/n; c=(p+z*z/(2*n))/den; h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den; return (c-h,c+h)
def rankdata(a):
    o=sorted(range(len(a)),key=lambda i:a[i]); rk=[0.0]*len(a); i=0
    while i<len(a):
        j=i
        while j<len(a) and a[o[j]]==a[o[i]]: j+=1
        r=(i+j-1)/2+1
        for k in range(i,j): rk[o[k]]=r
        i=j
    return rk
def pear(x,y):
    n=len(x); mx=sum(x)/n; my=sum(y)/n
    cov=sum((x[i]-mx)*(y[i]-my) for i in range(n)); sx=math.sqrt(sum((v-mx)**2 for v in x)); sy=math.sqrt(sum((v-my)**2 for v in y))
    return cov/(sx*sy) if sx*sy else 0
def spear(x,y): return pear(rankdata(x),rankdata(y))
def w(name,header,rows):
    with open(RES/name,'w',newline='',encoding='utf-8') as f:
        cw=csv.writer(f); cw.writerow(header); cw.writerows(rows)
    print(f'  wrote {name} ({len(rows)} rows)')

v3={json.loads(l)['record_id']:json.loads(l) for l in open(XP/'data/gold/final_labels_v3.jsonl',encoding='utf-8') if l.strip()}
U=set(v3); POS={r for r in U if v3[r]['intent']=='UNHEDGED_SUCCESS' and v3[r]['outcome']=='NOT_COMPLETED'}; NEG=U-POS; BASE=len(POS)/len(U)
def mibv_v(s,c):
    if s=='UNKNOWN' or c=='UNCLEAR': return 'REVIEW'
    if s=='COMPLETED' and c=='SUCCESS': return 'PASS'
    if s=='NOT_COMPLETED' and c=='FAILURE_OR_INCOMPLETE': return 'PASS'
    return 'FLAG'
def votes(runs,f,vv): return {r:sum(1 for x in runs if x.get(r,{}).get(f)==vv) for r in U}
def mvotes(runs,conv): return {r:sum(1 for x in runs if x.get(r,{}).get('completion') and conv.get(r,{}).get('conveys') and mibv_v(x.get(r,{}).get('completion'),conv.get(r,{}).get('conveys'))=='FLAG') for r in U}
# deepseek
dsb=[load(LEG/f'experiments/rq1_2_baseline_judge_failure/outputs/deepseek_baseline_run{i}.jsonl') for i in range(1,6)]
dsm=[load(LEG/f'experiments/rq4_1_cross_model/outputs/deepseek_mibv_run{i}.jsonl') for i in range(1,6)]
dsc=load(LEG/'experiments/rq4_1_cross_model/outputs/deepseek_claim_conveyance_v2_run1.jsonl')
ver=[load(XP/f'experiments/rq7_action_audit/outputs/verify_run{i}.jsonl') for i in range(1,6)]
cons=[load(XP/f'experiments/rq4_conservative_baseline/outputs/conservative_dpsk_run{i}.jsonl') for i in range(1,6)]
awa=[load(MB/f'experiments/oracle_separation/outputs/separated_aware_deepseek_run{i}.jsonl') for i in range(1,6)]
visA=load(LEG/'experiments/rq2_2_modern_baselines/outputs/aer_vision_qwenvl_run1.jsonl')
visB=load(LEG/'experiments/rq2_2_modern_baselines/outputs/aer_vision_qwen3vl235b_run1.jsonl')
D={'outcomeNC':votes(dsb,'outcome_verdict','NOT_COMPLETED'),'claimINC':votes(dsb,'claim_verdict','INCONSISTENT'),
   'MIBVblind':mvotes(dsm,dsc),'action':votes(ver,'verdict','ALARM'),'conservative':votes(cons,'outcome_verdict','NOT_COMPLETED'),'MIBVaware':mvotes(awa,dsc)}
D['bare']={r:max(D['outcomeNC'][r],D['claimINC'][r]) for r in U}
# qwen
qwb=[load(LEG/f'experiments/rq1_2_baseline_judge_failure/outputs/qwen_baseline_run{i}.jsonl') for i in range(1,6)]
qwm=[load(LEG/f'experiments/rq2_1_mibv_main/outputs/qwen_mibv_run{i}.jsonl') for i in range(1,6)]
qwc=load(LEG/'experiments/rq4_1_cross_model/outputs/qwen_claim_conveyance_v2_run1.jsonl')
Q={'outcomeNC':votes(qwb,'outcome_verdict','NOT_COMPLETED'),'claimINC':votes(qwb,'claim_verdict','INCONSISTENT'),'MIBVblind':mvotes(qwm,qwc),'action':votes(ver,'verdict','ALARM')}
Q['bare']={r:max(Q['outcomeNC'][r],Q['claimINC'][r]) for r in U}
print('writing results/*.csv ...')

# 1. discrimination
rows=[]
for k in ('outcomeNC','claimINC','bare','MIBVblind','action','conservative'):
    A={r for r in U if D[k][r]>=3}; prec=len(A&POS)/len(A) if A else 0
    pf=len(A&POS)/len(POS); nf=len(A&NEG)/len(NEG)
    ra={f:len({r for r in A if r in POS and fam(r)==f})/90 for f in ('appagent','mav3')}
    ratio=max(ra.values())/min(ra.values()) if min(ra.values())>0 else 99
    excl='EXCLUDE' if (prec<=BASE or pf<=nf or ratio>2) else 'keep'
    rows.append([k,len(A),round(prec,3),round(pf,3),round(nf,3),round(prec-BASE,3),round(ratio,2),excl])
w('rq1_channel_discrimination.csv',['channel','n_alarm','precision','POS_flag','NEG_flag','lift','fam_ratio','decision'],rows)

# 2. spectrum by set x backbone
SETS={'A_v1_4ch':('outcomeNC','claimINC','MIBVblind','action'),'B_bare_MIBV_action':('bare','MIBVblind','action'),'C_V2_bare_MIBV':('bare','MIBVblind')}
def spec(V,ch):
    m=len(ch); n={r:sum(1 for k in ch if V[k][r]>=3) for r in POS}
    red=sum(1 for r in POS if (n[r]>=3 if m>=3 else n[r]==m)); sil=sum(1 for r in POS if n[r]==0); fra=len(POS)-red-sil
    return red,fra,sil
rows=[]
for name,ch in SETS.items():
    for tag,V in (('deepseek',D),('qwen',Q)):
        rd,fr,sl=spec(V,ch); nr=fr+sl; lo,hi=wilson(nr,180)
        rows.append([name,tag,rd,fr,sl,round(100*rd/180,1),round(100*fr/180,1),round(100*sl/180,1),round(100*nr/180,1),round(100*lo,1),round(100*hi,1)])
w('rq1_spectrum.csv',['channel_set','backbone','redundant_n','fragile_n','silent_n','redundant_pct','fragile_pct','silent_pct','not_redundant_pct','nr_wilson_lo','nr_wilson_hi'],rows)

# 3. held-out H1
chC=SETS['C_V2_bare_MIBV']; nC=[sum(1 for k in chC if D[k][r]>=3) for r in POS]
circ=[(5-min(D['bare'][r],5))+(5-min(D['MIBVblind'][r],5)) for r in POS]
held=[(5-min(D['conservative'][r],5))+(5-min(D['MIBVaware'][r],5)) for r in POS]
def vt(x): return x not in (None,'',False,0,'false','False','NO','no','None')
visn=[2-(1 if vt(visA.get(r,{}).get('aer_alarm')) else 0)-(1 if vt(visB.get(r,{}).get('aer_alarm')) else 0) for r in POS]
w('rq1_heldout_h1.csv',['axis','spearman_rho_vs_nindep','status'],
  [['within-set (bare+MIBV) nonalarm mass',round(spear(nC,circ),3),'CIRCULAR identity - not evidence'],
   ['held-out (conservative+MIBVaware) nonalarm mass',round(spear(nC,held),3),'FALSIFIABLE H1'],
   ['held-out vision nonalarm',round(spear(nC,visn),3),'adverse/underpowered']])

# 4. silent thresholds + cross-model core
def silent_at(V,thr): return {r for r in POS if all(V[k][r]<thr for k in chC)}
rows=[]
for thr in (1,3,5):
    s=silent_at(D,thr); fc=collections.Counter(fam(r) for r in s); rows.append([f'{thr}-of-5','deepseek',len(s),fc['appagent'],fc['mav3']])
sd=silent_at(D,3); sq=silent_at(Q,3); core=sorted(sd&sq)
rows.append(['3-of-5','qwen',len(sq),sum(1 for r in sq if fam(r)=='appagent'),sum(1 for r in sq if fam(r)=='mav3')])
rows.append(['3-of-5','cross-model-intersection',len(core),sum(1 for r in core if fam(r)=='appagent'),sum(1 for r in core if fam(r)=='mav3')])
w('rq1_silent.csv',['threshold','scope','silent_n','appagent','mav3'],rows)
w('rq1_silent_core_records.csv',['record_id','family','carrier'],[[r,fam(r),carrier(r)] for r in sorted(core)])

# 5+6. RQ3 info layers
blindv=D['MIBVblind']; awarev=D['MIBVaware']
blind={r for r in POS if blindv[r]>=3}; aware={r for r in POS if awarev[r]>=3}
vision={r for r in POS if vt(visA.get(r,{}).get('aer_alarm')) or vt(visB.get(r,{}).get('aer_alarm'))}
unionbv={r for r in POS if r in blind or r in vision}
w('rq3_info_layers_overall.csv',['layer','recall','catch_n','net_migration_vs_blind'],
  [['UItree-only (MIBVblind)',round(len(blind)/180,3),len(blind),0],
   ['+reasoning (same-modality)',round(len(aware)/180,3),len(aware),len(aware-blind)-len(blind-aware)],
   ['+vision (cross-modality)',round(len(unionbv)/180,3),len(unionbv),len(vision-blind)],
   ['vision-alone',round(len(vision)/180,3),len(vision),'-']])
cats=collections.defaultdict(list)
for r in POS: cats[carrier(r)].append(r)
rows=[]
for c in ['render/list','value/toggle','delete-vacuous','file-system','external/comms','other']:
    rs=cats.get(c,[])
    if not rs: continue
    n=len(rs); bR=sum(1 for r in rs if r in blind)/n
    net=sum(1 for r in rs if r in aware and r not in blind)-sum(1 for r in rs if r in blind and r not in aware)
    miss=[r for r in rs if r not in blind]; vres=sum(1 for r in miss if r in vision)
    resid=sum(1 for r in rs if r not in blind and r not in aware and r not in vision)
    rows.append([c,n,round(bR,3),net,vres,len(miss),resid])
w('rq3_carrier_crossing.csv',['carrier','n_POS','blind_recall','reasoning_net_delta','vision_rescue','blind_miss','all3_residual'],rows)

# 7. construct relativity
old={}
for l in open(XP/'data/derived_gold_for_comparison/sampled_records.jsonl',encoding='utf-8'):
    l=l.strip()
    if l:
        o=json.loads(l)
        if o.get('record_id') in U: old[o['record_id']]=o
US={r for r in U if v3[r]['intent']=='UNHEDGED_SUCCESS'}
POSc={r for r in US if v3[r]['outcome']=='NOT_COMPLETED'}; POSe={r for r in US if old.get(r,{}).get('outcome_gold')=='NOT_COMPLETED'}
stable=POSc&POSe; lost=POSc-POSe; gained=POSe-POSc
def isdel(r): return carrier(r)=='delete-vacuous'
def nindepC(r,V=D): return (1 if V['bare'][r]>=3 else 0)+(1 if V['MIBVblind'][r]>=3 else 0)
hi=[r for r in POSc if nindepC(r)>=2]; lo=[r for r in POSc if nindepC(r)<2]
specc=spec(D,chC);
def spec_on(pos):
    n={r:nindepC(r) for r in pos}; red=sum(1 for r in pos if n[r]==2); sil=sum(1 for r in pos if n[r]==0); return red,len(pos)-red-sil,sil
rc=spec_on(POSc); re=spec_on(POSe)
w('rq4_construct_relativity.csv',['metric','value'],
  [['POS_causal',len(POSc)],['POS_endstate',len(POSe)],['stable',len(stable)],['lost',len(lost)],['gained',len(gained)],
   ['jaccard',round(len(stable)/len(POSc|POSe),3)],['survive_pct',round(100*len(stable)/len(POSc),1)],
   ['delete_in_lost',f'{sum(1 for r in lost if isdel(r))}/{len(lost)}'],['delete_in_stable',f'{sum(1 for r in stable if isdel(r))}/{len(stable)}'],
   ['redundant_pct_causal',round(100*rc[0]/len(POSc),1)],['redundant_pct_endstate',round(100*re[0]/len(POSe),1)],
   ['survival_high_checkable',f'{sum(1 for r in hi if r in POSe)}/{len(hi)}'],['survival_low_checkable',f'{sum(1 for r in lo if r in POSe)}/{len(lo)}']])
print('DONE results tables.')
