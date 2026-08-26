"""Pareto 前沿扫描: 对各大码表在权重网格上求精确最优指派, 输出非支配点.

用法: python pareto.py [big表名...]  (默认: sa m1max balanced relief official)
"""
import os
import sys
import numpy as np

sys.path.insert(0, '/workspace/yima-optim/src')
from optimize2 import Optimizer

BASE = '/workspace/yima-optim/data'

W_GRID = []
for w2, w3 in [(200, 20), (300, 30), (500, 50), (200, 60), (100, 15), (400, 20), (1000, 100), (200, 5)]:
    for w1 in list(range(0, 61)) + list(range(65, 301, 5)) + [400, 600, 3000]:
        W_GRID.append((w1, w2, w3))


def pareto_filter(points):
    """points: set of (M1, M2, M3); 保留非支配点 (M1大/M2小/M3小 皆优)."""
    pts = sorted(points, key=lambda p: (-p[0], p[1], p[2]))
    keep = []
    for p in pts:
        dominated = False
        for q in keep:
            if q[0] >= p[0] and q[1] <= p[1] and q[2] <= p[2] and q != p:
                if q[0] > p[0] or q[1] < p[1] or q[2] < p[2]:
                    dominated = True
                    break
        if not dominated:
            keep.append(p)
    return keep


def main():
    names = sys.argv[1:] or ['sa', 'm1max', 'balanced', 'relief', 'official']
    opt = Optimizer()
    all_points = {}
    for name in names:
        path = f'{BASE}/processed/big_{name}.npy'
        if not os.path.exists(path):
            print(f'-- 跳过 {name} (不存在)')
            continue
        big = np.load(path)
        prefix, full = opt.prefix_full(big)
        points = set()
        for w1, w2, w3 in W_GRID:
            _, m1, c15, c23, c36 = opt.assign_and_conflicts(
                prefix, full, w_m1=w1, w23=w2, w36=w3)
            if c15 == 0:
                points.add((m1, c23, c36))
        all_points[name] = points
        pf = pareto_filter(points)
        print(f'\n== {name}: {len(points)} 个组合, Pareto {len(pf)} 点 ==')
        for m1, c23, c36 in sorted(pf, key=lambda p: -p[0]):
            print(f'  M1={m1:>3}  M2={c23:>3}  M3={c36:>3}')

    # 全局 Pareto (跨表)
    glob = set()
    for pts in all_points.values():
        glob |= pts
    pf = pareto_filter(glob)
    print(f'\n== 全局 Pareto 前沿 (跨所有大码表) ==')
    print(f"{'M1':>5} {'M2':>4} {'M3':>5}  达成表")
    for m1, c23, c36 in sorted(pf, key=lambda p: -p[0]):
        src = [n for n, pts in all_points.items() if (m1, c23, c36) in pts]
        print(f'{m1:>5} {c23:>4} {c36:>5}  {",".join(src)}')


if __name__ == '__main__':
    main()
