"""精确多目标 Pareto 前沿: 逐前缀候选结果向量做 Minkowski 和 + 支配剪枝.

各前缀 S 选择独立 (同全码⇒同前缀), 每候选产生 (M1, M2, M3) 增量向量,
逐前缀合并全部组合并剪枝 → 该大码表可达的精确 Pareto 前沿 (超越线性标量化).
C1500=0 作为硬约束在每前缀内强制 (只保留 c15=0 的候选结果).

用法: python exact_front.py [big表名...]
"""
import sys
import time
import numpy as np

sys.path.insert(0, '/workspace/yima-optim/src')
from optimize2 import Optimizer

BASE = '/workspace/yima-optim/data'


def filter_3d(arr):
    """arr: (n,3) [m1,c23,c36]; 返回非支配行 (m1大, c23/c36小).

    按 -m1 排序后逐点插入, 用 Fenwick(c23)→min(c36) 查询支配:
    v 被支配 ⇔ 存在更早(即 m1≥)的点 c23≤v.c23 且 c36≤v.c36.
    """
    if len(arr) == 0:
        return arr
    arr = np.unique(arr, axis=0)
    order = np.lexsort((arr[:, 2], arr[:, 1], -arr[:, 0]))
    arr = arr[order]
    ux = np.unique(arr[:, 1])
    xid = np.searchsorted(ux, arr[:, 1])
    size = len(ux)
    INF = float('inf')
    tree = [INF] * (size + 1)

    def upd(i, v):
        i += 1
        while i <= size:
            if v < tree[i]:
                tree[i] = v
            i += i & (-i)

    def qry(i):
        i += 1
        r = INF
        while i > 0:
            if tree[i] < r:
                r = tree[i]
            i -= i & (-i)
        return r

    out = []
    for k in range(len(arr)):
        m1, c23, c36 = int(arr[k, 0]), int(arr[k, 1]), int(arr[k, 2])
        xi = int(xid[k])
        if qry(xi) <= c36:
            continue
        upd(xi, c36)
        out.append((m1, c23, c36))
    return np.array(out, dtype=np.int64) if out else np.empty((0, 3), dtype=np.int64)


def table_front(opt, big, cap=3000, log=False):
    """返回该大码表的精确 Pareto 前沿 (n,3): [M1, M2, M3]."""
    N = opt.N
    rank = opt.rank
    prefix, full = opt.prefix_full(big)

    by_prefix = {}
    for i in range(N):
        by_prefix.setdefault(int(prefix[i]), []).append(i)

    def outcome(idxs, s_idx):
        """S=s_idx 时的 (m1, c15, c23, c36).

        c36 = 前6000出简重总数 (含 c15/c23 频段, 与 assign_and_conflicts 口径一致).
        """
        m1 = 1 if rank[s_idx] < 1500 else 0
        c15 = c23 = c36 = 0
        gm = {}
        for i in idxs:
            if i == s_idx:
                continue
            gm.setdefault(int(full[i]), []).append(i)
        for g in gm.values():
            g_sorted = sorted(g, key=lambda i: rank[i])
            for i in g_sorted[1:]:
                r = rank[i]
                if r < 6000:
                    c36 += 1
                    if r < 1500:
                        c15 += 1
                    elif r < 3000:
                        c23 += 1
        return (m1, c15, c23, c36)

    per_prefix = []
    for p, idxs in by_prefix.items():
        vecs = set()
        for x in idxs:
            m1, c15, c23, c36 = outcome(idxs, x)
            if c15 == 0:
                vecs.add((m1, c23, c36))
        assert vecs, f'前缀 {p} 无 c15=0 候选!'
        pf = filter_3d(np.array(sorted(vecs), dtype=np.int64))
        per_prefix.append(pf)

    # 固定前缀(单点)直接平移合并; 交替前缀逐个 Minkowski+过滤
    per_prefix.sort(key=lambda a: len(a))
    glob = np.array([[0, 0, 0]], dtype=np.int64)
    n_alt = 0
    for pf in per_prefix:
        if len(pf) == 1:
            glob = glob + pf[0]
            continue
        n_alt += 1
        new = (glob[:, None, :] + pf[None, :, :]).reshape(-1, 3)
        glob = filter_3d(new)
        if len(glob) > cap:
            glob = glob[np.argsort(-glob[:, 0])][:cap]
        if log:
            print(f'    交替前缀#{n_alt}: front={len(glob)}', flush=True)
    return glob


def main():
    import json
    import os
    names = sys.argv[1:] or ['m1max', 'balanced', 'relief']
    # 自动纳入已存在的大码表
    if not sys.argv[1:]:
        for extra in ['mid', 'sa']:
            p = f'{BASE}/processed/big_{extra}.npy'
            if os.path.exists(p) and extra not in names:
                names.append(extra)
    opt = Optimizer()
    all_pts = {}
    for name in names:
        t0 = time.time()
        big = np.load(f'{BASE}/processed/big_{name}.npy')
        front = table_front(opt, big)
        pts = {tuple(int(x) for x in v) for v in front}
        all_pts[name] = pts
        print(f'\n== {name}: 前沿 {len(pts)} 点 ({time.time()-t0:.0f}s) ==', flush=True)
        for m1, c23, c36 in sorted(pts, key=lambda p: -p[0])[:12]:
            print(f'  M1={m1:>3}  M2={c23:>3}  M3={c36:>3}')

    # 保存 (供后续汇总/对比)
    out = {n: sorted(v) for n, v in all_pts.items()}
    with open(f'{BASE}/processed/fronts.json', 'w', encoding='utf-8') as f:
        json.dump(out, f)
    print(f"\n已保存 {BASE}/processed/fronts.json")

    glob = set()
    for pts in all_pts.values():
        glob |= pts
    front = filter_3d(np.array(sorted(glob), dtype=np.int64))
    print(f'\n== 全局精确 Pareto 前沿 ({len(front)} 点, 官方基线 563/5/324) ==')
    for v in front:
        m1, c23, c36 = int(v[0]), int(v[1]), int(v[2])
        src = [n for n, pts in all_pts.items() if (m1, c23, c36) in pts]
        print(f'  M1={m1:>3}  M2={c23:>3}  M3={c36:>3}   {",".join(src)}')


if __name__ == '__main__':
    main()
