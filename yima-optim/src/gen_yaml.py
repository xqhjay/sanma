"""生成小泥巴平台方案文件 (YAML): 官方结构 + 优化大码.

原理: 深拷贝官方 奕码_小泥巴_1.2.yaml, 仅替换 form.mapping 中 272 个主根的
"大码+小码" (小码不变, 大码=优化指派), 并更新 info 元数据.
两个引用式编码值特殊处理:
  '6': [{'element': '5', 'index': 0}, 'i']  → 6 的大码引用 5 的大码: 若优化后
      两者不同字母则改为独立字符串, 相同则保留引用 (自动跟随);
  '冖': ['c', {'element': '宀', 'index': 1}] → 首字母替换为新大码, 保留宀小码引用.

用法: python gen_yaml.py [big表名(mid/m1max/relief) ...]  (默认三个全出)
"""
import copy
import json
import sys

import numpy as np
import yaml

sys.path.insert(0, '/workspace/yima-optim/src')
from optimize2 import Optimizer

BASE = '/workspace/yima-optim/data'
OUT = '/workspace/yima-optim/output'

VARIANTS = {
    'mid': '均衡',
    'm1max': '极速',
    'relief': '低重',
}


def resolve(mapping, r, depth=0):
    """解析 mapping 中根 r 的生效编码 (字符串值或列表引用值)."""
    v = mapping.get(r)
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if depth > 5:
        return None
    out = ''
    for part in v:
        if isinstance(part, str):
            out += part
        elif isinstance(part, dict):
            ref = resolve(mapping, part['element'], depth + 1)
            if ref is None:
                return None
            out += ref[part.get('index', 0)]
    return out


def main():
    names = sys.argv[1:] or list(VARIANTS)
    opt = Optimizer()
    sigs = json.load(open(f'{BASE}/processed/sigs.json', encoding='utf-8'))
    roots = sigs['roots']
    official = yaml.safe_load(open(f'{BASE}/sanma/奕码_小泥巴_1.2.yaml', encoding='utf-8'))

    for name in names:
        zh = VARIANTS.get(name, name)
        big = np.load(f'{BASE}/processed/big_{name}.npy')
        d = copy.deepcopy(official)
        m = d['form']['mapping']

        # 替换 272 主根编码 (小码不变)
        n_changed = 0
        for r in roots:
            new_code = chr(97 + int(big[opt.ridx[r]])) + roots[r][1]
            v = m.get(r)
            if isinstance(v, str):
                if v != new_code:
                    m[r] = new_code
                    n_changed += 1
            elif r == '冖':
                # [旧大码, {element: 宀, index: 1}] → 首字母换新大码, 保留宀引用
                m[r] = [new_code[0], v[1]]
                if resolve(m, '冖') != new_code:
                    m[r] = new_code
            elif r == '6':
                # [{'element': '5', 'index': 0}, 'i']: 6大码=5大码? 相同则保留引用
                if new_code[0] == chr(97 + int(big[opt.ridx['5']])):
                    pass  # 保留引用, 自动跟随 5 的新大码
                else:
                    m[r] = new_code
            else:
                m[r] = new_code

        d['info'] = {
            'name': f'奕码优化·{zh}',
            'author': '小泥巴(原版) / 大码重排优化',
            'version': '1.2-opt',
            'description': '乱序音托双编三码定长形码输入方案·优化版'
                           f'({zh}: 拆分与小码音托与官方1.2完全一致, 仅重排大码)',
        }

        path = f'{OUT}/奕码_小泥巴_优化_{zh}.yaml'
        with open(path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(d, f, allow_unicode=True, sort_keys=False, width=1000000)
        print(f'[{zh}] 已生成 {path} (大码变更 {n_changed} 根)')

        # ---------- 校验 ----------
        chk = yaml.safe_load(open(path, encoding='utf-8'))
        cm = chk['form']['mapping']
        # 1) 272 根生效编码 == 优化后编码
        bad = []
        for r in roots:
            new_code = chr(97 + int(big[opt.ridx[r]])) + roots[r][1]
            got = resolve(cm, r)
            if got != new_code:
                bad.append((r, got, new_code))
        # 2) 变体根仍正确指向主根
        n_var_ok = sum(1 for v, main in sigs['variants'].items()
                       if isinstance(cm.get(v), dict) and cm[v].get('element') == main)
        # 3) 逐字全码 == 四二顶码表三码条目
        table = {}
        for line in open(f'{OUT}/奕码优化_四二顶码表_{zh}.txt', encoding='utf-8'):
            p = line.rstrip('\r\n').split('\t')
            if len(p) == 2 and len(p[1]) == 3:
                table[p[0]] = p[1]
        mism = 0
        for ch, e in sigs['chars'].items():
            rs = e['roots']
            codes = []
            for r in rs:
                c = resolve(cm, r)
                if c is None:
                    codes = None
                    break
                codes.append(c)
            if codes is None:
                mism += 1
                continue
            n = len(codes)
            if n == 1:
                full = codes[0][0] + codes[0][1] + codes[0][1]
            elif n == 2:
                full = codes[0][0] + codes[1][0] + codes[1][1]
            else:
                full = codes[0][0] + codes[1][0] + codes[-1][0]
            if table.get(ch) != full:
                mism += 1
                if mism <= 3:
                    print(f'   不匹配示例: {ch} 表={table.get(ch)} yaml={full}')
        print(f'[{zh}] 校验: 根编码不符 {len(bad)}, 变体指向正确 {n_var_ok}/{len(sigs["variants"])}, '
              f'逐字全码不符 {mism}/{len(sigs["chars"])}')
        assert not bad and mism == 0, f'{zh} 校验失败!'


if __name__ == '__main__':
    main()
