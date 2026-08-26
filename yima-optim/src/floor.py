"""M3结构下限: 同对二根字碰撞; M1覆盖: 官方前缀拥塞分解."""
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

top = [c for c, _ in freq[:6000] if c in splits]

# 1. 同对二根字统计
pair2 = defaultdict(list)   # (R1,R2) -> [二根字]
for ch in top:
    roots = splits[ch]['roots']
    if len(roots) == 2:
        pair2[(roots[0], roots[1])].append(ch)
multi = {p: v for p, v in pair2.items() if len(v) > 1}
floor6000 = sum(len(v) - 1 for v in multi.values())
print(f"前6000: 二根字 {sum(len(v) for v in pair2.values())}, 同对多字组 {len(multi)}, 结构碰撞(每对留1字+1字取二码) {floor6000}")
# 分区间
f1500 = sum(1 for p, v in multi.items() for c in v[1:] if rank[c] < 1500)
f3000 = sum(1 for p, v in multi.items() for c in v[1:] if 1500 <= rank[c] < 3000)
print(f"  其中: 前1500多余字 {f1500}, 1501-3000多余字 {f3000}, 3001-6000多余字 {floor6000-f1500-f3000}")
big_multi = sorted(multi.items(), key=lambda x: -len(x[1]))[:15]
print("  最大同对组:", [(f"{'|'.join(p)}", v) for p, v in big_multi])

# 2. 官方全码碰撞分解: 用官方码统计 top6000 全码组
code_chars = defaultdict(list)
for ch in top:
    oc = [x for x in cm42.get(ch, []) if len(x) == 3]
    if oc:
        code_chars[oc[0]].append(ch)
two_chars = {c: [x for x in cs if len(x) == 2][0] for c, cs in cm42.items() if any(len(x) == 2 for x in cs)}
coll = 0
for code, chars in code_chars.items():
    users = [c for c in chars if c not in two_chars or two_chars[c] != code[:2]]
    # 二码字的全码仍占用? 字劫逻辑: I[ch]=最短码. 二码字最短=2码, m[code]只含 I==code 的字
    users = [c for c in chars if two_chars.get(c) != code[:2]]
    if len(users) > 1:
        coll += len(users) - 1
print(f"\n官方码: 前6000全码组多余字(排除二码字占用) = {coll}")

# 3. 同对二根字在官方表里的处理: 抽查几个
print("\n同对二根字官方码抽查:")
for p, v in list(multi.items())[:8]:
    print(f"  {'|'.join(p)}: {[(c, [x for x in cm42.get(c,[]) if len(x)==3], two_chars.get(c)) for c in v]}")
