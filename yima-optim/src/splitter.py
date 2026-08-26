"""拆分引擎: 基于 IDS 树的递归拆分 (复现字劫工具的 decompose 逻辑).

数据源:
- sky_ids.txt: U+XXXX \t 字 \t IDS[...G]  (多源变体, _pickG 规则优先 [G] 源)
- stroke.txt: 字 \t 笔画序列
- 官方 yaml: glyph_customization (拆分定制) + transformers (结构变换) + form.mapping (字根编码)

拆分算法 (字劫 decompose):
  recursively expand IDS tree until all leaves are roots.
"""
import re


def pick_G(fields):
    """复现 _pickG: 优先带 [G] 标签的变体(去标签), 否则第一个无标签的."""
    first_untagged = None
    for f in fields:
        f = f.strip()
        if not f:
            continue
        m = re.match(r'^(.*?)\[([A-Z]+)\]\s*$', f)
        if m:
            if 'G' in m.group(2):
                return m.group(1)
        else:
            if first_untagged is None:
                first_untagged = f
    return first_untagged


def load_sky_ids(path):
    decomp = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line.strip() or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) < 3:
                continue
            ch = parts[1]
            ids = pick_G(parts[2:])
            if ids:
                decomp[ch] = ids
    return decomp


def load_strokes(path):
    strokes = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) >= 2:
                strokes.setdefault(parts[0], parts[1])
    return strokes


class IdsNode:
    """IDS 树节点."""
    __slots__ = ('char', 'op', 'children')

    def __init__(self, char=None, op=None, children=None):
        self.char = char
        self.op = op
        self.children = children

    def is_leaf(self):
        return self.char is not None

    def leaves(self):
        if self.is_leaf():
            return [self.char]
        out = []
        for c in self.children:
            out.extend(c.leaves())
        return out

    def to_ids(self):
        if self.is_leaf():
            return self.char
        return self.op + ''.join(c.to_ids() for c in self.children)


# IDS 运算符与操作数数量
IDS_OPS = {'⿰': 2, '⿱': 2, '⿲': 3, '⿳': 3, '⿴': 2, '⿵': 2, '⿶': 2,
           '⿷': 2, '⿸': 2, '⿹': 2, '⿺': 2, '⿻': 2, '⿼': 2, '⿽': 2}


def parse_ids(s):
    """解析 IDS 字符串为树."""
    if not s:
        return None
    s = s.strip()
    # 去掉 [G] 等标签
    s = re.sub(r'\[[A-Z]+\]', '', s).strip()
    if not s:
        return None
    pos = [0]

    def parse():
        if pos[0] >= len(s):
            return None
        ch = s[pos[0]]
        pos[0] += 1
        if ch in IDS_OPS:
            n = IDS_OPS[ch]
            children = []
            for _ in range(n):
                c = parse()
                if c is None:
                    return None
                children.append(c)
            return IdsNode(op=ch, children=children)
        return IdsNode(char=ch)

    tree = parse()
    if pos[0] != len(s):
        return None  # 未完全消费 → 解析失败
    return tree


class Splitter:
    def __init__(self, decomp, roots, custom=None, transformers=None):
        self.decomp = decomp      # char -> IDS string
        self.roots = roots        # set of root glyphs (含变体)
        self.custom = custom or {}
        self.transformers = transformers or []
        self.cache = {}

    def get_ids(self, ch):
        """取字的 IDS (优先定制)."""
        if ch in self.custom:
            return self.custom[ch]
        return self.decomp.get(ch)

    def decompose(self, ch):
        if ch in self.cache:
            return self.cache[ch]
        # 字根身份优先 (复现 _buildWithIds 的 roots.has 检查)
        if ch in self.roots:
            tree = IdsNode(char=ch)
            self.cache[ch] = tree
            return tree
        ids = self.get_ids(ch)
        if not ids:
            tree = IdsNode(char=ch)
            self.cache[ch] = tree
            return tree
        tree = parse_ids(ids)
        if tree is None:
            tree = IdsNode(char=ch)
            self.cache[ch] = tree
            return tree
        expanded = self._expand(tree, frozenset([ch]))
        self.cache[ch] = expanded
        return expanded

    def _expand(self, node, visited):
        if node.is_leaf():
            if node.char in self.roots:
                return node
            # 非根叶子 → 继续展开其 IDS
            if node.char in visited:
                return node  # 环路保护
            ids = self.get_ids(node.char)
            if not ids:
                return node
            sub = parse_ids(ids)
            if sub is None:
                return node
            return self._expand(sub, visited | {node.char})
        children = [self._expand(c, visited) for c in node.children]
        return IdsNode(op=node.op, children=children)

    def leaves(self, ch):
        return self.decompose(ch).leaves()
