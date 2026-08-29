# -*- coding: utf-8 -*-
"""奕码基础数据加载库: 从yaml提取字根编码映射、码表、频表"""
import yaml, json, re
from collections import defaultdict, Counter

YAML_PATH = '/workspace/sanma/奕码_1.2.yaml'

def load_yaml(path=YAML_PATH):
    return yaml.safe_load(open(path, encoding='utf-8'))

def resolve_code(v, mapping, depth=0):
    """把 mapping 值解析为 (大码, 小码)。支持:
    - 字符串 'xy' -> (x, y)
    - {element: X} -> X的编码(递归)
    - [a, b] 其中 a/b 可为字母或 {element: X, index: i}
    - {element: X, index: i} 单独出现在列表中
    """
    if depth > 10:
        return None
    if isinstance(v, str):
        if len(v) == 2:
            return (v[0], v[1])
        if len(v) == 1:
            return (v, None)  # 单字母，位置由列表上下文决定
        return None
    if isinstance(v, dict):
        el = v.get('element')
        if el is None:
            return None
        idx = v.get('index', None)
        base = resolve_code(mapping.get(el), mapping, depth+1)
        if base is None:
            return None
        if idx == 0:
            return (base[0], None)
        if idx == 1:
            return (None, base[1])
        return base
    if isinstance(v, list) and len(v) == 2:
        da = db = None
        # 第一项: 大码
        x = v[0]
        if isinstance(x, str) and len(x) >= 1:
            da = x[0]
        else:
            r = resolve_code(x, mapping, depth+1)
            if r is None:
                return None
            da = r[0] if r[0] is not None else r[1]
        # 第二项: 小码
        y = v[1]
        if isinstance(y, str) and len(y) >= 1:
            db = y[0]
        else:
            r = resolve_code(y, mapping, depth+1)
            if r is None:
                return None
            db = r[1] if r[1] is not None else r[0]
        if da and db:
            return (da, db)
        return None
    return None

def load_roots():
    """返回 (元素->(大码,小码), 组->元素列表, 未解析项)"""
    d = load_yaml()
    mp = d['form']['mapping']
    codes = {}
    for k, v in mp.items():
        if k.startswith('首字母') or k.startswith('末字母'):
            continue  # 优化约束标记，非字根
        r = resolve_code(v, mp)
        if r and r[0] and r[1]:
            codes[k] = r
    unresolved = {k: v for k, v in mp.items()
                  if k not in codes and not k.startswith('首字母') and not k.startswith('末字母')}
    groups = defaultdict(list)
    for k, (a, b) in codes.items():
        groups[(a, b)].append(k)
    return codes, dict(groups), unresolved

def load_table(path):
    """码表: 字 -> [码...] (保持文件顺序)"""
    d = defaultdict(list)
    order = []
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line or line.startswith('#'):
            continue
        p = line.split('\t')
        if len(p) >= 2:
            if p[0] not in d:
                order.append(p[0])
            d[p[0]].append(p[1])
    return dict(d), order

def load_freq(path='/workspace/chs_data/kc6000.txt'):
    """频表: 字 -> 频 (按序)"""
    freq = {}
    for line in open(path, encoding='utf-8'):
        p = line.split()
        if len(p) >= 2:
            try:
                freq[p[0]] = int(p[1])
            except ValueError:
                continue
    return freq

if __name__ == '__main__':
    codes, groups, unresolved = load_roots()
    print('元素总数(可解析):', len(codes), ' 未解析:', len(unresolved))
    print('未解析样例:', list(unresolved.items())[:8])
    print('字根组数:', len(groups))
    sizes = Counter(len(v) for v in groups.values())
    print('组大小分布:', dict(sorted(sizes.items())))
    da = Counter(a for a, b in codes.values())
    print('大码分布:', dict(sorted(da.items())))
    # 小码合规检查样本
    print('样例组:')
    for g in list(groups)[:10]:
        print(' ', g, groups[g])
