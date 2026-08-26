"""奕码大码重排优化器 v2: 模拟退火搜索 240 个归并码组 -> 26 字母的大码指派.

固定: 小码 (官方音托), 拆分 (splits.json), 编码规则 (大大小/大大末大).
优化: 每组大码字母.

代理口径 (与最终冲突感知指派一致的两阶段贪心):
  二码字 = 每前缀: 有前1500字 -> 前1500中(碰撞组优先,频次最高)者;
          否则 -> (碰撞组优先, 频次最高)者. 其全码腾空.
  碰撞 = 腾空后各全码组内按频序排, 第2位起者计入其频段 (与字劫"排除全码"口径一致).
"""
import sys, json, time
import numpy as np
sys.path.insert(0, '/workspace/yima-optim/src')
import yaml

BASE = '/workspace/yima-optim/data'
LET = 'abcdefghijklmnopqrstuvwxyz'


def load():
    data = yaml.safe_load(open(f'{BASE}/sanma/奕码_小泥巴_1.2.yaml', encoding='utf-8'))
    m = data['form']['mapping']
    main_roots = {k: v for k, v in m.items() if isinstance(v, str) and len(v) == 2 and len(k) == 1}
    variant_map = {}
    for k, v in m.items():
        if isinstance(v, dict) and 'element' in v and len(k) == 1:
            e = v['element']
            if isinstance(e, str) and len(e) == 1:
                variant_map[k] = e
    special = {'6': 'wi', '冖': 'cb'}

    code2gi, groups = {}, []
    all_code = dict(main_roots)
    all_code.update(special)
    for r, c in sorted(all_code.items()):
        if c not in code2gi:
            code2gi[c] = len(groups)
            groups.append(c)
    G = len(groups)
    root2gi = {r: code2gi[c] for r, c in all_code.items()}

    def gi(r):
        r2 = variant_map.get(r, r)
        g = root2gi.get(r2)
        if g is None:
            raise KeyError(f'不可编码根: {r!r}')
        return g

    splits = json.load(open(f'{BASE}/processed/splits.json'))
    freq = []
    with open(f'{BASE}/zijie_kc6000.txt', encoding='utf-8') as f:
        for line in f:
            p = line.strip().split('\t')
            if len(p) >= 2 and len(p[0]) == 1:
                try:
                    freq.append((p[0], int(p[1])))
                except ValueError:
                    pass
    freq.sort(key=lambda x: -x[1])
    rank_of = {c: i for i, (c, _) in enumerate(freq)}
    fw = {c: f for c, f in freq}

    chars = sorted(splits.keys(), key=lambda c: rank_of.get(c, 99999))
    N = len(chars)
    t = np.zeros(N, dtype=np.int8)
    g1 = np.zeros(N, dtype=np.int32)
    g2 = np.zeros(N, dtype=np.int32)
    gl = np.zeros(N, dtype=np.int32)
    g3s = np.zeros(N, dtype=np.int32)
    rank = np.zeros(N, dtype=np.int32)
    fwv = np.zeros(N, dtype=np.float64)
    for i, ch in enumerate(chars):
        roots = splits[ch]['roots']
        gi1 = gi(roots[0])
        t[i] = 0 if len(roots) == 1 else (1 if len(roots) == 2 else 2)
        g1[i] = gi1
        if len(roots) >= 2:
            g2[i] = gi(roots[1])
            gl[i] = gi(roots[-1])
            g3s[i] = gi(roots[1])
        else:
            g2[i] = gl[i] = g3s[i] = gi1
        rank[i] = rank_of.get(ch, 99999)
        fwv[i] = fw.get(ch, 0.0)

    small_g = np.array([LET.index(c[1]) for c in groups], dtype=np.int8)
    off_big = np.array([LET.index(c[0]) for c in groups], dtype=np.int8)

    # 频段: 0 前1500 / 1 1501-3000 / 2 3001-6000 / 3 6000+
    rg = np.zeros(N, dtype=np.int8)
    rg[(rank >= 1500) & (rank < 3000)] = 1
    rg[(rank >= 3000) & (rank < 6000)] = 2
    rg[rank >= 6000] = 3

    return {
        'chars': chars, 'N': N, 'G': G, 'groups': groups,
        't': t, 'g1': g1, 'g2': g2, 'gl': gl, 'g3s': g3s,
        'rank': rank, 'fw': fwv, 'small_g': small_g, 'off_big': off_big,
        'rg': rg, 'all_code': all_code, 'main_roots': main_roots,
        'special': special, 'variant_map': variant_map,
    }


class Objective:
    def __init__(self, D, w_m1=1000.0, w_m2=100.0, w_m3=6.0, w_out=0.5,
                 w_hard=300000.0, w_bal=150.0, cnt_lo=5, cnt_hi=14):
        for k in ('N', 'G', 't', 'g1', 'g2', 'gl', 'g3s', 'rank', 'fw',
                  'small_g', 'off_big', 'rg'):
            setattr(self, k, D[k])
        self.chars = D['chars']
        self.w_m1, self.w_m2, self.w_m3, self.w_out = w_m1, w_m2, w_m3, w_out
        self.w_hard, self.w_bal = w_hard, w_bal
        self.cnt_lo, self.cnt_hi = cnt_lo, cnt_hi
        self.is_single = self.t == 0
        self.is_multi = self.t == 2
        self.m1500 = self.rg == 0
        # 平衡: 前6000 频次加权, 三码位权重和=1
        bw = np.where(self.rank < 6000, self.fw, 0.0)
        self.bal_w = bw / bw.sum() * 3.0

    def codes(self, big):
        c1 = big[self.g1]
        c2 = np.where(self.is_single, self.small_g[self.g1], big[self.g2])
        c3 = np.where(self.is_multi, big[self.gl], self.small_g[self.g3s])
        return c1.astype(np.int32), c2.astype(np.int32), c3.astype(np.int32)

    def metrics(self, big):
        """返回 (M1, c15, c23, c36, cout, taker_mask, prefix, full).

        精确逐前缀指派 (向量化):
        - 各全码组按频序排, 组内第2位起为"计数者", 权重=频段权重 w(rg)
        - 腾空字 j 的收益 relief_j = 被解放计数者的权重:
          j 为组内频次最高者 -> 解放第2位; 否则解放 j 自身
        - 二码字 = 每前缀: 有前1500字 -> 前1500候选中 relief 最大者;
          否则 -> 全体候选中 relief 最大者
        """
        c1, c2, c3 = self.codes(big)
        prefix = c1 * 26 + c2
        full = prefix * 26 + c3
        N = self.N
        rank, rg = self.rank, self.rg
        # 频段权重
        w = np.array([self.w_hard, self.w_m2, self.w_m3, self.w_out])
        # 组内频序 -> 计算每字 relief
        order = np.lexsort((rank, full))
        fs, rgs = full[order], rg[order]
        gstart = np.empty(N, dtype=bool)
        gstart[0] = True
        gstart[1:] = fs[1:] != fs[:-1]
        gid = np.cumsum(gstart) - 1                       # 组号
        pos = np.arange(N) - np.maximum.accumulate(np.where(gstart, np.arange(N), 0)) + 1
        # pos: 组内频序位置 (1起)
        same_next = np.empty(N, dtype=bool)               # 组内下一个字存在
        same_next[:-1] = ~gstart[1:]
        same_next[-1] = False
        freed_rg = np.where(pos == 1,
                            np.where(same_next, np.concatenate((rgs[1:], rgs[-1:])), rgs),
                            rgs)                          # 被解放者的频段
        relief = w[freed_rg] * (pos >= 1)                 # 单字组 relief=w(自身rg)*0? 见下
        # 单字组 (无碰撞) relief 应为 0:
        alone = ~same_next & (pos == 1)
        # 组内最后一个字 pos==1 意味着组大小1
        relief[alone] = 0.0
        relief_full = np.zeros(N)
        relief_full[order] = relief
        # --- 逐前缀二码字: 两阶段 argmax relief ---
        taker = np.zeros(N, dtype=bool)
        idx15 = np.flatnonzero(self.m1500)
        o = idx15[np.lexsort((rank[idx15], -relief_full[idx15], prefix[idx15]))]
        p = prefix[o]
        f = np.empty(o.size, dtype=bool)
        f[0] = True
        f[1:] = p[1:] != p[:-1]
        taker[o[f]] = True
        cov = np.zeros(676, dtype=bool)
        cov[p[f]] = True
        rest = np.flatnonzero(~taker & ~cov[prefix])
        if rest.size:
            o2 = rest[np.lexsort((rank[rest], -relief_full[rest], prefix[rest]))]
            p2 = prefix[o2]
            f2 = np.empty(o2.size, dtype=bool)
            f2[0] = True
            f2[1:] = p2[1:] != p2[:-1]
            taker[o2[f2]] = True
        # --- 碰撞: 腾空后组内按频序, 第2位起计入频段 ---
        kept = ~taker
        ids, rk, rgs2 = full[kept], rank[kept], rg[kept]
        order2 = np.lexsort((rk, ids))
        ids_s, rgs_s = ids[order2], rgs2[order2]
        nf = np.empty(ids_s.size, dtype=bool)
        nf[0] = True
        nf[1:] = ids_s[1:] != ids_s[:-1]
        cr = np.bincount(rgs_s[~nf], minlength=4)  # [c15, c23, c36, cout]
        m1 = int(np.unique(prefix[self.m1500]).size)
        return m1, int(cr[0]), int(cr[1]), int(cr[2]), int(cr[3]), taker, prefix, full

    def score(self, big, detail=False):
        m1, c15, c23, c36, cout, taker, prefix, full = self.metrics(big)
        s = (self.w_m1 * (676 - m1) + self.w_m2 * c23 + self.w_m3 * c36
             + self.w_out * cout + self.w_hard * c15)
        cntg = np.bincount(big, minlength=26)
        s += 800.0 * (np.maximum(0, self.cnt_lo - cntg).sum()
                      + np.maximum(0, cntg - self.cnt_hi).sum())
        bal = 0.0
        if self.w_bal > 0:
            c1, c2, c3 = self.codes(big)
            for pos in (c1, c2, c3):
                u = np.bincount(pos, weights=self.bal_w, minlength=26)
                bal += float(((u - 1.0) ** 2).sum())
            s += self.w_bal * bal
        if detail:
            return s, dict(M1=m1, C1500=c15, C1501_3000=c23, C3001_6000=c36,
                           C6000p=cout, score=float(s), bal=bal)
        return s


def sa(D, iters=200000, T0=6.0, cool=0.9995, seed=42, obj=None, verbose=True,
       init=None):
    rng = np.random.default_rng(seed)
    obj = obj or Objective(D)
    G = obj.G
    big = obj.off_big.copy() if init is None else init.copy()
    cur = obj.score(big)
    best, best_s = big.copy(), cur
    T = T0
    t0 = time.time()
    for it in range(iters):
        if rng.random() < 0.55:
            g = rng.integers(G)
            nb = rng.integers(26)
            if nb == big[g]:
                continue
            cnt = np.bincount(big, minlength=26)
            if cnt[big[g]] <= obj.cnt_lo or cnt[nb] >= obj.cnt_hi:
                continue
            old = big[g]
            big[g] = nb
            s = obj.score(big)
            if s <= cur or rng.random() < np.exp((cur - s) / T):
                cur = s
            else:
                big[g] = old
        else:
            a, b = rng.integers(G, size=2)
            if a == b or big[a] == big[b]:
                continue
            big[a], big[b] = big[b], big[a]
            s = obj.score(big)
            if s <= cur or rng.random() < np.exp((cur - s) / T):
                cur = s
            else:
                big[a], big[b] = big[b], big[a]
        if cur < best_s:
            best_s, best = cur, big.copy()
        if verbose and (it + 1) % 5000 == 0:
            T *= cool ** 5000
            d = obj.score(best, detail=True)[1]
            print(f"  it={it+1} T={T:.3f} cur={cur:.0f} best={best_s:.0f} "
                  f"M1={d['M1']} C15={d['C1500']} C23={d['C1501_3000']} "
                  f"C36={d['C3001_6000']} Cout={d['C6000p']} ({time.time()-t0:.0f}s)",
                  flush=True)
    return best, best_s, obj


if __name__ == '__main__':
    D = load()
    obj = Objective(D)
    print(f"字数 {D['N']}, 码组 {D['G']}")
    d0 = obj.score(D['off_big'], detail=True)[1]
    print(f"官方大码 (代理口径, 应≈ 608/0/5/319): {d0}")
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    best, bs, obj = sa(D, iters=iters)
    print(f"\n最优 score={bs:.0f}")
    print(obj.score(best, detail=True)[1])
    out = {c: LET[b] for c, b in zip(D['groups'], best)}
    json.dump(out, open(f'{BASE}/processed/big_opt.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=0)
    print("已保存 data/processed/big_opt.json")
