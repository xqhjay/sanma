"""核查 splits.json 所有根的可编码性 (主根/变体/特殊)."""
import sys, json
from collections import defaultdict
sys.path.insert(0, '/workspace/yima-optim/src')
import yaml

BASE = '/workspace/yima-optim/data'
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

splits = json.load(open(f'{BASE}/processed/splits.json'))
roots_used = defaultdict(int)
for ch, d in splits.items():
    for r in d['roots']:
        roots_used[r] += 1

def root_code(r):
    r2 = variant_map.get(r, r)
    c = main_roots.get(r2)
    if c:
        return r2, c
    c = special.get(r2)
    if c:
        return r2, c
    return None, None

unres = {}
main_set = set()
for r, n in roots_used.items():
    tgt, c = root_code(r)
    if tgt is None:
        unres[r] = n
    else:
        main_set.add(tgt)
print(f"splits.json: {len(splits)} 字, 不同根字形 {len(roots_used)}, 归一后主根 {len(main_set)}")
print(f"不可编码根: {len(unres)}: {dict(sorted(unres.items(), key=lambda x:-x[1])[:20])}")

# 主根未被使用?
unused = [r for r in main_roots if r not in main_set]
print(f"主根未在拆分中出现: {len(unused)}: {unused[:30]}")
# special 根使用
for r in special:
    print(f"特殊根 {r!r} 使用 {sum(n for rr, n in roots_used.items() if variant_map.get(rr, rr) == r)} 次")
# 主根编码唯一性
codes = defaultdict(list)
for r, c in main_roots.items():
    codes[c].append(r)
dupc = {k: v for k, v in codes.items() if len(v) > 1}
print(f"主根编码重复: {dupc}")
# 每个大码字母的根数
bc = defaultdict(int)
for r, c in main_roots.items():
    bc[c[0]] += 1
print(f"大码字母数: {len(bc)}, 根数范围: {min(bc.values())}~{max(bc.values())}")
