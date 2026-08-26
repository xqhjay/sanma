"""诊断: assign_and_conflicts(贪心value) vs 逐前缀穷举线性最优 是否一致."""
import sys
import numpy as np

sys.path.insert(0, '/workspace/yima-optim/src')
from optimize2 import Optimizer

opt = Optimizer()
big = np.load('/workspace/yima-optim/data/processed/big_m1max.npy')
prefix, full = opt.prefix_full(big)
rank = opt.rank

W_M1, W23, W36 = 3000.0, 200.0, 20.0

# 官方贪心
S, m1, c15, c23, c36 = opt.assign_and_conflicts(
    prefix, full, w_m1=W_M1, w23=W23, w36=W36)
print(f'贪心: M1={m1} C15={c15} M2={c23} M3={c36}')

# 逐前缀穷举 (outcome 模型)
by_prefix = {}
for i in range(opt.N):
    by_prefix.setdefault(int(prefix[i]), []).append(i)


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


tot = [0, 0, 0, 0]
diff_prefixes = 0
for p, idxs in by_prefix.items():
    best = None
    for x in idxs:
        m1_, c15_, c23_, c36_ = outcome(idxs, x)
        if c15_ > 0:
            continue  # 硬约束
        cost = -W_M1 * m1_ + W23 * c23_ + W36 * c36_
        if best is None or cost < best[0]:
            best = (cost, m1_, c23_, c36_, x)
    tot[0] += best[1]
    tot[1] += best[2]
    tot[2] += best[3]
    # 贪心选了谁?
    gx = [i for i in idxs if S[i]]
    if gx and gx[0] != best[4]:
        diff_prefixes += 1
        if diff_prefixes <= 5:
            print(f'  前缀{p}: 贪心={opt.chars[gx[0]]}(rank{rank[gx[0]]}) '
                  f'穷举={opt.chars[best[4]]}(rank{rank[best[4]]}) '
                  f'outcome贪心={outcome(idxs, gx[0])} outcome穷举={outcome(idxs, best[4])}')
print(f'穷举(c15=0硬约束): M1={tot[0]} M2={tot[1]} M3={tot[2]}  前缀选择不同数={diff_prefixes}')
