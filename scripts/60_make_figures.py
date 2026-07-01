"""从 results/rq4_construct_relativity.csv 生成 construct-relativity 图
(fig3_construct.pdf/.png；在论文中显示为 Figure 2)。matplotlib Agg, 读 CSV 保证图=表一致。
注：旧的 fig1 spectrum 与 fig2 carrier-x-info-layer 图已退役——论文改用 tab:spectrum 表、
carrier count 表，以及 TikZ evidence-boundary decomposition 主图(Figure 1, 在 paper/main.tex 内联)，
故本脚本不再生成那两张。
"""
import csv, sys
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
try: sys.stdout.reconfigure(encoding='utf-8')
except Exception: pass
from _paths import RES, FIG
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140,'savefig.bbox':'tight'})
C_RED='#4C72B0'; C_FRA='#DD8452'; C_SIL='#C44E52'; C_OK='#55A868'; C_GRAY='#9aa0a6'
def rd(n):
    with open(RES/n,encoding='utf-8') as f: return list(csv.DictReader(f))
def frac(s): a,b=s.split('/'); return int(a),int(b)
def save(fig,name):
    fig.savefig(FIG/f'{name}.pdf'); fig.savefig(FIG/f'{name}.png'); plt.close(fig); print(f'  wrote {name}.pdf/.png')

# ===== construct-relativity figure (paper Figure 2; file kept as fig3_construct.pdf) =====
cr={r['metric']:r['value'] for r in rd('rq4_construct_relativity.csv')}
fig,(a,b)=plt.subplots(1,2,figsize=(7.2,3.0),gridspec_kw={'width_ratios':[1.2,1]})
# (a) POS reshuffle + redundant share
stable=int(cr['stable']); lost=int(cr['lost']); gained=int(cr['gained'])
a.bar(0,stable,color=C_OK,label='stable'); a.bar(0,lost,bottom=stable,color=C_SIL,label='lost (causal-only)')
a.bar(1,stable,color=C_OK); a.bar(1,gained,bottom=stable,color=C_FRA,label='gained (end-state-only)')
a.text(0,stable+lost+3,f'{int(cr["POS_causal"])} POS\nred. {cr["redundant_pct_causal"]}%',ha='center',fontsize=8)
a.text(1,stable+gained+3,f'{int(cr["POS_endstate"])} POS\nred. {cr["redundant_pct_endstate"]}%',ha='center',fontsize=8)
a.text(0,stable/2,f'{stable}',ha='center',va='center',color='w',fontsize=8)
a.text(0,stable+lost/2,f'{lost}',ha='center',va='center',color='w',fontsize=8)
a.text(1,stable+gained/2,f'{gained}',ha='center',va='center',color='w',fontsize=8)
a.set_xticks([0,1]); a.set_xticklabels(['causal\ngold','end-state\ngold'],fontsize=8)
a.set_ylabel('positive class size'); a.set_ylim(0,205)
a.legend(fontsize=7,frameon=False,loc='upper right')
a.set_title('(a) Swapping gold reshuffles >50% of POS',fontsize=9,loc='left')
# (b) survival by checkability
sh=frac(cr['survival_high_checkable']); sl=frac(cr['survival_low_checkable'])
vals=[sh[0]/sh[1]*100,sl[0]/sl[1]*100]
b.bar([0,1],vals,color=[C_OK,C_SIL],width=0.6)
for i,(v,fr) in enumerate(zip(vals,[sh,sl])): b.text(i,v+1.5,f'{v:.1f}%\n({fr[0]}/{fr[1]})',ha='center',fontsize=8)
b.set_xticks([0,1]); b.set_xticklabels(['high-checkable\n(nindep=2)','low-checkable\n(nindep<2)'],fontsize=8)
b.set_ylabel('% surviving the gold swap'); b.set_ylim(0,75)
b.set_title('(b) Redundancy tracks construct-robustness',fontsize=9,loc='left')
fig.suptitle('Checkability is construct-relative: the end-state construct drops the hard delete-vacuous cases',fontsize=9.5,y=1.02)
save(fig,'fig3_construct')
print('DONE figures.')
