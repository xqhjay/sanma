"""验证官方二码字规则: 碰撞组优先(组内频次最高), 无碰撞组才选频次最高."""
import sys
import numpy as np
sys.path.insert(0, '/workspace/yima-optim/src')
from evaluator import parse_code_table, load_freq

BASE = '/workspace/yima-optim/data'
cm, _ = parse_code_table(f'{BASE}/sanma/奕码四二顶-官方最新修正版.txt')
freq = load_freq(f'{BASE}/zijie_kc6000.txt')
rank_of = {c: i for i, (c, _) in enumerate(freq)}

chars, full, is_taker_off = [], [], []
for ch, codes in cm.items():
    f3 = [x for x in codes if len(x) == 3]
    if not f3:
        continue
    chars.append(ch)
    full.append(f3[0])
    is_taker_off.append(any(len(x) == 2 for x in codes))
N = len(chars)
LET = 'abcdefghijklmnopqrstuvwxyz'
L = {c: i for i, c in enumerate(LET)}
prefix = np.array([L[f[0]]*26 + L[f[1]] for f in full])
fullid = np.array([L[f[0]]*676 + L[f[1]]*26 + L[f[2]] for f in full])
rank = np.array([rank_of.get(c, 99999) for c in chars])
rg = np.zeros(N, dtype=int)
rg[(rank >= 1500) & (rank < 3000)] = 1
rg[(rank >= 3000) & (rank < 6000)] = 2
rg[rank >= 6000] = 3

def collisions(taker_mask):
    kept = ~taker_mask
    ids, rk, rgs = fullid[kept], rank[kept], rg[kept]
    order = np.lexsort((rk, ids))
    ids_s, rgs_s = ids[order], rgs[order]
    nf = np.empty(ids_s.size, dtype=bool)
    nf[0] = True
    nf[1:] = ids_s[1:] != ids_s[:-1]
    return np.bincount(rgs_s[~nf], minlength=4)

# 官方规则: 每前缀, 碰撞组成员中频次最高者; 无碰撞组则全体频次最高者
_, inv, cnt = np.unique(fullid, return_inverse=True, return_counts=True)
gsize = cnt[inv]
collided = gsize >= 2
taker = np.zeros(N, dtype=bool)
# 键: (prefix, 非碰撞, rank)
o = np.lexsort((rank, ~collided, prefix))
p = prefix[o]
f = np.empty(N, dtype=bool)
f[0] = True
f[1:] = p[1:] != p[:-1]
taker[o[f]] = True
cr = collisions(taker)
print(f"官方规则复现: c15={cr[0]} c23={cr[1]} c36={cr[2]} cout={cr[3]}  (官方实际: 0/5/319/?)")
# 与官方二码字集合对比
off = np.array(is_taker_off)
same = int((taker & off).sum())
print(f"二码字重合: {same}/676")
diff = [i for i in range(N) if taker[i] != off[i]]
print("差异例:", [(chars[i], full[i], rank[i]) for i in diff[:12]])
# M1 对比
m1500 = rank < 1500
m1_rule = int(np.unique(prefix[m1500 & taker]).size)
m1_off = int(np.unique(prefix[m1500 & off]).size)
print(f"M1: 规则={m1_rule}, 官方={m1_off}")
