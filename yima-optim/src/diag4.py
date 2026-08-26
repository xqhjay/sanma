"""逐前缀比较: 贪心S选择的outcome向量 vs 穷举线性最优, 找出差异前缀."""
import sys
import numpy as np

sys.path.insert(0, '/workspace/yima-optim/src')
from optimize2 import Optimizer

opt = Optimizer()
big = np.load('/workspace/yima-optim/data/processed/big_m1max.npy')
prefix, full = opt.prefix_full(big)
rank = opt.rank

W_M1, W23, W36 = 3000.0, 200.0, 20.0

S, m1, c15, c23, c36 = opt.assign_and_conflicts(
    prefix, full, w_m1=W_M1, w23=W23, w36=W36)
print(f'assign: M1={m1} C15={c15} M2={c23} M3={c36}')


def outcome(idxs, s_idx):
    m1_ = 1 if rank[s_idx] < 1500 else 0
    c15_ = c23_ = c36_ = 0
    gm = {}
    for i in idxs:
        if i == s_idx:
            continue
        gm.setdefault(int(full[i]), []).append(i)
    for g in gm.values():
        for i in sorted(g, key=lambda i: rank[i])[1:]:
            r = rank[i]
            if r < 1500:
                c15_ += 1
            elif r < 3000:
                c23_ += 1
            elif r < 6000:
                c36_ += 1
    return m1_, c15_, c23_, c36_


by_prefix = {}
for i in range(opt.N):
    by_prefix.setdefault(int(prefix[i]), []).append(i)

tot_g = [0, 0, 0, 0]   # 贪心S的outcome总和
tot_e = [0, 0, 0, 0]   # 穷举最优总和
n_noS = 0
n_diff = 0
for p, idxs in by_prefix.items():
    sx = [i for i in idxs if S[i]]
    if not sx:
        n_noS += 1
        continue
    og = outcome(idxs, sx[0])
    tot_g[0] += og[0]
    tot_g[1] += og[1]
    tot_g[2] += og[2]
    tot_g[3] += og[3]
    best = None
    for x in idxs:
        ox = outcome(idxs, x)
        if ox[1] > 0:
            continue
        cost = -W_M1 * ox[0] + W23 * ox[2] + W36 * ox[3]
        if best is None or cost < best[0]:
            best = (cost, x, ox)
    tot_e[0] += best[2][0]
    tot_e[1] += best[2][1]
    tot_e[2] += best[2][2]
    tot_e[3] += best[2][3]
    if best[1] != sx[0]:
        n_diff += 1
        if n_diff <= 8:
            print(f'前缀{p}: 贪心S={opt.chars[sx[0]]}(r{rank[sx[0]]}) outcome={og} | '
                  f'穷举={opt.chars[best[1]]}(r{rank[best[1]]}) outcome={best[2]}')

print(f'贪心S outcome总和: M1={tot_g[0]} C15={tot_g[1]} M2={tot_g[2]} M3={tot_g[3]}')
print(f'穷举最优总和:     M1={tot_e[0]} C15={tot_e[1]} M2={tot_e[2]} M3={tot_e[3]}')
print(f'无S前缀数={n_noS} 选择不同前缀数={n_diff} 总前缀数={len(by_prefix)}')
