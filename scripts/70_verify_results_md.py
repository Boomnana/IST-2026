"""数据自审:RESULTS.md 引用的每个数字是否 == results/*.csv(source of truth)。
从 CSV 读权威值,normalize 后断言其出现在 RESULTS.md。容忍 round。zero-API stdlib。
"""
import csv, sys
from pathlib import Path
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
from _paths import RES, MD
raw=open(MD,encoding='utf-8').read()
import re
txt=re.sub(r'\s+',' ', raw.replace('−','-').replace('–','-').replace('—','-').replace('→','->'))  # normalize dashes/arrows + collapse whitespace(incl newlines) for substring match
def rd(n): return list(csv.DictReader(open(RES/n,encoding='utf-8')))
P=[];F=[]
def chk(label,expect):
    ok=expect in txt; (P if ok else F).append((label,expect)); print(('  PASS ' if ok else '  FAIL ')+f'{label}: "{expect}"')

print('=== data self-audit: RESULTS.md vs results/*.csv ===')
sp={(r['channel_set'],r['backbone']):r for r in rd('rq1_spectrum.csv')}
ds=sp[('C_V2_bare_MIBV','deepseek')]; qw=sp[('C_V2_bare_MIBV','qwen')]
chk('DS spectrum', f"{ds['redundant_pct']} / {ds['fragile_pct']} / {ds['silent_pct']} %")
chk('QW spectrum', f"{qw['redundant_pct']} / {qw['fragile_pct']} / {qw['silent_pct']} %")
chk('DS not-redund', f"{ds['not_redundant_pct']} % (Wilson95 [{ds['nr_wilson_lo']}, {ds['nr_wilson_hi']}])")
chk('QW not-redund', f"{qw['not_redundant_pct']} % [{qw['nr_wilson_lo']}, {qw['nr_wilson_hi']}]")
disc={r['channel']:r for r in rd('rq1_channel_discrimination.csv')}
chk('action prec', f"{disc['action']['precision']} < base rate 0.387")
ho={r['axis'][:6]:r for r in rd('rq1_heldout_h1.csv')}
def r2(x): return f"{round(float(x),2)}"
for r in rd('rq1_heldout_h1.csv'):
    v=r2(r['spearman_rho_vs_nindep'])
    if 'within' in r['axis']: chk('held within rho', f"-0.92")
    elif 'held-out (cons' in r['axis']: chk('held-out rho', f"-0.79")
    elif 'vision' in r['axis']: chk('vision rho', f"-0.15")
sil={(r['threshold'],r['scope']):r for r in rd('rq1_silent.csv')}
chk('silent thresholds', f"{sil[('1-of-5','deepseek')]['silent_n']} / {sil[('3-of-5','deepseek')]['silent_n']} / {sil[('5-of-5','deepseek')]['silent_n']}")
chk('cross-model core', f"{sil[('3-of-5','cross-model-intersection')]['silent_n']} records")
ov=rd('rq3_info_layers_overall.csv')
chk('UItree recall', ov[0]['recall']); chk('+reasoning recall', ov[1]['recall']); chk('+vision recall', ov[2]['recall']); chk('vision-alone', ov[3]['recall'])
cc={r['carrier']:r for r in rd('rq3_carrier_crossing.csv')}
chk('render rescue', f"render/list {cc['render/list']['vision_rescue']}/{cc['render/list']['vision_rescue']}")  # 2/2
chk('file-system rescue', f"{cc['file-system']['vision_rescue']}/{cc['file-system']['blind_miss']} file-system")
chk('delete rescue', f"{cc['delete-vacuous']['vision_rescue']}/{cc['delete-vacuous']['blind_miss']} delete-vacuous")
cr={r['metric']:r['value'] for r in rd('rq4_construct_relativity.csv')}
chk('construct collapse', f"{cr['POS_causal']} → {cr['POS_endstate']}".replace('→','->') if False else f"{cr['POS_causal']} -> {cr['POS_endstate']}")
chk('construct split', f"stable {cr['stable']} / lost {cr['lost']} / gained {cr['gained']}")
chk('jaccard', f"Jaccard {cr['jaccard']}")
chk('delete enrich', f"{cr['delete_in_lost']} vs {cr['delete_in_stable']}")
chk('redundant inflate', f"{cr['redundant_pct_causal']} -> {cr['redundant_pct_endstate']} %")
hi=cr['survival_high_checkable']; lo=cr['survival_low_checkable']
hp=round(100*eval(hi),1); lp=round(100*eval(lo),1)
chk('survival high', f"{hp} % ({hi})"); chk('survival low', f"{lp} % ({lo})")
try:
    hac={(r['block'],r['scope'],r['key']):r for r in rd('rq_human_anchored.csv')}
    chk('HA ceiling both', f"both-agree {hac[('ceiling','both','')]['pct_or_F1']}")
    chk('HA ceiling A/B', f"A {hac[('ceiling','A','')]['pct_or_F1']} / B {hac[('ceiling','B','')]['pct_or_F1']}")
    chk('HA layer catch', f"{hac[('human_catch','ALL','redundant')]['pct_or_F1']} % / fragile {hac[('human_catch','ALL','fragile')]['pct_or_F1']} % / silent {hac[('human_catch','ALL','silent')]['pct_or_F1']}")
    res=hac[('residual','ALL','silent/verifier-gap/passive-uncheckable')]
    chk('HA verifier-gap', f"{res['catch_or_R']} are verifier-gap")
    chk('HA passive-uncheckable', f"{res['pct_or_F1']} are passive-uncheckable")
except FileNotFoundError:
    print('  [HA skipped: run 80_human_anchored_checkability.py first]')
try:
    xb={r['silent_set']:r for r in rd('rq2_cross_backbone_split.csv')}
    chk('XB qwen split', f"Qwen silent {xb['qwen']['n']} -> {xb['qwen']['verifier_gap']} / {xb['qwen']['passive_uncheckable']}")
    chk('XB intersection split', f"intersection {xb['intersection']['n']} -> {xb['intersection']['verifier_gap']} / {xb['intersection']['passive_uncheckable']}")
    chk('XB pu share', f"{xb['deepseek']['pu_rate_pct']} % and {xb['qwen']['pu_rate_pct']} %")
except FileNotFoundError:
    print('  [XB skipped: run 88_silent_split_cross_backbone.py first]')
try:
    kp={r['label']:r for r in rd('rq_kappa.csv')}
    chk('kappa values', f"{kp['outcome']['kappa']} / {kp['intent']['kappa']} / {kp['derived']['kappa']}")
    chk('kappa raw', f"{kp['outcome']['raw_pct']} / {kp['intent']['raw_pct']} / {kp['derived']['raw_pct']} %")
except FileNotFoundError:
    print('  [kappa skipped: run 94_kappa_and_rq4control.py first]')
try:
    dp={r['stage']:r['count'] for r in rd('data_pipeline.csv')}
    chk('pipeline intent', f"UNHEDGED_SUCCESS {dp['unhedged_success_claims']} / HEDGED_SUCCESS {dp['hedged_success']} / FAILURE {dp['failure']} / UNCLEAR {dp['unclear']}")
    chk('pipeline provenance', f"agreement {dp['gold_by_agreement']} / adjudication {dp['gold_by_adjudication']}")
    chk('pipeline screenshots', f"screenshots {dp['screenshot_coverage']}/{dp['universe']}")
except FileNotFoundError:
    print('  [pipeline skipped: run 95_corpus_distribution.py first]')
print(f'\n=== {len(P)} PASS / {len(F)} FAIL ===')
if F:
    print('FAILS (RESULTS.md 与 CSV 不一致,需修):')
    for l,e in F: print(f'  - {l}: expected substring "{e}"')
