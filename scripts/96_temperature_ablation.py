"""Q3 robustness: is the high-consensus tail a T=0 sampling artifact?

Re-runs the SAME bare dual-axis judge (method.baselines.run_baseline_judge -> identical prompt,
model deepseek-v4-flash, identical parser) as the frozen T=0 cache, but at T in {0.3, 0.7},
5 samples each, over the deployment universe (180 POS + 177 true successes = 357 unhedged-success
claims). Only temperature changes vs the cache, so any shift in the consensus distribution is a
temperature effect, not a prompt confound.

API exception (second in the paper, alongside RQ3-B): uses MATTER_LLM_API_KEY via the silra endpoint
(deepseek-v4-flash). Outputs are cached per (T, run) and the runner is resumable: re-running skips
records already written, so it never double-spends. Adverse results are reported as-is.

Usage:
  python scripts/96_temperature_ablation.py --smoke      # 2 records x 1 sample x T=0.7, prints, no spend beyond ~2 calls
  python scripts/96_temperature_ablation.py              # full: 357 x 5 x {0.3,0.7} ~= 3570 calls (resumable)
"""
import json, sys, argparse, threading, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from _paths import XP, LEG, MB, ROOT

sys.path.insert(0, str(LEG))  # vendored engine: method/ + configs/
from method.baselines.llm_judge import run_baseline_judge          # noqa: E402  (identical prompt to T=0 cache)
from method.shared.llm_client import LLMConfig                      # noqa: E402

CFG = MB / 'configs' / 'judges' / 'deepseek-silra.json'            # deepseek-v4-flash via silra (MATTER_LLM_API_KEY)
OUT = ROOT / 'experiments' / 'rq3b_temperature_ablation' / 'outputs'
OUT.mkdir(parents=True, exist_ok=True)
TEMPS = [0.3, 0.7]
N_RUNS = 5
CONC = 100   # silra oracle_generator config caps at 100; above this risks 429 -> UNSURE fallback (would bias zero-vote count)

def loadl(p):
    out = []
    for l in open(p, encoding='utf-8'):
        l = l.strip()
        if not l: continue
        r = json.loads(l)
        if isinstance(r, dict) and r.get('_header'): continue
        out.append(r)
    return out

# --- targets: deployment universe = unhedged-success claims (POS=NOT_COMPLETED, true-success=COMPLETED) ---
v3 = {r['record_id']: r for r in loadl(XP / 'data/gold/final_labels_v3.jsonl')}
ji = {r['record_id']: r for r in loadl(XP / 'data/raw_compact/judge_inputs.jsonl')}
unhedged = {r for r in v3 if v3[r]['intent'] == 'UNHEDGED_SUCCESS'}
POS = sorted(r for r in unhedged if v3[r]['outcome'] == 'NOT_COMPLETED')
TRUE = sorted(r for r in unhedged if v3[r]['outcome'] == 'COMPLETED')
TARGETS = POS + TRUE
print(f'deployment universe: {len(unhedged)} unhedged-success = {len(POS)} POS + {len(TRUE)} true-success; '
      f'judge_inputs cover {sum(1 for r in TARGETS if r in ji)}/{len(TARGETS)}')

def _done_ids(p):
    """record_ids already written; tolerant of a truncated/garbled last line from a killed run."""
    ids = set()
    if not p.exists(): return ids
    for l in p.open(encoding='utf-8'):
        l = l.strip()
        if not l: continue
        try: ids.add(json.loads(l)['record_id'])
        except Exception: continue
    return ids

def call_one(cfg, rid):
    rec = ji[rid]
    r = run_baseline_judge(cfg, task=rec.get('task', ''), claim=rec.get('final_claim', ''),
                           steps=rec.get('steps', []), n_steps=rec.get('n_steps'), compact_payload=False)
    return {'record_id': rid, 'outcome_verdict': r['outcome_verdict'],
            'claim_verdict': r['claim_verdict'], 'parse_status': r['parse_status']}

def make_cfg(temp):
    cfg = LLMConfig.from_file(CFG, 'oracle_generator')
    cfg.temperature = temp
    return cfg

def run_pass(temp, run_id):
    cfg = make_cfg(temp)
    outp = OUT / f'bare_T{temp}_run{run_id}.jsonl'
    done = _done_ids(outp)
    todo = [r for r in TARGETS if r not in done]
    if not todo:
        print(f'  T={temp} run{run_id}: complete ({len(done)}/{len(TARGETS)}) [skip]'); return
    lock = threading.Lock(); prog = {'n': 0, 'err': 0}; t0 = time.time()
    with outp.open('a', encoding='utf-8') as fh, ThreadPoolExecutor(max_workers=CONC) as ex:
        futs = {ex.submit(call_one, cfg, rid): rid for rid in todo}
        for fut in as_completed(futs):
            row = fut.result()
            with lock:
                fh.write(json.dumps(row, ensure_ascii=False) + '\n'); fh.flush()
                prog['n'] += 1
                if row['parse_status'].startswith('error') or row['parse_status'] == 'fallback':
                    prog['err'] += 1
                if prog['n'] % 50 == 0:
                    print(f'    T={temp} run{run_id}: {prog["n"]}/{len(todo)} (+{len(done)} cached, err={prog["err"]}, {time.time()-t0:.0f}s)')
    print(f'  T={temp} run{run_id}: done {prog["n"]} new, err={prog["err"]}, {time.time()-t0:.0f}s -> {outp.name}')

def smoke():
    cfg = make_cfg(0.7)
    sample = [POS[0], TRUE[0]]
    print(f'SMOKE (T=0.7, 1 sample) on {sample}:')
    for rid in sample:
        r = call_one(cfg, rid)
        gold = v3[rid]['outcome']
        print(f'  {rid[:48]:48s} gold_outcome={gold:14s} -> outcome_verdict={r["outcome_verdict"]:14s} parse={r["parse_status"]}')
    print('SMOKE ok if parse=ok above. If error:* -> key/endpoint problem; fix before full run.')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--smoke', action='store_true')
    a = ap.parse_args()
    if a.smoke:
        smoke()
    else:
        for t in TEMPS:
            for s in range(1, N_RUNS + 1):
                run_pass(t, s)
        print('FULL DONE. analyze with scripts/97_temperature_consensus.py')
