"""数据准备: 官方拆分 → 主根签名表 (优化管线的精确数据层).

产出 data/processed/sigs.json:
  roots:  主根字符 -> [大码, 小码]  (含双编码列表值根, 如 冖=cb, 6=wi)
  variants: 变体 -> 主根
  chars:  字 -> {roots: [主根...], kind: 1|2|3, freq排名}
    kind=1: 单根字  码 = 大+小+小,      二码前缀 = 大+小
    kind=2: 两根字  码 = 大1+大2+小2,   二码前缀 = 大1+大2
    kind=3: 3+根字  码 = 大1+大2+大末,  二码前缀 = 大1+大2
"""
import json
import sys
import yaml

sys.path.insert(0, '/workspace/yima-optim/src')
from official_split import load_official_splits, resolve_element_chain, SPECIAL_NAMES

BASE = '/workspace/yima-optim/data'


def build_root_tables():
    """构建 (主根码表 root->[big,small], 变体表 variant->main)."""
    data = yaml.safe_load(open(f'{BASE}/sanma/奕码_小泥巴_1.2.yaml', encoding='utf-8'))
    m = data['form']['mapping']
    roots = {}
    variants = {}
    for k, v in m.items():
        if len(k) != 1:
            continue  # 首字母-X 等非根键
        code = resolve_element_chain(k, m)
        if isinstance(v, str) and len(v) == 2 and len(code) == 2:
            roots[k] = [code[0], code[1]]
        elif isinstance(v, list) and len(code) == 2:
            roots[k] = [code[0], code[1]]
        elif isinstance(v, dict) and 'element' in v and isinstance(v['element'], str) and len(v['element']) == 1:
            e = v['element']
            if e in roots or e in m:
                variants[k] = e
    # 变体链拉直 (变体的变体)
    def flatten(v):
        while v in variants and variants[v] != v:
            v = variants[v]
        return v
    variants = {k: flatten(v) for k, v in variants.items()}
    return roots, variants


def main():
    roots, variants = build_root_tables()
    print(f'主根数: {len(roots)}, 变体数: {len(variants)}')

    splits, resolved, unresolved = load_official_splits()
    # 名字→主根 (拆分表中的名字直接是主根字符 或 repertoire名)
    rep = json.load(open(f'{BASE}/chai_data/repertoire_all.json', encoding='utf-8'))
    name2ch = {it['name']: chr(it['unicode']) for it in rep if isinstance(it, dict) and it.get('name')}
    name2ch.update(SPECIAL_NAMES)

    def to_main(r):
        """拆分根名 → 主根字符 (查码表或变体表)."""
        if r in roots:
            return r
        if r in variants:
            v = variants[r]
            return v if v in roots else None
        if r in name2ch:
            rc = name2ch[r]
            if rc in roots:
                return rc
            if rc in variants:
                v = variants[rc]
                return v if v in roots else None
        return None

    # 频序
    freq = []
    for line in open(f'{BASE}/zijie_kc6000.txt', encoding='utf-8'):
        p = line.strip().split('\t')
        if len(p) >= 2 and len(p[0]) == 1:
            try:
                freq.append((p[0], int(p[1])))
            except ValueError:
                pass
    freq.sort(key=lambda x: -x[1])
    rank = {ch: i for i, (ch, _) in enumerate(freq)}

    chars = {}
    nbad = 0
    for ch, names in splits.items():
        mainseq = []
        ok = True
        for nm in names:
            mr = to_main(nm)
            if mr is None:
                ok = False
                break
            mainseq.append(mr)
        if not ok:
            nbad += 1
            continue
        chars[ch] = {'roots': mainseq, 'rank': rank.get(ch, 99999)}
    print(f'拆分字数: {len(chars)}, 无法解析: {nbad}')

    # 验证: 与官方三码全对 (含 kind 规则)
    official_codes = {}
    for line in open(f'{BASE}/sanma/奕码四二顶-官方最新修正版.txt', encoding='utf-8'):
        p = line.split()
        if len(p) >= 2 and len(p[1]) == 3:
            official_codes[p[0]] = p[1]

    def full_code(entry, big_of):
        rs = entry['roots']
        n = len(rs)
        if n == 1:
            b, s = big_of(rs[0]), roots[rs[0]][1]
            return b + s + s
        if n == 2:
            return big_of(rs[0]) + big_of(rs[1]) + roots[rs[1]][1]
        return big_of(rs[0]) + big_of(rs[1]) + big_of(rs[-1])

    match = miss = 0
    for ch, entry in chars.items():
        oc = official_codes.get(ch)
        if not oc:
            continue
        code = full_code(entry, lambda r: roots[r][0])
        if code == oc:
            match += 1
        else:
            miss += 1
            if miss <= 8:
                print('  ✗', ch, entry['roots'], code, oc)
    print(f'主根化后编码验证: {match} 对, {miss} 错')

    out = {
        'roots': {r: ''.join(v) for r, v in roots.items()},
        'variants': variants,
        'chars': chars,
    }
    json.dump(out, open(f'{BASE}/processed/sigs.json', 'w', encoding='utf-8'),
              ensure_ascii=False)
    print('已保存 data/processed/sigs.json')

    # 结构冲突分析: 同 (R1,R2,R末/小) 签名
    from collections import Counter
    sig_map = {}
    for ch, e in chars.items():
        rs = e['roots']
        n = len(rs)
        if n == 1:
            sig = (rs[0], rs[0], rs[0] + ':s')
        elif n == 2:
            sig = (rs[0], rs[1], rs[1] + ':s')
        else:
            sig = (rs[0], rs[1], rs[-1])
        sig_map.setdefault(sig, []).append((e['rank'], ch))
    top6000_groups = {s: v for s, v in sig_map.items()
                      if sum(1 for r, _ in v if r < 6000) >= 2}
    conflict_cnt = sum(sum(1 for r, _ in v if r < 6000) - 1
                       for v in top6000_groups.values()
                       if sum(1 for r, _ in v if r < 6000) >= 2)
    print(f'结构冲突组(前6000内同签名≥2): {len(top6000_groups)} 组, 冲突字数下限: {conflict_cnt}')
    t15 = {s: v for s, v in sig_map.items() if sum(1 for r, _ in v if r < 1500) >= 2}
    print(f'前1500结构冲突组: {len(t15)}')
    for s, v in sorted(top6000_groups.items(), key=lambda kv: min(r for r, _ in kv[1]))[:10]:
        print('  ', s, sorted(v)[:6])


if __name__ == '__main__':
    main()
