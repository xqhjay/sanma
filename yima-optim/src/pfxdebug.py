"""深入分析差异前缀的完整结构: ts, bf, vb, dt."""
import sys
import numpy as np
sys.path.insert(0, '/workspace/yima-optim/src')
from evaluator import parse_code_table, load_freq

BASE = '/workspace/yima-optim/data'
cm, _ = parse_code_table(f'{BASE}/sanma/奕码四二顶-官方最新修正版.txt')
freq = load_freq(f'{BASE}/zijie_kc6000.txt')
rank_of = {c: i for i, (c, _) in enumerate(freq)}

for pfx in ['ts', 'bf', 'vb', 'dt', 'eq']:
    chars = []
    for ch, codes in cm.items():
        f3 = [x for x in codes if len(x) == 3]
        if f3 and f3[0][:2] == pfx:
            taker = any(len(x) == 2 for x in codes)
            chars.append((rank_of.get(ch, 99999), ch, f3[0], taker))
    chars.sort()
    print(f"\n=== 前缀 {pfx} ({len(chars)}字) ===")
    for rk, ch, code, tk in chars:
        mark = ' <二码' if tk else ''
        rng = 'T1500' if rk < 1500 else ('1501-3000' if rk < 3000 else ('3001-6000' if rk < 6000 else '6000+'))
        print(f"  #{rk:<6}{ch} {code}{mark}  {rng}")
