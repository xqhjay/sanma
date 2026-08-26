"""验证拆分引擎: 用官方字根映射+官方布局重编码, 与官方码表对比."""
import sys
sys.path.insert(0, '/workspace/yima-optim/src')
import yaml
from splitter import Splitter, load_sky_ids, load_strokes, parse_ids, IdsNode
from evaluator import parse_code_table, load_freq

BASE = '/workspace/yima-optim/data'


def build_variant_map(mapping):
    """variant glyph -> main root glyph."""
    vmap = {}
    for k, v in mapping.items():
        if isinstance(v, dict) and 'element' in v:
            vmap[k] = v['element']
    return vmap


def main():
    data = yaml.safe_load(open(f'{BASE}/sanma/奕码_小泥巴_1.2.yaml', encoding='utf-8'))
    mapping = data['form']['mapping']

    # 主字根: 简单 2 字母编码的字根
    main_roots = {k: v for k, v in mapping.items() if isinstance(v, str) and len(v) == 2}
    variant_map = build_variant_map(mapping)

    # 根集合 = 主根 + 变体 (变体拆到即可, 编码时映射回主根)
    root_set = set(main_roots.keys()) | set(variant_map.keys())
    print(f"主字根组: {len(main_roots)}, 变体根: {len(variant_map)}, 总根字形: {len(root_set)}")

    # 字根 -> 编码 (大码+小码)
    def root_code(g):
        g2 = variant_map.get(g, g)
        return main_roots.get(g2)

    # 拆分定制: glyph_customization (char -> {operator, operandList})
    custom = {}
    for ch, spec in data['data'].get('glyph_customization', {}).items():
        if isinstance(spec, dict) and 'operator' in spec:
            ops = spec['operandList']
            custom[ch] = spec['operator'] + ''.join(str(o) for o in ops)

    decomp = load_sky_ids(f'{BASE}/zijie_sky_ids.txt')
    print(f"IDS 数据: {len(decomp)} 字")

    sp = Splitter(decomp, root_set, custom=custom)

    # 官方码表 (全码)
    official, _ = parse_code_table(f'{BASE}/sanma/奕码三定-官方最新修正版.txt')
    full_code = {}  # char -> 3码全码 (最长码)
    for ch, codes in official.items():
        full_code[ch] = max(codes, key=len)

    def encode(leaves):
        """按奕码规则编码: 单根=大大小; 两根=大大小; 多根=大大末大."""
        if not leaves:
            return None
        codes = [root_code(l) for l in leaves]
        if any(c is None for c in codes):
            return None
        if len(leaves) == 1:
            c = codes[0]
            return c[0] + c[1] + c[1]
        if len(leaves) == 2:
            return codes[0][0] + codes[1][0] + codes[1][1]
        return codes[0][0] + codes[1][0] + codes[-1][0]

    match = mismatch = nocode = 0
    mism_examples = []
    for ch, ocode in full_code.items():
        if len(ocode) != 3:
            continue
        try:
            leaves = sp.leaves(ch)
        except RecursionError:
            nocode += 1
            continue
        mycode = encode(leaves)
        if mycode is None:
            nocode += 1
            continue
        if mycode == ocode:
            match += 1
        else:
            mismatch += 1
            if len(mism_examples) < 30:
                mism_examples.append((ch, ocode, mycode, ''.join(leaves)))
    total = match + mismatch + nocode
    print(f"\n验证结果: 总 {total} 字, 匹配 {match} ({match/total*100:.1f}%), "
          f"不匹配 {mismatch} ({mismatch/total*100:.1f}%), 无法编码 {nocode}")
    print("\n不匹配示例 (字, 官方码, 我的码, 拆分):")
    for ch, oc, mc, lv in mism_examples:
        print(f"  {ch}  {oc}  {mc}  {lv}")


if __name__ == '__main__':
    main()
