"""汇总修正后各配置 Pareto 前沿: 全局前沿 + 关键候选点 (M3 已为前6000总数口径)."""
import json
import numpy as np

D = json.load(open('/workspace/yima-optim/data/processed/fronts.json'))
BASELINE = (563, 5, 324)


def filter3d(pts):
    """keep non-dominated: m1大, c23/c36小."""
    arr = np.array(sorted(set(map(tuple, pts))))
    keep = []
    for i, p in enumerate(arr):
        dominated = ((arr[:, 0] > p[0]) & (arr[:, 1] <= p[1]) & (arr[:, 2] <= p[2])).any() \
            or ((arr[:, 0] >= p[0]) & (arr[:, 1] < p[1]) & (arr[:, 2] <= p[2])).any() \
            or ((arr[:, 0] >= p[0]) & (arr[:, 1] <= p[1]) & (arr[:, 2] < p[2])).any()
        if not dominated:
            keep.append(tuple(int(x) for x in p))
    return keep


for k, v in D.items():
    pts = sorted(set(map(tuple, v)))
    m1s = [p[0] for p in pts]
    print(f'== {k}: {len(pts)} 点, M1范围 [{min(m1s)}, {max(m1s)}]')
    mx = max(m1s)
    print(f'   M1={mx} 的点(前5):', [p for p in pts if p[0] == mx][:5])
    z = [p for p in pts if p[1] == 0]
    if z:
        zm = max(p[0] for p in z)
        print(f'   M2=0 最大M1={zm}:', [p for p in z if p[0] == zm])
    b = [p for p in pts if p[0] > 563 and p[1] <= 5 and p[2] <= 324]
    if b:
        bm = max(p[0] for p in b)
        print(f'   全面≥官方(563/5/324)的最大M1={bm}:', [p for p in b if p[0] == bm])
    print()

glob = []
for v in D.values():
    glob.extend(map(tuple, v))
front = filter3d(glob + [BASELINE])
print(f'全局前沿点数: {len(front)} (含官方基线)')

better = [p for p in front if p[0] > 563 and p[1] <= 5 and p[2] < 324]
print(f'\n严格优于官方 (M1>563, M2<=5, M3<324) 的点数: {len(better)}')
better.sort(key=lambda p: -p[0])
print('M1最高的前12个:')
for p in better[:12]:
    src = [n for n, v in D.items() if p in set(map(tuple, v))]
    print(f'   M1={p[0]:>3} M2={p[1]:>2} M3={p[2]:>3}   {",".join(src)}')

print('\nM2=0 且 M3<=324 的点 (按M1降序前10):')
z = sorted([p for p in front if p[1] == 0 and p[2] <= 324], key=lambda p: -p[0])[:10]
for p in z:
    src = [n for n, v in D.items() if p in set(map(tuple, v))]
    print(f'   M1={p[0]:>3} M2={p[1]:>2} M3={p[2]:>3}   {",".join(src)}')

print('\nM1>=676 的点:')
for p in sorted([p for p in front if p[0] >= 676], key=lambda p: p[2])[:8]:
    src = [n for n, v in D.items() if p in set(map(tuple, v))]
    print(f'   M1={p[0]:>3} M2={p[1]:>2} M3={p[2]:>3}   {",".join(src)}')
