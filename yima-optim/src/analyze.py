"""结构核查: 四二顶/三定表结构, 根大码分布, 前缀统计."""
import sys, json
from collections import defaultdict
sys.path.insert(0, '/workspace/yima-optim/src')
from evaluator import parse_code_table, load_freq

BASE = '/workspace/yima-optim/data'

# --- 1. 四二顶表结构 ---
cm42, _ = parse_code_table(f'{BASE}/sanma/奕码四二顶-官方最新修正版.txt')
two = {c: [x for x in cs if len(x) == 2] for c, cs in cm42.items()}
two_chars = {c: v[0] for c, v in two.items() if v}
print(f"四二顶: 总字数 {len(cm42)}, 二码字 {len(two_chars)}")
# 重复前缀检查
pref2 = defaultdict(list)
for ch, code in two_chars.items():
    pref2[code].append(ch)
dups = {k: v for k, v in pref2.items() if len(v) > 1}
print(f"二码重复前缀: {dups}")
# 二码字是否有对应三码 (前缀关系)
n_prefix = n_noprefix = n_only2 = 0
for ch, code in two_chars.items():
    fulls = [x for x in cm42[ch] if len(x) == 3]
    if not fulls:
        n_only2 += 1
    elif any(f.startswith(code) for f in fulls):
        n_prefix += 1
    else:
        n_noprefix += 1
print(f"二码字: 有三码且为前缀 {n_prefix}, 有三码非前缀 {n_noprefix}, 仅二码 {n_only2}")

# --- 2. 三定表结构 ---
cm3, _ = parse_code_table(f'{BASE}/sanma/奕码三定-官方最新修正版.txt')
one = {c: cs[0] for c, cs in cm3.items() if any(len(x) == 1 for x in cs)}
print(f"\n三定: 总字数 {len(cm3)}, 一简字 {len(one)}: {' '.join(f'{c}{k}' for c, k in sorted(one.items(), key=lambda x: x[1]))}")
# 二简与四二顶二码对比
two3 = {c: [x for x in cs if len(x) == 2][0] for c, cs in cm3.items() if any(len(x) == 2 for x in cs)}
same = sum(1 for ch, k in two_chars.items() if two3.get(ch) == k)
print(f"三定二简 {len(two3)} 个, 与四二顶二码相同 {same}")

# --- 3. 根编码: 大码分布 ---
import yaml
data = yaml.safe_load(open(f'{BASE}/sanma/奕码_小泥巴_1.2.yaml', encoding='utf-8'))
m = data['form']['mapping']
main_roots = {k: v for k, v in m.items() if isinstance(v, str) and len(v) == 2}
big_cnt = defaultdict(list)
for r, c in main_roots.items():
    big_cnt[c[0]].append(r)
print(f"\n主根 {len(main_roots)} 个, 大码分布 (字母:根数):")
print(' '.join(f"{b}:{len(v)}" for b, v in sorted(big_cnt.items())))
print(f"每字母根数: min={min(len(v) for v in big_cnt.values())} max={max(len(v) for v in big_cnt.values())} 平均={len(main_roots)/len(big_cnt):.1f}")
# 小码分布
small_cnt = defaultdict(int)
for r, c in main_roots.items():
    small_cnt[c[1]] += 1
print(f"小码字母数: {len(small_cnt)}, 小码分布: {dict(sorted(small_cnt.items()))}")

# --- 4. 拆分表 + 重编码: 前缀统计 ---
splits = json.load(open(f'{BASE}/processed/splits.json'))
freq = load_freq(f'{BASE}/zijie_kc6000.txt')
rank = {c: i for i, (c, f) in enumerate(freq)}

def encode(roots):
    cs = [main_roots.get(r) for r in roots]
    if any(c is None for c in cs):
        return None
    if len(cs) == 1:
        return cs[0][0] + cs[0][1] + cs[0][1]
    if len(cs) == 2:
        return cs[0][0] + cs[1][0] + cs[1][1]
    return cs[0][0] + cs[1][0] + cs[-1][0]

# 对比官方全码
match = mism = lack = 0
full_by_char = {}
for ch in rank:
    if ch not in splits:
        lack += 1
        continue
    roots = splits[ch]['roots']
    code = encode(roots)
    oc = [x for x in cm42.get(ch, []) if len(x) == 3]
    if not oc:
        lack += 1
        continue
    if code == oc[0]:
        match += 1
    else:
        mism += 1
    full_by_char[ch] = code or oc[0]
print(f"\n重编码 vs 官方: 匹配 {match}, 不匹配 {mism}, 缺 {lack} (前6000)")

# 前缀统计 (用官方全码, 最准确)
pref_chars = defaultdict(list)
for ch in rank:
    oc = [x for x in cm42.get(ch, []) if len(x) == 3]
    if oc:
        pref_chars[oc[0][:2]].append(ch)

top1500 = set(c for c, _ in freq[:1500])
top6000 = set(c for c, _ in freq[:6000])
pref_top1500 = {p for p, chars in pref_chars.items() if any(c in top1500 for c in chars)}
print(f"\n官方码: 前6000字占前缀数 {len([p for p in pref_chars if any(c in top6000 for c in pref_chars[p])])}, 前1500字占前缀数 {len(pref_top1500)}")
empty = [a+b for a in 'abcdefghijklmnopqrstuvwxyz' for b in 'abcdefghijklmnopqrstuvwxyz' if a+b not in pref_top1500]
print(f"前1500空前缀数: {len(empty)}")
# 前1500字前缀拥塞: 多少前缀有>1个前1500字
cong = {p: [c for c in chars if c in top1500] for p, chars in pref_chars.items()}
multi = {p: v for p, v in cong.items() if len(v) > 1}
print(f"含多个前1500字的前缀: {len(multi)} 个 (共 {sum(len(v) for v in multi.values())} 字)")
# 二码字当前归属: 每前缀的官方二码字频rank
subopt = 0
for ch, code in two_chars.items():
    if code in pref_chars:
        cands = pref_chars[code]
        best = min(cands, key=lambda c: rank.get(c, 99999))
        if best != ch and rank.get(best, 99999) < rank.get(ch, 99999):
            subopt += 1
print(f"官方二码字非该前缀最高频字: {subopt} 个")
