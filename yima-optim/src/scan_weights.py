"""权重扫描: 在各大码表上找能命中关键 Pareto 前沿点的 (w1, w2, w3) 权重.

目标: 1) 主方案: M2=0 且 M3<=324 的最大 M1 (全面不劣于官方 563/5/324)
      2) M1 极限: 最大 M1
      3) 低重码: 最小 M3
"""
import sys
import numpy as np

sys.path.insert(0, '/workspace/yima-optim/src')
from optimize2 import Optimizer

BASE = '/workspace/yima-optim/data'
OFFICIAL = (563, 5, 324)

opt = Optimizer()

# 权重网格: w1 细网格 × (w2, w3) 组合 (w2 大 → 压 M2)
W2W3 = [(200, 20), (300, 30), (500, 50), (1000, 100), (2000, 200),
        (5000, 100), (200, 60), (500, 150), (1000, 300), (2000, 500),
        (10000, 1000), (100, 10), (400, 400), (1000, 1000)]
W1S = list(range(10, 105, 5)) + list(range(105, 401, 15)) + [500, 700, 1000, 2000, 3000]


def scan(name):
    big = np.load(f'{BASE}/processed/big_{name}.npy')
    prefix, full = opt.prefix_full(big)
    found = {}
    for w2, w3 in W2W3:
        for w1 in W1S:
            _, m1, c15, c23, c36 = opt.assign_and_conflicts(
                prefix, full, w_m1=float(w1), w23=float(w2), w36=float(w3))
            if c15 == 0:
                key = (m1, c23, c36)
                if key not in found:
                    found[key] = (w1, w2, w3)
    return found


results = {}
for name in ['balanced', 'm1max', 'relief', 'mid', 'sa']:
    try:
        found = scan(name)
    except FileNotFoundError:
        print(f'-- 跳过 {name}')
        continue
    results[name] = found
    pts = sorted(found.keys(), key=lambda p: (-p[0], p[1], p[2]))

    # 目标1: 全面不劣于官方 (M1>563, M2<=5, M3<=324), 最大 M1
    ok = [p for p in pts if p[0] > 563 and p[1] <= 5 and p[2] <= 324]
    print(f'== {name}: 命中 {len(pts)} 个不同 (M1,M2,M3) 组合 ==')
    if ok:
        best = max(ok, key=lambda p: (p[0], -p[1], -p[2]))
        print(f'   全面≥官方最优: {best}  权重={found[best]}')
    # 目标2: 最大 M1
    mx = max(p[0] for p in pts)
    cands = sorted([p for p in pts if p[0] == mx], key=lambda p: (p[1], p[2]))
    print(f'   M1最大={mx}: {cands[0]}  权重={found[cands[0]]}')
    # 目标3: M2=0 最大 M1
    z = [p for p in pts if p[1] == 0]
    if z:
        zm = max(z, key=lambda p: p[0])
        print(f'   M2=0 最大M1: {zm}  权重={found[zm]}')
    # 目标4: 最小 M3
    mn = min(p[2] for p in pts)
    mm = max([p for p in pts if p[2] == mn], key=lambda p: p[0])
    print(f'   M3最小={mn}: {mm}  权重={found[mm]}')
    print()

# 全局汇总: 各目标的全局最优
print('== 全局 ==')
allpts = {}
for n, f in results.items():
    for p, w in f.items():
        allpts.setdefault(p, (n, w))
ok = [p for p in allpts if p[0] > 563 and p[1] <= 5 and p[2] <= 324]
if ok:
    best = max(ok, key=lambda p: (p[0], -p[1], -p[2]))
    n, w = allpts[best]
    print(f'全面≥官方全局最优: {best}  表={n} 权重={w}')
z = [p for p in allpts if p[1] == 0 and p[2] <= 324]
if z:
    best = max(z, key=lambda p: p[0])
    n, w = allpts[best]
    print(f'M2=0且M3<=324全局最优: {best}  表={n} 权重={w}')
mx = max(p[0] for p in allpts)
cands = sorted([p for p in allpts if p[0] == mx], key=lambda p: (p[1], p[2]))
n, w = allpts[cands[0]]
print(f'M1全局最大={mx}: {cands[0]}  表={n} 权重={w}')
mn = min(p[2] for p in allpts)
mm = max([p for p in allpts if p[2] == mn], key=lambda p: p[0])
n, w = allpts[mm]
print(f'M3全局最小={mn}: {mm}  表={n} 权重={w}')
