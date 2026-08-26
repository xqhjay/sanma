"""大码布局分析: 每字母根数/根列表, 供设计报告用."""
import json
import sys
import numpy as np

sys.path.insert(0, '/workspace/yima-optim/src')
from optimize2 import Optimizer

BASE = '/workspace/yima-optim/data'


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'sa'
    opt = Optimizer()
    big = np.load(f'{BASE}/processed/big_{name}.npy')
    d = json.load(open(f'{BASE}/processed/sigs.json', encoding='utf-8'))
    roots, variants = d['roots'], d['variants']
    inv = {}
    for v, m in variants.items():
        inv.setdefault(m, []).append(v)
    print(f'== 大码布局 ({name}) ==')
    cnt = np.bincount(big, minlength=26)
    for l in range(26):
        rs = [opt.root_chars[r] for r in np.flatnonzero(big == l)]
        line = ' '.join(f'{r}{roots[r]}' for r in rs)
        nvar = sum(len(inv.get(r, [])) for r in rs)
        print(f'{chr(97+l)} ({cnt[l]:>2}根+{nvar}变体): {line}')
    print(f'总根 {len(roots)}, 字母负载: min={cnt.min()} max={cnt.max()} '
          f'mean={cnt.mean():.1f}, >16超载: {int(np.maximum(0, cnt-16).sum())}')


if __name__ == '__main__':
    main()
