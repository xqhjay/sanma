"""官方小码音托规律分析: 根拼音 -> 小码 映射合规率."""
import sys, json
sys.path.insert(0, '/workspace/yima-optim/src')
import yaml
from pypinyin import pinyin, Style
from collections import defaultdict

BASE = '/workspace/yima-optim/data'
data = yaml.safe_load(open(f'{BASE}/sanma/奕码_小泥巴_1.2.yaml', encoding='utf-8'))
m = data['form']['mapping']
main_roots = {k: v for k, v in m.items() if isinstance(v, str) and len(v) == 2 and len(k) == 1}

def py(ch):
    r = pinyin(ch, style=Style.NORMAL, heteronym=False)
    return r[0][0] if r and r[0] else ''

def initial(s):
    for pre in ('zh', 'ch', 'sh'):
        if s.startswith(pre):
            return pre
    return s[0] if s else ''

# 每个根: 大码, 小码, 拼音, 声母, 韵母首字母
rows = []
for r, c in main_roots.items():
    p = py(r)
    rows.append({'root': r, 'big': c[0], 'small': c[1], 'py': p, 'ini': initial(p)})

# 规则检验: 小码 == 声母首字母?
n_ini = sum(1 for x in rows if x['py'] and x['small'] == x['ini'][0])
# 小码 == 韵母首字母
n_fin = sum(1 for x in rows if x['py'] and x['small'] == (x['py'][len(x['ini']):] or ' ')[0])
# 小码 == 拼音任一字母
n_any = sum(1 for x in rows if x['py'] and x['small'] in x['py'])
n_py = sum(1 for x in rows if x['py'])
print(f"可注音根: {n_py}/{len(rows)}")
print(f"小码=声母首字母: {n_ini} ({n_ini/n_py*100:.0f}%)")
print(f"小码=韵母首字母: {n_fin} ({n_fin/n_py*100:.0f}%)")
print(f"小码∈拼音字母: {n_any} ({n_any/n_py*100:.0f}%)")

# 按声母统计小码分布 (找规律)
by_ini = defaultdict(lambda: defaultdict(list))
for x in rows:
    if x['py']:
        by_ini[x['ini']][x['small']].append(x['root'])
print("\n声母 -> 小码分布 (前20声母):")
for ini in sorted(by_ini, key=lambda k: -sum(len(v) for v in by_ini[k].values()))[:20]:
    dist = {s: len(v) for s, v in sorted(by_ini[ini].items(), key=lambda kv: -len(kv[1]))}
    print(f"  {ini or '(零声母)'}: {dist}")

# 不可注音根 (PUA/部件) 列表
nopron = [x for x in rows if not x['py']]
print(f"\n不可直接注音根 {len(nopron)} 个:")
print(' '.join(f"{x['root']}{x['big']}{x['small']}" for x in nopron))
