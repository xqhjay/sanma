"""用官方码直接检验指派逻辑: 是否复现 0/5/319."""
import sys
import numpy as np
sys.path.insert(0, '/workspace/yima-optim/src')
from evaluator import parse_code_table, load_freq

BASE = '/workspace/yima-optim/data'
cm, _ = parse_code_table(f'{BASE}/sanma/奕码四二顶-官方最新修正版.txt')
freq = load_freq(f'{BASE}/zijie_kc6000.txt')
rank_of = {c: i for i, (c, _) in enumerate(freq)}

# 全部表字: 官方全码 + 是否官方二码字
chars, full, is_taker_off = [], [], []
for ch, codes in cm.items():
    f3 = [x for x in codes if len(x) == 3]
    if not f3:
        continue
    chars.append(ch)
    full.append(f3[0])
    is_taker_off.append(any(len(x) == 2 for x in codes))
N = len(chars)
print(f"表字 {N}, 官方二码字 {sum(is_taker_off)}")

LET = 'abcdefghijklmnopqrstuvwxyz'
L = {c: i for i, c in enumerate(LET)}
prefix = np.array([L[f[0]]*26 + L[f[1]] for f in full])
fullid = np.array([L[f[0]]*676 + L[f[1]]*26 + L[f[2]] for f in full])
rank = np.array([rank_of.get(c, 99999) for c in chars])
rg = np.zeros(N, dtype=int)
rg[(rank >= 1500) & (rank < 3000)] = 1
rg[(rank >= 3000) & (rank < 6000)] = 2
rg[rank >= 6000] = 3
m1500 = rank < 1500

W = {0: 300000.0, 1: 100.0, 2: 6.0, 3: 0.5}

def collisions(taker_mask):
    kept = ~taker_mask
    ids, rk, rgs = fullid[kept], rank[kept], rg[kept]
    order = np.lexsort((rk, ids))
    ids_s, rgs_s = ids[order], rgs[order]
    nf = np.empty(ids_s.size, dtype=bool)
    nf[0] = True
    nf[1:] = ids_s[1:] != ids_s[:-1]
    cr = np.bincount(rgs_s[~nf], minlength=4)
    return cr

# 1. 官方二码字 -> 碰撞 (期望 0/5/319)
cr = collisions(np.array(is_taker_off))
print(f"官方二码字碰撞: c15={cr[0]} c23={cr[1]} c36={cr[2]} cout={cr[3]}  (期望 0/5/319/?)")

# 2. 我的精确指派
order = np.lexsort((rank, fullid))
fs, rgs = fullid[order], rg[order]
gstart = np.empty(N, dtype=bool)
gstart[0] = True
gstart[1:] = fs[1:] != fs[:-1]
pos = np.arange(N) - np.maximum.accumulate(np.where(gstart, np.arange(N), 0)) + 1
same_next = np.empty(N, dtype=bool)
same_next[:-1] = ~gstart[1:]
same_next[-1] = False
freed_rg = np.where(pos == 1,
                    np.where(same_next, np.concatenate((rgs[1:], rgs[-1:])), rgs),
                    rgs)
relief = np.array([W[r] for r in freed_rg])
alone = ~same_next & (pos == 1)
relief[alone] = 0.0
relief_full = np.zeros(N)
relief_full[order] = relief

taker = np.zeros(N, dtype=bool)
idx15 = np.flatnonzero(m1500)
o = idx15[np.lexsort((rank[idx15], -relief_full[idx15], prefix[idx15]))]
p = prefix[o]
f = np.empty(o.size, dtype=bool)
f[0] = True
f[1:] = p[1:] != p[:-1]
taker[o[f]] = True
cov = np.zeros(676, dtype=bool)
cov[p[f]] = True
rest = np.flatnonzero(~taker & ~cov[prefix])
o2 = rest[np.lexsort((rank[rest], -relief_full[rest], prefix[rest]))]
p2 = prefix[o2]
f2 = np.empty(o2.size, dtype=bool)
f2[0] = True
f2[1:] = p2[1:] != p2[:-1]
taker[o2[f2]] = True
cr2 = collisions(taker)
print(f"我的精确指派碰撞: c15={cr2[0]} c23={cr2[1]} c36={cr2[2]} cout={cr2[3]}")

# 3. 差异分析: 官方二码字 vs 我的, 逐前缀
off_t = np.array(is_taker_off)
diff_pfx = set(prefix[off_t != taker].tolist())
print(f"\n指派不同的前缀数: {len(diff_pfx)}")
# 找出我的指派比官方差的例证: 比较每个不同前缀的碰撞贡献
mine_by_pfx = {}
for i in range(N):
    mine_by_pfx.setdefault(prefix[i], []).append(i)

def pfx_cost(p, tk):
    """前缀 p 在指派 tk 下的碰撞计数(4段)."""
    idxs = [i for i in mine_by_pfx[p] if not tk[i]]
    groups = {}
    for i in idxs:
        groups.setdefault(fullid[i], []).append(i)
    c = [0, 0, 0, 0]
    for g in groups.values():
        g.sort(key=lambda i: rank[i])
        for i in g[1:]:
            c[rg[i]] += 1
    return c

worse = 0
examples = []
for p in diff_pfx:
    co = pfx_cost(p, off_t)
    cm_ = pfx_cost(p, taker)
    if sum(cm_[1:]) > sum(co[1:]) or cm_[0] > co[0]:
        worse += 1
        if len(examples) < 10:
            my_t = [chars[i] for i in mine_by_pfx[p] if taker[i]]
            of_t = [chars[i] for i in mine_by_pfx[p] if off_t[i]]
            examples.append((p, my_t, of_t, co, cm_))
print(f"我的指派更差的前缀: {worse}")
for p, mt, ot, co, cm_ in examples:
    print(f"  前缀{LET[p//26]}{LET[p%26]}: 我={mt} 官方={ot} 官方碰撞{co} 我的碰撞{cm_}")
