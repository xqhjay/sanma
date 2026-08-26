"""码表生成: 最优大码 + 精确加权二码指派 → 四二顶/三定/字根编码/拆分 表.

输出格式与官方一致: 字\t码\r\n, 按码字典序 (同码组内按频序, 高频在前).
用法: python gen_tables.py [big.npy路径] [w_m1] [w_m2] [w_m3] [后缀]
"""
import json
import os
import sys
import numpy as np

sys.path.insert(0, '/workspace/yima-optim/src')
from optimize2 import Optimizer

BASE = '/workspace/yima-optim/data'
OUT = '/workspace/yima-optim/output'


def letters(codes):
    return ''.join(chr(97 + c) for c in codes)


def py_of(ch):
    from pypinyin import pinyin, Style
    r = pinyin(ch, style=Style.NORMAL, heteronym=False)
    s = r[0][0] if r and r[0] else ''
    return s if s and all(c.isascii() for c in s) else ''


def initial(s):
    for pre in ('zh', 'ch', 'sh'):
        if s.startswith(pre):
            return pre
    return s[0] if s else ''


def yintuo_type(root, code):
    """返回 (拼音, 音托类型)."""
    p = py_of(root)
    if not p:
        return '', '部件(形托)' if not root.isascii() else '数字根'
    sm = code[1]
    ini = initial(p)
    fin = p[len(ini):]
    if sm == ini[0]:
        return p, '声母托'
    if fin and sm == fin[0]:
        return p, '韵母托'
    if sm == 'v' and ('yu' in p or p.startswith('u')):
        return p, 'ü→v韵托'
    return p, '形托/约定'


def build(opt, big, w_m1=3000.0, w_m2=200.0, w_m3=20.0):
    """返回 (full_codes: char->3码, prefix_codes: char->2码, 指标)."""
    prefix, full = opt.prefix_full(big)
    S, m1, c15, c23, c36 = opt.assign_and_conflicts(
        prefix, full, w_m1=w_m1, w23=w_m2, w36=w_m3)
    full_map = {}
    pfx_map = {}
    for i in range(opt.N):
        ch = opt.chars[i]
        full_map[ch] = letters([full[i] // 676, full[i] // 26 % 26, full[i] % 26])
        if S[i]:
            pfx_map[ch] = letters([prefix[i] // 26, prefix[i] % 26])
    return full_map, pfx_map, (m1, c15, c23, c36)


def write_table(path, entries):
    """entries: [(char, code)] 已排序; 写 字\t码\r\n."""
    with open(path, 'w', encoding='utf-8', newline='') as f:
        for ch, code in entries:
            f.write(f'{ch}\t{code}\r\n')


def load_rank():
    freq = []
    for line in open(f'{BASE}/zijie_kc6000.txt', encoding='utf-8'):
        p = line.strip().split('\t')
        if len(p) >= 2 and len(p[0]) == 1:
            try:
                freq.append((p[0], int(p[1])))
            except ValueError:
                pass
    freq.sort(key=lambda x: -x[1])
    return {ch: i for i, (ch, _) in enumerate(freq)}


def main():
    big_path = sys.argv[1] if len(sys.argv) > 1 else f'{BASE}/processed/big_sa.npy'
    w_m1 = float(sys.argv[2]) if len(sys.argv) > 2 else 3000.0
    w_m2 = float(sys.argv[3]) if len(sys.argv) > 3 else 200.0
    w_m3 = float(sys.argv[4]) if len(sys.argv) > 4 else 20.0
    suffix = sys.argv[5] if len(sys.argv) > 5 else ''

    opt = Optimizer()
    big = np.load(big_path)
    full_map, pfx_map, (m1, c15, c23, c36) = build(opt, big, w_m1, w_m2, w_m3)
    print(f'指标: M1={m1}, C1500={c15}, M2={c23}, M3={c36} (权重 {w_m1}/{w_m2}/{w_m3}, {os.path.basename(big_path)})')
    assert c15 == 0, '前1500出简重必须为0!'

    rank = load_rank()
    rk = lambda ch: rank.get(ch, 99999)
    os.makedirs(OUT, exist_ok=True)

    # ---------- 四二顶 ----------
    entries = []
    for ch, code in full_map.items():
        if ch in pfx_map:
            entries.append((ch, pfx_map[ch]))
        entries.append((ch, code))
    entries.sort(key=lambda e: (e[1], rk(e[0])))
    write_table(f'{OUT}/奕码优化_四二顶码表{suffix}.txt', entries)
    print(f'四二顶: {len(entries)} 行 (二码 {len(pfx_map)}, 全码 {len(full_map)})')

    # ---------- 三定 ----------
    # 一简: 每字母 → 以该字母开头的最高频二码字 (官方规则: 一简 ⊆ 四二顶二码字)
    by_first = {}
    for ch, p in pfx_map.items():
        by_first.setdefault(p[0], []).append(ch)
    yijian = {}
    for l, chs in by_first.items():
        yijian[min(chs, key=rk)] = l
    # 二简: 四二顶二码字; 若为一简字, 让位给该前缀次优候选
    erjian = {}
    prefix_owner = {}
    for ch, p in pfx_map.items():
        prefix_owner.setdefault(p, []).append(ch)
    for p, chs in prefix_owner.items():
        chs = sorted(chs, key=rk)
        pick = chs[0] if chs[0] not in yijian else (chs[1] if len(chs) > 1 else chs[0])
        if pick in yijian:
            cands = [c for c in full_map
                     if full_map[c].startswith(p) and c not in yijian]
            pick = min(cands, key=rk) if cands else chs[0]
        erjian[pick] = p
    entries3 = list(yijian.items()) + list(erjian.items()) + list(full_map.items())
    entries3.sort(key=lambda e: (e[1], rk(e[0])))
    write_table(f'{OUT}/奕码优化_三定码表{suffix}.txt', entries3)
    print(f'三定: {len(entries3)} 行 (一简 {len(yijian)}, 二简 {len(erjian)}, 全码 {len(full_map)})')

    # ---------- 字根编码表 ----------
    d = json.load(open(f'{BASE}/processed/sigs.json', encoding='utf-8'))
    roots = d['roots']
    variants = d['variants']
    inv = {}
    for v, m in variants.items():
        inv.setdefault(m, []).append(v)
    lines = ['# 奕码优化版 字根编码表 (小码=官方音托不变, 大码=优化指派)',
             '# 格式: 字根\t编码(大+小)\t拼音\t音托依据\t变体(形近归并)']
    order = sorted(roots.keys(), key=lambda r: big[opt.ridx[r]])
    ntype = {}
    for r in order:
        code = chr(97 + big[opt.ridx[r]]) + roots[r][1]
        p, t = yintuo_type(r, code)
        ntype[t] = ntype.get(t, 0) + 1
        vs = ' '.join(inv.get(r, []))
        lines.append(f'{r}\t{code}\t{p}\t{t}\t{vs}')
    with open(f'{OUT}/字根编码表{suffix}.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'字根编码表: {len(roots)} 根, 音托分布: {ntype}')

    # ---------- 拆分表 ----------
    chars = d['chars']
    lines = ['# 奕码优化版 拆分表 (官方拆分 100% 保真, 根名为主根字符)']
    items = sorted(chars.items(), key=lambda kv: kv[1]['rank'])
    for ch, e in items:
        lines.append(f"{ch}\t{' '.join(e['roots'])}")
    with open(f'{OUT}/拆分表{suffix}.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'拆分表: {len(chars)} 字')

    # 保存指派供报告用
    json.dump({'yijian': yijian, 'erjian': erjian, 'pfx': pfx_map,
               'metrics': dict(M1=m1, C1500=c15, M2=c23, M3=c36,
                               weights=[w_m1, w_m2, w_m3])},
              open(f'{BASE}/processed/assignment{suffix}.json', 'w', encoding='utf-8'),
              ensure_ascii=False)


if __name__ == '__main__':
    main()
