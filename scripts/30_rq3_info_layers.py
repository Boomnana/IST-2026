"""RQ3 载重新机制(V2 headline): carrier x information-layer crossing。zero-API stdlib。
UItree-only(MIBVblind) -> +reasoning(MIBVaware proxy, 同模态) -> +vision(run1, 跨模态)。
按 success-criterion carrier 代理拆迁移:验证 reasoning 净<=0、vision 救 render/value、0 救 file-system core。
carrier 现用 task-name 关键词代理(标注:RQ2 human carrier 落地后替换)。
"""
import json, sys, collections
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
def carrier(rid):
    t=rid.split('__')[0].lower()
    if any(k in t for k in ('camera','photo','audio','record','video')): return 'file-system'
    if any(k in t for k in ('sms','email','message','send','share','call','contact')): return 'external/comms'
    if any(k in t for k in ('delete','remove','clear','duplicate')): return 'delete-vacuous'
    if any(k in t for k in ('brightness','bluetooth','wifi','rotate','setting','volume','timer','alarm','clock','toggle')): return 'value/toggle'
    if any(k in t for k in ('recipe','calendar','event','note','markor','expense','task','draw','sketch','add','create','new')): return 'render/list'
    return 'other'
v3={json.loads(l)['record_id']:json.loads(l) for l in open(XP/'data/gold/final_labels_v3.jsonl',encoding='utf-8') if l.strip()}
U=set(v3); POS={r for r in U if v3[r]['intent']=='UNHEDGED_SUCCESS' and v3[r]['outcome']=='NOT_COMPLETED'}
def mibv_v(s,c):
    if s=='UNKNOWN' or c=='UNCLEAR': return 'REVIEW'
    if s=='COMPLETED' and c=='SUCCESS': return 'PASS'
    if s=='NOT_COMPLETED' and c=='FAILURE_OR_INCOMPLETE': return 'PASS'
    return 'FLAG'
def mvotes(runs,conv): return {r:sum(1 for x in runs if x.get(r,{}).get('completion') and conv.get(r,{}).get('conveys') and mibv_v(x.get(r,{}).get('completion'),conv.get(r,{}).get('conveys'))=='FLAG') for r in U}
dsm=[load(LEG/f'experiments/rq4_1_cross_model/outputs/deepseek_mibv_run{i}.jsonl') for i in range(1,6)]
dsc=load(LEG/'experiments/rq4_1_cross_model/outputs/deepseek_claim_conveyance_v2_run1.jsonl')
awa=[load(MB/f'experiments/oracle_separation/outputs/separated_aware_deepseek_run{i}.jsonl') for i in range(1,6)]
visA=load(LEG/'experiments/rq2_2_modern_baselines/outputs/aer_vision_qwenvl_run1.jsonl')
visB=load(LEG/'experiments/rq2_2_modern_baselines/outputs/aer_vision_qwen3vl235b_run1.jsonl')
def vtruthy(x): return x not in (None,'',False,0,'false','False','NO','no','None')
blindv=mvotes(dsm,dsc); awarev=mvotes(awa,dsc)
blind={r for r in POS if blindv[r]>=3}
aware={r for r in POS if awarev[r]>=3}
vision={r for r in POS if vtruthy(visA.get(r,{}).get('aer_alarm')) or vtruthy(visB.get(r,{}).get('aer_alarm'))}

print('='*72); print('RQ3 carrier x information-layer crossing (V2 headline, deepseek)'); print('='*72)
print(f'\n[overall recall on 180 POS]')
print(f'  UItree-only (MIBVblind)        : {len(blind)}/180 = {len(blind)/180:.3f}')
lost=blind-aware; gain=aware-blind
print(f'  +reasoning  (MIBVaware proxy)   : {len(aware)}/180 = {len(aware)/180:.3f}   (gain {len(gain)} / lost {len(lost)} = NET {len(gain)-len(lost):+d})  <- same-modality, narrative poisoning')
union_bv={r for r in POS if r in blind or r in vision}
print(f'  +vision (blind OR vision, x-modal): {len(union_bv)}/180 = {len(union_bv)/180:.3f}   (vision rescues {len(vision-blind)} blind-misses)  <- cross-modality lever')
print(f'  vision-alone recall            : {len(vision)}/180 = {len(vision)/180:.3f}  (weak alone, single-run)')

print('\n[per-carrier crossing]  carrier | nPOS | blindR | +reason netΔ | vision-rescue(of blind-miss) | all-3-miss(residual)')
cats=collections.defaultdict(list)
for r in POS: cats[carrier(r)].append(r)
order=['render/list','value/toggle','delete-vacuous','file-system','external/comms','other']
for c in order:
    rs=cats.get(c,[])
    if not rs: continue
    n=len(rs)
    bR=sum(1 for r in rs if r in blind)/n
    net=sum(1 for r in rs if r in aware and r not in blind)-sum(1 for r in rs if r in blind and r not in aware)
    miss=[r for r in rs if r not in blind]
    vres=sum(1 for r in miss if r in vision)
    resid=sum(1 for r in rs if r not in blind and r not in aware and r not in vision)
    print(f'  {c:15s} | {n:3d} | {bR:.3f} | {net:+3d} | {vres:2d}/{len(miss):2d} | {resid:2d}')

print('\n[the hard core: missed by blind AND aware AND vision]')
core=sorted(r for r in POS if r not in blind and r not in aware and r not in vision)
cc=collections.Counter(carrier(r) for r in core); fc=collections.Counter(fam(r) for r in core)
print(f'  n={len(core)}  carrier={dict(cc)}  family={dict(fc)}')
for r in core: print(f'    {fam(r):8s} {carrier(r):15s} {r.split("__")[0]}')
print('\nDONE rq3 (V2).')
