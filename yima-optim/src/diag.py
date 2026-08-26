"""诊断393个重编码不匹配的字."""
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
main_roots = {k: v for k, v in m.items() if isinstance(v, str) and len(v) == 2}
special = {}
for k, v in m.items():
    if isinstance(v, str) and len(v) == 1:
        special[k] = v + v  # 单字母笔画根: 大小同码?
# 检查 special 编码方式
print("单字母根样例:", {k: v for k, v in list(m.items()) if isinstance(v, str) and len(v) == 1})

special2 = {'6': 'wi', '冖': 'cb'}

def encode(roots):
    cs = []
    for r in roots:
        if r in main_roots:
            cs.append(main_roots[r])
        elif r in special2:
            cs.append(special2[r])
        else:
            return None
    if len(cs) == 1:
        return cs[0][0] + cs[0][1] + cs[0][1]
    if len(cs) == 2:
        return cs[0][0] + cs[1][0] + cs[1][1]
    return cs[0][0] + cs[1][0] + cs[-1][0]

mism = []
for ch in rank:
    if ch not in splits:
        continue
    roots = splits[ch]['roots']
    code = encode(roots)
    oc = [x for x in cm42.get(ch, []) if len(x) == 3]
    if not oc:
        continue
    if code != oc[0]:
        mism.append((ch, rank[ch], roots, code, oc, splits[ch].get('src')))

print(f"\n不匹配总数: {len(mism)}")
# 按 src 分类
by_src = defaultdict(int)
for ch, rk, roots, code, oc, src in mism:
    by_src[src] += 1
print("按来源:", dict(by_src))
# 按 rank 分布
r1500 = sum(1 for x in mism if x[1] < 1500)
r3000 = sum(1 for x in mism if 1500 <= x[1] < 3000)
print(f"rank分布: 前1500: {r1500}, 1501-3000: {r3000}, 3001-6000: {len(mism)-r1500-r3000}")
# 根数分布
rn = defaultdict(int)
for ch, rk, roots, code, oc, src in mism:
    rn[len(roots)] += 1
print("根数分布:", dict(sorted(rn.items())))
# 展示前30个
print("\n样例 (字 rank roots 编码 官方码 来源):")
for ch, rk, roots, code, oc, src in mism[:30]:
    print(f"  {ch} #{rk} {'|'.join(roots)} -> {code} vs {oc} [{src}]")
# 是否多码字
multi = [ch for ch, rk, roots, code, oc, src in mism if len(oc) > 1]
print(f"\n官方多三码字: {len(multi)}")
# oracle 状态: splits.json src 分布
src_all = defaultdict(int)
for ch, d in splits.items():
    src_all[d.get('src')] += 1
print("splits.json 全量 src:", dict(src_all))
