"""官方拆分表加载器: 奕码拆分-官方.txt → 根字符序列 (100% 忠实官方).

根名解析链:
  1. 方案 mapping 直查 (口 木 氵 1-6 ...)
  2. repertoire name → PUA/字符, 再经 element 链解析到方案根
  3. 特判: 月凡→f000(jy), 或字心→e800(me), 彧两撇→彡(is)
"""
import json
import sys
import yaml

sys.path.insert(0, '/workspace/yima-optim/src')

BASE = '/workspace/yima-optim/data'

# 官方拆分表晚于 repertoire 版本的新名 → 方案根字符
SPECIAL_NAMES = {
    '月凡': '\uf000',      # 赢 pjq 验证: 大码 j
    '或字心': '\ue800',    # 或 qm 验证: 大码 m
    '彧两撇': '彡',         # 彧 qmi 验证: 大码 i
}


def build_name_map():
    """根名 → 方案根字符 (可直接查 main_roots 的键)."""
    rep = json.load(open(f'{BASE}/chai_data/repertoire_all.json', encoding='utf-8'))
    name2ch = {}
    for it in rep:
        if isinstance(it, dict) and it.get('name'):
            name2ch[it['name']] = chr(it['unicode'])
    name2ch.update(SPECIAL_NAMES)
    return name2ch


def resolve_element_chain(ch, mapping):
    """跟随 {'element': X} 链直到得到编码串. 返回编码或 None."""
    seen = set()
    while ch in mapping and ch not in seen:
        seen.add(ch)
        v = mapping[ch]
        if isinstance(v, str):
            return v
        if isinstance(v, dict) and 'element' in v:
            ch = v['element']
            continue
        if isinstance(v, list) and len(v) == 2:
            # 双编码列表 [大, 小]: 分量 = 字母 或 {element,index}
            out = ''
            for part in v:
                if isinstance(part, str):
                    out += part
                elif isinstance(part, dict) and 'element' in part:
                    sub = resolve_element_chain(part['element'], mapping)
                    if sub is None:
                        return None
                    out += sub[part.get('index', 0)]
                else:
                    return None
            return out
        return None
    return None


def load_official_splits():
    """返回 (splits: char -> [根名字符串], roots_resolved: char -> [根字符])."""
    name2ch = build_name_map()
    data = yaml.safe_load(open(f'{BASE}/sanma/奕码_小泥巴_1.2.yaml', encoding='utf-8'))
    mapping = data['form']['mapping']

    splits = {}       # char -> 根名列表
    resolved = {}     # char -> 根字符列表 (方案键)
    unresolved = {}   # 根名 -> 次数
    for line in open(f'{BASE}/sanma/奕码拆分-官方.txt', encoding='utf-8'):
        parts = line.rstrip('\n').split('\t')
        if len(parts) < 2:
            continue
        ch, rootstr = parts[0], parts[1]
        names = rootstr.split()
        splits[ch] = names
        out = []
        ok = True
        for nm in names:
            if nm in mapping:
                out.append(nm)
            elif nm in name2ch:
                rc = name2ch[nm]
                if rc in mapping:
                    out.append(rc)
                else:
                    # element 链: 名字字符不在 mapping, 但它可能作为 element 被引用
                    out.append(rc)
            else:
                unresolved[nm] = unresolved.get(nm, 0) + 1
                ok = False
        resolved[ch] = out if ok else None
    return splits, resolved, unresolved


def encode_split(roots, code_of):
    """官方 encoder 状态机 (由官方码表逆向验证):
    - 1 根: 大 + 小 + 小        (回 dh→dhh, 水 is→iss)
    - 2 根: 大1 + 大2 + 小2     (相 sf m: 木sm+目fm)
    - 3+ 根: 大1 + 大2 + 大末   (就 c h d: 享字头cg+小hx+尤dy)
    """
    codes = [code_of(r) for r in roots]
    if any(c is None for c in codes):
        return None
    n = len(codes)
    if n == 1:
        return codes[0][0] + codes[0][1] + codes[0][1]
    if n == 2:
        return codes[0][0] + codes[1][0] + codes[1][1]
    return codes[0][0] + codes[1][0] + codes[-1][0]


if __name__ == '__main__':
    from chaisplit import load_scheme
    main_roots, variant_map, special, customize, glyph_cust, _ = load_scheme()
    raw_mapping = yaml.safe_load(
        open(f'{BASE}/sanma/奕码_小泥巴_1.2.yaml', encoding='utf-8'))['form']['mapping']

    def code_of(r):
        if r in variant_map:
            r = variant_map[r]
        if r in main_roots and isinstance(main_roots[r], str):
            return main_roots[r]
        return resolve_element_chain(r, raw_mapping)

    splits, resolved, unresolved = load_official_splits()
    print(f'官方拆分: {len(splits)} 字, 未解析根名: {unresolved}')

    # 编码并对比官方四二顶码表
    official_codes = {}
    for line in open(f'{BASE}/sanma/奕码四二顶-官方最新修正版.txt', encoding='utf-8'):
        parts = line.split()
        if len(parts) >= 2:
            official_codes.setdefault(parts[0], []).append(parts[1])

    # 变体已在 code_of 内处理
    code_of_full = code_of

    match = miss = noc = 0
    bad = []
    for ch, roots in resolved.items():
        if roots is None:
            continue
        code = encode_split(roots, code_of_full)
        oc = official_codes.get(ch)
        if not oc:
            continue
        if code and code in oc:
            match += 1
        elif code is None:
            noc += 1
        else:
            miss += 1
            if len(bad) < 15:
                bad.append((ch, roots, code, oc))
    print(f'三码编码匹配: {match}, 不匹配: {miss}, 无码: {noc}, 共 {match+miss+noc}')
    for b in bad:
        print('  ', b)
