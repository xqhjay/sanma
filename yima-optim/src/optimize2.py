"""奕码优化器 v3: 官方拆分(100%保真) + 大码SA + 冲突感知二码指派.

精确模型 (经官方码表端到端酸测):
  码结构: kind1: 大+小+小 (前缀=大+小) | kind2: 大1+大2+小2 (前缀=大1+大2) | kind3+: 大1+大2+大末
  S = 二码字集 (每前缀≤1, 条目=该字全码前缀)
  出简重(排除全码) = 非S字中, 全码与频序更早的非S字相同者
  M1 = |S ∩ top1500|,  C1500/M2/M3 = 各频段出简重

关键性质 (已验证):
  - 二码指派零副作用: S字最短码唯一, 其全码让渡给同组字 → 纯收益
  - 结构冲突组(同签名) 25组全为 size2 → 全部可由二码化解
  - 跨签名全码冲突由大码指派消除 (SA 搜索目标)
"""
import json
import sys
import numpy as np

sys.path.insert(0, '/workspace/yima-optim/src')

BASE = '/workspace/yima-optim/data'


class Optimizer:
    def __init__(self, sigs_path=f'{BASE}/processed/sigs.json'):
        d = json.load(open(sigs_path, encoding='utf-8'))
        roots_d = d['roots']          # root -> '大小' 2字符
        self.root_chars = sorted(roots_d.keys())
        self.R = len(self.root_chars)
        self.ridx = {r: i for i, r in enumerate(self.root_chars)}
        self.small = np.array([ord(roots_d[r][1]) - 97 for r in self.root_chars], dtype=np.int32)
        self.official_big = np.array([ord(roots_d[r][0]) - 97 for r in self.root_chars], dtype=np.int32)

        chars = d['chars']
        items = [(ch, e) for ch, e in chars.items()]
        items.sort(key=lambda kv: kv[1]['rank'])
        N = len(items)
        self.N = N
        self.chars = np.array([ch for ch, _ in items], dtype=object)
        rank = np.array([e['rank'] for _, e in items], dtype=np.int32)

        i1 = np.zeros(N, dtype=np.int32)
        i2 = np.zeros(N, dtype=np.int32)   # kind2/3: 第2根; kind1: 同i1
        iL = np.zeros(N, dtype=np.int32)   # kind3: 末根; kind1/2: 同i2 (仅当 third_is_root=False 用 small)
        kind = np.zeros(N, dtype=np.int8)
        for j, (_, e) in enumerate(items):
            rs = [self.ridx[r] for r in e['roots']]
            n = len(rs)
            if n == 1:
                kind[j] = 1
                i1[j] = i2[j] = iL[j] = rs[0]
            elif n == 2:
                kind[j] = 2
                i1[j], i2[j], iL[j] = rs[0], rs[1], rs[1]
            else:
                kind[j] = 3
                i1[j], i2[j], iL[j] = rs[0], rs[1], rs[-1]
        self.kind, self.i1, self.i2, self.iL = kind, i1, i2, iL

        # 频段掩码
        self.m1500 = rank < 1500
        self.m3000 = rank < 3000
        self.m6000 = rank < 6000
        self.rank = rank

    def band_w(self, w15=1e6, w23=200.0, w36=20.0):
        """频段权重数组: 出简重代价 (前1500为硬约束级, 6000外不计)."""
        r = self.rank
        return np.where(r < 1500, w15, np.where(r < 3000, w23, np.where(r < 6000, w36, 0.0)))

    # ---------- 编码 ----------
    def prefix_full(self, big):
        """返回 (prefix, full) 一维 int 数组."""
        l1 = big[self.i1]
        l2 = np.where(self.kind == 1, self.small[self.i1], big[self.i2])
        third = np.where(self.kind == 3, big[self.iL], self.small[self.i2])
        prefix = l1 * 26 + l2
        full = (l1 * 26 + l2) * 26 + third
        return prefix, full

    # ---------- 二码指派 + 冲突计算 ----------
    def assign_and_conflicts(self, prefix, full, w_m1=3000.0, w15=1e6, w23=200.0, w36=20.0):
        """精确加权指派与冲突. 返回 (S掩码, m1, c15, c23, c36).

        原理 (精确, 非启发式): 同全码 ⇒ 同前缀, 故各前缀的 S 选择完全独立.
        选 S=x 的全局变化 = w_m1·[rank(x)<1500] + relief(x), 其中
        relief(x) = w(x) (x 非组首) / w(组内第2位) (x 组首且组>1) / 0 (单字组).
        每前缀取 value 最大者即为该线性目标下的精确最优指派.
        """
        N = self.N
        rank, m1500 = self.rank, self.m1500
        w = self.band_w(w15, w23, w36)

        # 全码组 (频序即数组序, 因已按 rank 排序)
        order = np.argsort(full, kind='stable')
        fs = full[order]
        gstart = np.empty(N, dtype=bool)
        gstart[0] = True
        gstart[1:] = fs[1:] != fs[:-1]
        gfirst_idx = np.maximum.accumulate(np.where(gstart, np.arange(N), 0))
        pos_in_group = np.arange(N) - gfirst_idx          # 0起
        gsize = np.zeros(N, dtype=np.int32)
        np.add.at(gsize, np.cumsum(gstart) - 1, 1)
        gsize_of = gsize[np.cumsum(gstart) - 1]
        relief_sorted = np.where(pos_in_group > 0, w[order], 0.0)
        # 组首的 relief = w[组内第2位]
        first_positions = np.flatnonzero(gstart & (gsize_of > 1))
        if first_positions.size:
            relief_sorted[first_positions] = w[order[first_positions + 1]]
        relief = np.zeros(N)
        relief[order] = relief_sorted

        # 每前缀 value 最大者 (并列取频序靠前): value = w_m1·top1500 + relief
        value = np.where(m1500, w_m1, 0.0) + relief
        o = np.lexsort((-value, prefix))
        p = prefix[o]
        f = np.empty(o.size, dtype=bool)
        f[0] = True
        f[1:] = p[1:] != p[:-1]
        S = np.zeros(N, dtype=bool)
        S[o[f]] = True

        m1 = int(np.sum(S & m1500))

        # 冲突: 非S字全码组内非组首者
        kept = ~S
        ids = full[kept]
        rk = rank[kept]
        o2 = np.lexsort((rk, ids))
        ids_s, rk_s = ids[o2], rk[o2]
        nf = np.empty(ids_s.size, dtype=bool)
        nf[0] = True
        nf[1:] = ids_s[1:] != ids_s[:-1]
        firsts = np.maximum.accumulate(np.where(nf, np.arange(ids_s.size), 0))
        nonfirst = np.arange(ids_s.size) > firsts
        rkn = rk_s[nonfirst]
        c15 = int(np.sum(rkn < 1500))
        c23 = int(np.sum((rkn >= 1500) & (rkn < 3000)))
        c36 = int(np.sum(rkn < 6000))
        return S, m1, c15, c23, c36

    def score(self, big, detail=False, w_m1=3000.0, w_m2=200.0, w_m3=20.0):
        prefix, full = self.prefix_full(big)
        S, m1, c15, c23, c36 = self.assign_and_conflicts(
            prefix, full, w_m1=w_m1, w23=w_m2, w36=w_m3)
        s = (w_m1 * (676 - m1) + 1e6 * c15 + w_m2 * c23 + w_m3 * c36)
        # 大码均衡 (低权重): 各字母根数
        cnt = np.bincount(big, minlength=26)
        s += 5.0 * float(np.maximum(0, cnt - 16).sum())
        if detail:
            return s, dict(M1=m1, C1500=c15, M2=c23, M3=c36, S=S)
        return s


def sa(opt, big=None, steps=60000, t0=260.0, t1=0.4, seed=0, log_every=5000,
       w_m1=3000.0, w_m2=200.0, w_m3=20.0, init=None):
    """模拟退火: 冲突驱动移动(择优字母) + 随机移动 + 换位."""
    rng = np.random.default_rng(seed)
    big = (opt.official_big.copy() if big is None else big.copy())
    if init is not None:
        big = init.copy()
    kw = dict(w_m1=w_m1, w_m2=w_m2, w_m3=w_m3)
    cur = opt.score(big, **kw)
    best, best_big = cur, big.copy()
    R = opt.R
    conflict_roots = None
    refresh_at = 0
    for step in range(steps):
        T = t0 * (t1 / t0) ** (step / steps)
        u = rng.random()
        if u < 0.55:
            # 冲突驱动: 冲突根 → 采样3字母取最优
            if conflict_roots is None or step >= refresh_at:
                conf = get_conflict_chars(opt, big, **kw)
                if conf.size:
                    roots_pool = np.concatenate([
                        opt.i1[conf], opt.i2[conf], opt.iL[conf]])
                    conflict_roots = np.unique(roots_pool)
                else:
                    conflict_roots = np.arange(R)
                refresh_at = step + 300
            r = conflict_roots[rng.integers(len(conflict_roots))]
            old = big[r]
            cands = [int(x) for x in rng.integers(0, 26, 3) if x != old]
            if not cands:
                continue
            best_s, best_new = None, None
            for new in cands:
                big[r] = new
                s = opt.score(big, **kw)
                if best_s is None or s < best_s:
                    best_s, best_new = s, new
            big[r] = best_new
            s = best_s
            if s <= cur or rng.random() < np.exp((cur - s) / T):
                cur = s
                if s < best:
                    best, best_big = s, big.copy()
            else:
                big[r] = old
        elif u < 0.75:
            r = rng.integers(R)
            old = big[r]
            new = rng.integers(26)
            if new == old:
                continue
            big[r] = new
            s = opt.score(big, **kw)
            if s <= cur or rng.random() < np.exp((cur - s) / T):
                cur = s
                if s < best:
                    best, best_big = s, big.copy()
            else:
                big[r] = old
        else:
            # 换位: 冲突根 与 随机根
            if conflict_roots is not None and conflict_roots.size and rng.random() < 0.7:
                r1 = conflict_roots[rng.integers(len(conflict_roots))]
            else:
                r1 = rng.integers(R)
            r2 = rng.integers(R)
            if r1 == r2 or big[r1] == big[r2]:
                continue
            big[r1], big[r2] = big[r2], big[r1]
            s = opt.score(big, **kw)
            if s <= cur or rng.random() < np.exp((cur - s) / T):
                cur = s
                if s < best:
                    best, best_big = s, big.copy()
            else:
                big[r1], big[r2] = big[r2], big[r1]
        if log_every and step % log_every == 0:
            _, d = opt.score(big, detail=True, **kw)
            print(f'  step {step:>6} T={T:6.1f} cur={cur:.0f} best={best:.0f} '
                  f'M1={d["M1"]} C15={d["C1500"]} M2={d["M2"]} M3={d["M3"]}', flush=True)
    return best, best_big


def get_conflict_chars(opt, big, w_m1=3000.0, w_m2=200.0, w_m3=20.0):
    """返回冲突字索引 (非S, 全码组内非首), 按频序."""
    prefix, full = opt.prefix_full(big)
    S, *_ = opt.assign_and_conflicts(
        prefix, full, w_m1=w_m1, w23=w_m2, w36=w_m3)
    kept = ~S
    ids = full[kept]
    rk = opt.rank[kept]
    o2 = np.lexsort((rk, ids))
    ids_s = ids[o2]
    nf = np.empty(ids_s.size, dtype=bool)
    nf[0] = True
    nf[1:] = ids_s[1:] != ids_s[:-1]
    firsts = np.maximum.accumulate(np.where(nf, np.arange(ids_s.size), 0))
    nonfirst = np.flatnonzero(np.arange(ids_s.size) > firsts)
    conf = o2[nonfirst]
    conf = np.flatnonzero(kept)[conf]
    return conf[np.argsort(opt.rank[conf])]


def polish(opt, big, rounds=8, log=True, swaps=True,
           w_m1=3000.0, w_m2=200.0, w_m3=20.0):
    """精修: 单根穷举字母 + 根换位."""
    kw = dict(w_m1=w_m1, w_m2=w_m2, w_m3=w_m3)
    big = big.copy()
    best = opt.score(big, **kw)
    for rd in range(rounds):
        conf = get_conflict_chars(opt, big, **kw)
        if conf.size == 0:
            break
        improved = 0
        for ci in conf:
            roots = [int(opt.iL[ci]), int(opt.i2[ci]), int(opt.i1[ci])]
            if opt.kind[ci] <= 2:
                roots = [int(opt.i2[ci]), int(opt.i1[ci]), int(opt.i2[ci])]
            done = False
            for r in dict.fromkeys(roots):
                old = big[r]
                for letter in range(26):
                    if letter == old:
                        continue
                    big[r] = letter
                    s = opt.score(big, **kw)
                    if s < best:
                        best = s
                        improved += 1
                        done = True
                        break
                    big[r] = old
                if done:
                    break
                big[r] = old
            # 换位: r 与同字母其他根交换 (保持字母多重集, 常保 M1)
            if swaps and not done:
                for r in dict.fromkeys(roots):
                    same = np.flatnonzero(big == big[r])
                    for r2 in same:
                        if r2 == r:
                            continue
                        big[r], big[r2] = big[r2], big[r]
                        s = opt.score(big, **kw)
                        if s < best:
                            best = s
                            improved += 1
                            done = True
                            break
                        big[r], big[r2] = big[r2], big[r]
                    if done:
                        break
        if log:
            _, d = opt.score(big, detail=True, **kw)
            print(f'  polish round {rd}: 冲突{conf.size} 改善{improved} '
                  f'score={best:.0f} M1={d["M1"]} C15={d["C1500"]} M2={d["M2"]} M3={d["M3"]}', flush=True)
        if improved == 0:
            break
    return best, big


def main():
    import time
    import sys as _sys
    mode = _sys.argv[1] if len(_sys.argv) > 1 else 'sa'
    opt = Optimizer()
    print(f'字数 {opt.N}, 根数 {opt.R}')

    s, d = opt.score(opt.official_big, detail=True)
    print(f'官方大码+智能指派: M1={d["M1"]}, C1500={d["C1500"]}, M2={d["M2"]}, M3={d["M3"]}, score={s:.0f}')

    t0 = time.time()
    if mode == 'polish':
        big = np.load(f'{BASE}/processed/big_sa.npy')
        best, best_big = polish(opt, big)
    else:
        steps = int(mode) if mode.isdigit() else 60000
        best, best_big = sa(opt, steps=steps // 2, t0=200.0, t1=2.0, seed=1, log_every=10000)
        print(f'阶段1完成 ({time.time()-t0:.0f}s), best={best:.0f}')
        best, best_big = sa(opt, big=best_big, steps=steps // 2, t0=8.0, t1=0.15, seed=2, log_every=10000)
        print(f'阶段2完成 ({time.time()-t0:.0f}s), best={best:.0f}')
        # 精修
        best, best_big = polish(opt, best_big)
    print(f'完成 ({time.time()-t0:.0f}s)')
    _, d = opt.score(best_big, detail=True)
    print(f'最终: M1={d["M1"]}, C1500={d["C1500"]}, M2={d["M2"]}, M3={d["M3"]}, score={best:.0f}')
    np.save(f'{BASE}/processed/big_sa.npy', best_big)


if __name__ == '__main__':
    main()
