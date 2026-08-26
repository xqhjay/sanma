"""找出 assign_and_conflicts 与 outcome 模型冲突计数的差异字."""
import sys
import numpy as np

sys.path.insert(0, '/workspace/yima-optim/src')
from optimize2 import Optimizer

opt = Optimizer()
big = np.load('/workspace/yima-optim/data/processed/big_m1max.npy')
prefix, full = opt.prefix_full(big)
rank = opt.rank

S, m1, c15, c23, c36 = opt.assign_and_conflicts(
    prefix, full, w_m1=3000.0, w23=200.0, w36=20.0)
print(f'assign: M1={m1} C15={c15} M2={c23} M3={c36}')

# assign 的冲突集
kept = ~S
ids = full[kept]
rk = rank[kept]
o2 = np.lexsort((rk, ids))
ids_s, rk_s = ids[o2], rk[o2]
kk = np.flatnonzero(kept)[o2]
nf = np.empty(ids_s.size, dtype=bool)
nf[0] = True
nf[1:] = ids_s[1:] != ids_s[:-1]
firsts = np.maximum.accumulate(np.where(nf, np.arange(ids_s.size), 0))
nonfirst = np.arange(ids_s.size) > firsts
conf_assign = set()
for pos in np.flatnonzero(nonfirst):
    i = int(kk[pos])
    if rank[i] < 6000:
        conf_assign.add(i)

# outcome 模型的冲突集
by_prefix = {}
for i in range(opt.N):
    by_prefix.setdefault(int(prefix[i]), []).append(i)
conf_outcome = set()
for p, idxs in by_prefix.items():
    sx = [i for i in idxs if S[i]]
    s_idx = sx[0] if sx else None
    gm = {}
    for i in idxs:
        if i == s_idx:
            continue
        gm.setdefault(int(full[i]), []).append(i)
    for g in gm.values():
        for i in sorted(g, key=lambda i: rank[i])[1:]:
            if rank[i] < 6000:
                conf_outcome.add(i)

only_a = conf_assign - conf_outcome
only_o = conf_outcome - conf_assign
print(f'assign冲突数={len(conf_assign)} outcome冲突数={len(conf_outcome)}')
print(f'仅assign计入 ({len(only_a)}):')
for i in sorted(only_a, key=lambda i: rank[i])[:20]:
    print(f'  {opt.chars[i]} rank={rank[i]} prefix={prefix[i]} full={full[i]} S={bool(S[i])}')
print(f'仅outcome计入 ({len(only_o)}):')
for i in sorted(only_o, key=lambda i: rank[i])[:20]:
    print(f'  {opt.chars[i]} rank={rank[i]} prefix={prefix[i]} full={full[i]} S={bool(S[i])}')
