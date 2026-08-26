"""mid 表精细权重扫描: 找 M2=0 且 M3<=324 的最大 M1 及其他关键点."""
import sys
import numpy as np

sys.path.insert(0, '/workspace/yima-optim/src')
from optimize2 import Optimizer

BASE = '/workspace/yima-optim/data'
opt = Optimizer()

W2W3 = [(200, 20), (300, 30), (500, 50), (1000, 100), (2000, 200),
        (5000, 500), (10000, 1000), (200, 5), (500, 20), (1000, 30),
        (2000, 60), (5000, 100), (300, 10), (150, 15)]
W1S = (list(range(5, 105, 1)) + list(range(105, 401, 5)) + [500, 700, 1000, 2000, 3000])

for name in ['mid', 'balanced']:
    big = np.load(f'{BASE}/processed/big_{name}.npy')
    prefix, full = opt.prefix_full(big)
    found = {}
    for w2, w3 in W2W3:
        for w1 in W1S:
            _, m1, c15, c23, c36 = opt.assign_and_conflicts(
                prefix, full, w_m1=float(w1), w23=float(w2), w36=float(w3))
            if c15 == 0:
                found.setdefault((m1, c23, c36), (w1, w2, w3))
    pts = sorted(found.keys(), key=lambda p: (-p[0], p[1], p[2]))
    print(f'== {name}: {len(pts)} 组合 ==')
    # 全面不劣于官方: M1>563, M2<=5, M3<=324
    ok = [p for p in pts if p[0] > 563 and p[1] <= 5 and p[2] <= 324]
    for p in sorted(ok, key=lambda p: -p[0])[:8]:
        print(f'   全面≥官方: {p}  w={found[p]}')
    # M2=0 全部点
    z = sorted([p for p in pts if p[1] == 0], key=lambda p: -p[0])
    for p in z[:8]:
        print(f'   M2=0:      {p}  w={found[p]}')
    print()
