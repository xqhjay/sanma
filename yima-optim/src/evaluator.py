"""字劫测评工具算法的忠实复现.

从 chs.hertz.ltd 的前端 JS 逆向还原的测评逻辑:
- 输入码表 (char -> [codes]) 与字频表 [[char, freq], ...]
- 每字取最短码为实际使用码 R
- L  (simpleCollision/出简重): R 在 U[R] (含全码占用) 中的位置
- oe (simpleCollisionExclFull/出简重-排除全码): R 在 m[R] (最短码恰为 R 的字) 中的位置
- re (fullCollision/全码重): 最长码相同者中的位置
- brief2 (理论二简): 频序下该字的 2 码前缀首次出现
- 分区间: [0,300) [300,500) [500,1500) [1500,3000) [3000,6000)
"""

RANGES = [(0, 300), (300, 500), (500, 1500), (1500, 3000), (3000, 6000)]
RANGE_NAMES = ["前300", "300~500", "500~1500", "1500~3000", "3000~6000"]


def parse_code_table(path):
    """解析 码表 txt: char<TAB>code, 返回 (codeMap char->[codes 按文件序], codeToChars)."""
    code_map = {}
    code_to_chars = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 2:
                ch, code = parts[0], parts[1].lower()
                code_map.setdefault(ch, [])
                if code not in code_map[ch]:
                    code_map[ch].append(code)
                code_to_chars.setdefault(code, [])
                if ch not in code_to_chars[code]:
                    code_to_chars[code].append(ch)
    return code_map, code_to_chars


def load_freq(path, limit=66000):
    """加载字频表: char<TAB>freq, 按频降序."""
    lst = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2 and len(parts[0]) == 1:
                try:
                    lst.append((parts[0], int(parts[1])))
                except ValueError:
                    continue
    lst.sort(key=lambda x: -x[1])
    return lst[:limit]


def evaluate(code_map, freq_list, select_keys=";'456789", n=4, top=6000):
    """复现 cv() 的核心逻辑, 返回逐字记录列表 (频序)."""
    a = [(c, f) for c, f in freq_list[:top]]
    E = set(c for c, _ in a)

    # U: code -> [chars], 按 codeMap (文件序) 插入
    U = {}
    for ch, codes in code_map.items():
        if ch not in E:
            continue
        for code in codes:
            U.setdefault(code, [])
            if ch not in U[code]:
                U[code].append(ch)

    # S: 最长码 -> [chars] (文件序)
    S = {}
    for ch, codes in code_map.items():
        if ch not in E or not codes:
            continue
        longest = max(codes, key=len)
        S.setdefault(longest, [])
        S[longest].append(ch)

    # I: char -> 最短码
    I = {}
    for ch, codes in code_map.items():
        if codes:
            I[ch] = min(codes, key=len)

    # m: code -> [chars 且 I[char]==code]
    m = {}
    for code, chars in U.items():
        mm = [c for c in chars if I.get(c) == code]
        if mm:
            m[code] = mm

    records = []
    seen_prefix = set()
    full_counter = {}
    for ch, freq in a:
        codes = code_map.get(ch)
        if not codes:
            records.append({'char': ch, 'freq': freq, 'isLack': True})
            continue
        R = min(codes, key=len)
        W = len(R)
        longest = max(codes, key=len)
        H = U.get(R)
        L = H.index(ch) + 1 if H and ch in H else 1
        z = m.get(R)
        oe = z.index(ch) + 1 if z and ch in z else 1
        re_ = full_counter.get(longest, 0) + 1
        full_counter[longest] = re_
        # brief2: 频序下 2 码前缀首现
        ue = False
        if W >= 2:
            pfx = R[:2]
            if pfx not in seen_prefix:
                seen_prefix.add(pfx)
                ue = True
        select = ""
        if L > 1:
            idx = min(L - 2, len(select_keys) - 1)
            select = select_keys[idx]
        elif W < n:
            select = " "
        records.append({
            'char': ch, 'freq': freq, 'isLack': False,
            'code': R, 'codeLen': W, 'longestCode': longest,
            'collision': L, 'simpleCollision': L,
            'simpleCollisionExclFull': oe, 'fullCollision': re_,
            'brief2': ue, 'selectKey': select,
        })
    return records


def summarize(records, excl_full=False):
    """按区间聚合各指标."""
    out = {}
    for (s, e), name in zip(RANGES, RANGE_NAMES):
        seg = [r for r in records[s:e] if not r.get('isLack')]
        out[name] = {
            'n': len(seg),
            'cd1': sum(1 for r in seg if r['codeLen'] == 1),
            'cd2': sum(1 for r in seg if r['codeLen'] == 2),
            'cd3': sum(1 for r in seg if r['codeLen'] == 3),
            '出简重': sum(1 for r in seg if (r['simpleCollisionExclFull'] if excl_full else r['simpleCollision']) > 1),
            '全码重': sum(1 for r in seg if r['fullCollision'] > 1),
            '理论二简': sum(1 for r in seg if r['brief2']),
            '缺字': sum(1 for r in records[s:e] if r.get('isLack')),
        }
    return out


def print_summary(title, records):
    print(f"\n{'='*72}\n{title}\n{'='*72}")
    for mode, excl in [("出简重(含全码占用)", False), ("出简重(排除全码)", True)]:
        s = summarize(records, excl)
        print(f"\n--- {mode} ---")
        hdr = f"{'区间':<10}{'字数':>5}{'1码':>5}{'2码':>5}{'3码':>6}{'出简重':>7}{'全码重':>7}{'理论二简':>8}{'缺字':>5}"
        print(hdr)
        for name in RANGE_NAMES:
            d = s[name]
            print(f"{name:<10}{d['n']:>5}{d['cd1']:>5}{d['cd2']:>5}{d['cd3']:>6}{d['出简重']:>7}{d['全码重']:>7}{d['理论二简']:>8}{d['缺字']:>5}")
        # 汇总指标
        top1500 = records[:1500]
        r1500_3000 = records[1500:3000]
        top6000 = records[:6000]
        def cnt(seg, key, excl): return sum(1 for r in seg if not r.get('isLack') and ((r['simpleCollisionExclFull'] if excl else r['simpleCollision']) > 1))
        print(f"\n[关键指标] 前1500二码字总数: {sum(1 for r in top1500 if not r.get('isLack') and r['codeLen']==2)}")
        print(f"[关键指标] 前1500出简重: {cnt(top1500,'x',excl)}  1501~3000出简重: {cnt(r1500_3000,'x',excl)}  前6000出简重: {cnt(top6000,'x',excl)}")
        print(f"[关键指标] 前1500全码重: {sum(1 for r in top1500 if not r.get('isLack') and r['fullCollision']>1)}  前6000全码重: {sum(1 for r in top6000 if not r.get('isLack') and r['fullCollision']>1)}")


if __name__ == '__main__':
    import sys
    base = '/workspace/yima-optim/data'
    freq = load_freq(f'{base}/zijie_kc6000.txt')
    for name in ['奕码四二顶-官方最新修正版', '奕码三定-官方最新修正版']:
        cm, _ = parse_code_table(f'{base}/sanma/{name}.txt')
        recs = evaluate(cm, freq)
        print_summary(f'官方 {name} (基线)', recs)
