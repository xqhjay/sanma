"""big_final 精细权重扫描 + 精确前沿: 评估其可达点."""
import sys
import numpy as np

sys.path.insert(0, '/workspace/yima-optim/src')
from optimize2 import Optimizer
from exact_front import table_front

BASE = '/workspace/yima-optim/data'
opt = Optimizer()

W2W3 = [(200, 20), (300, 30), (500, 50), (1000, 100), (2000, 200),
        (5000, 500), (10000, 1000), (200, 5), (500, 20), (1000, 30),
        (2000, 60), (5000, 100), (300, 10), (150, 15), (600, 60), (100, 100)]
W1S = (list(range(5, 105, 1)) + list(range(105, 401, 5)) + [500, 700, 1000, 2000, 3000])

big = np.load(f'{BASE}/processed/big_final.npy')
prefix, full = opt.prefix_full(big)
found = {}
for w2, w3 in W2W3:
    for w1 in W1S:
        _, m1, c15, c23, c36 = opt.assign_and_conflicts(
            prefix, full, w_m1=float(w1), w23=float(w2), w36=float(w3))
        if c15 == 0:
            found.setdefault((m1, c23, c36), (w1, w2, w3))

pts = sorted(found.keys(), key=lambda p: (-p[0], p[1], p[2]))
print(f'== big_final 权重扫描: {len(pts)} 组合 ==')
ok = [p for p in pts if p[0] > 563 and p[1] <= 5 and p[2] <= 324]
for p in sorted(ok, key=lambda p: -p[0])[:10]:
    print(f'   全面≥官方: {p}  w={found[p]}')
z = sorted([p for p in pts if p[1] == 0], key=lambda p: -p[0])
for p in z[:10]:
    print(f'   M2=0:      {p}  w={found[p]}')
mx = max(p[0] for p in pts)
for p in sorted([p for p in pts if p[0] == mx], key=lambda p: (p[1], p[2]))[:3]:
    print(f'   M1最大={mx}: {p}  w={found[p]}')

# 精确前沿关键点
front = table_front(opt, big)
fp = sorted({tuple(int(x) for x in v) for v in front}, key=lambda p: -p[0])
print(f'\n== big_final 精确前沿: {len(fp)} 点 ==')
okf = [p for p in fp if p[0] > 563 and p[1] <= 5 and p[2] <= 324]
if okf:
    print('全面≥官方最优点:', max(okf, key=lambda p: (p[0], -p[1], -p[2])))
for p in fp[:12]:
    print(f'   M1={p[0]:>3} M2={p[1]:>2} M3={p[2]:>3}')
