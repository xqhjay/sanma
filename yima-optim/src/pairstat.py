"""前缀分布理论分析: (R1,R2)对统计, 单根字前缀, M1上限估计."""
import sys, json
from collections import defaultdict
sys.path.insert(0, '/workspace/yima-optim/src')
from evaluator import parse_code_table, load_freq
import yaml

BASE = '/workspace/yima-optim/data'
cm42, _ = parse_code_table(f'{BASE}/sanma/奕码四二顶-官方最新修正版.txt')
splits = json.load(open(f'{BASE}/processed/splits.json'))
freq = load_freq(f'{BASE}/zijie_kc6000.txt')
rank = {c: i for i, (c, f) in enumerate(freq)}

data = yaml.safe_load(open(f'{BASE}/sanma/奕码_小泥巴_1.2.yaml', encoding='utf-8'))
m = data['form']['mapping']
main_roots = {k: v for k, v in m.items() if isinstance(v, str) and len(v) == 2 and len(k) == 1}
special = {'6': 'wi', '冖': 'cb'}

def root_code(r):
    return main_roots.get(r) or special.get(r)

top1500 = [c for c, _ in freq[:1500] if c in splits]
top6000 = [c for c, _ in freq[:6000] if c in splits]

# 统计: 单根字 / (R1,R2) 对
pairs1500 = defaultdict(int)
single1500 = []
r1_cnt = defaultdict(int)
for ch in top1500:
    roots = splits[ch]['roots']
    if len(roots) == 1:
        single1500.append((ch, roots[0]))
    else:
        pairs1500[(roots[0], roots[1])] += 1
        r1_cnt[roots[0]] += 1

print(f"前1500字: 单根字 {len(single1500)}, 多根字 {len(top1500)-len(single1500)}")
print(f"不同 (R1,R2) 有序对: {len(pairs1500)}")
print(f"不同首根: {len(r1_cnt)}, 前20首根: {sorted(r1_cnt.items(), key=lambda x:-x[1])[:20]}")

# M1 上限 = 不同对数 + 单根字根码数 - 可能重叠, 受限于676
# 单根字: 不同根数
singles = set(r for _, r in single1500)
print(f"单根字涉及根: {len(singles)} 个: {sorted(singles, key=lambda r: -sum(1 for c,rr in single1500 if rr==r))[:30]}")

pairs6000 = set()
for ch in top6000:
    roots = splits[ch]['roots']
    if len(roots) >= 2:
        pairs6000.add((roots[0], roots[1]))
print(f"\n前6000字不同 (R1,R2) 对: {len(pairs6000)}")

# 大码重排后, 前缀 = (big(R1), big(R2)); 单根 = 根码(big,small)
# 关键约束: 每个字母的根数 ~10 (大码乱序平衡)
# 问: 能否让前1500的1333个多根字 + 单根字 填满676前缀?
# 需要每个字母对 (a,b) 至少一个前1500字. 首根分布是瓶颈: R1集中
r1_top = sorted(r1_cnt.items(), key=lambda x: -x[1])
print(f"\n首根集中度: 前10首根覆盖 {sum(c for _,c in r1_top[:10])}/{len(top1500)-len(single1500)}")
print(f"首根数>10的根: {[(r,c) for r,c in r1_top if c>10]}")

# 每个首根的次根种类
r1_r2 = defaultdict(set)
for (r1, r2), n in pairs1500.items():
    r1_r2[r1].add(r2)
# 一个首根的big=a时, 它能覆盖的a-前缀 = big(次根集合) 的大小
print(f"\n若每根独立选big: 首根为a的行, 列覆盖 = 该首根的次根们的big集合")
