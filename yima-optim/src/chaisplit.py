"""ChaiSans 字库驱动的拆分引擎 v2.

数据链:
  奕码_小泥巴_1.2.yaml form.mapping  →  270 主根编码 + 278 变体→主根
  repertoire_all.json               →  每字复合定义 (多候选) + 笔画数据
  analysis.customize                →  官方定制拆分 (20条)
  data.glyph_customization          →  官方字形定制 (63条)

拆分策略 (复现官方 analysis.selector):
  1. 多候选择: ChaiSans 每字可能有多个复合定义, 取「全叶为根且根数最少」者 (根少优先)
  2. ⿺/⿹ 包围结构换序: 辶廴弋等后写包围件放根序列末尾 (连续笔顺)
  3. 笔画级兜底: 非根部件 (basic_component/PUA) 用笔画序列 DP 分割成根 (根少优先)

编码: 大码+小码; 单根=大大小, 两根=大大小, 3+根=大大末大 (复现 encoder 状态机).
"""
import json
import re
import yaml

BASE = '/workspace/yima-optim/data'


# ---------- 笔画分类 (ChaiSans classifier: 5类 + 奕码定制第6类横折弯钩) ----------
FEATURE_CLASS = {
    # 1 横(含提)
    '横': '1', '提': '1',
    # 2 竖(含竖钩)
    '竖': '2', '竖钩': '2',
    # 3 撇(含平撇)
    '撇': '3', '平撇': '3',
    # 4 点/捺(含平点平捺挑捺)
    '点': '4', '平点': '4', '捺': '4', '平捺': '4', '挑捺': '4',
    # 5 折(各种折笔)
    '横钩': '5', '横撇': '5', '横折': '5', '横折钩': '5', '横斜钩': '5',
    '横折提': '5', '横折折': '5', '横折弯': '5', '横撇弯钩': '5',
    '横斜弯钩': '5', '横折折撇': '5', '横折折折': '5', '横折折折钩': '5',
    '竖提': '5', '竖折': '5', '竖弯': '5', '竖弯左': '5', '竖弯钩': '5',
    '竖折撇': '5', '竖折折钩': '5', '竖折折': '5', '撇点': '5', '撇折': '5',
    '弯钩': '5', '斜钩': '5', '撇钩': '5', '卧钩': '5', '圈': '5',
    '特殊笔画': '5', '乙': '5',
    # 6 横折弯钩 (奕码 classifier 定制)
    '横折弯钩': '6',
}

# 笔画字符 -> feature 名 (IDS/STROKE_MAP 用到的笔画字符)
STROKE_CHAR_FEATURE = {
    '一': '横', '㇀': '提', '丨': '竖', '亅': '竖钩', '丨': '竖',
    '丿': '撇', '㇓': '撇', '㇒': '平撇',
    '丶': '点', '㇔': '点', '乀': '捺', '㇏': '捺', '乁': '捺',
    '乙': '横折弯钩', '㇠': '横钩', '㇖': '横钩', '㇇': '横撇',
    '𠃍': '横折', '𠃌': '横折钩', '㇪': '横折提',
    '㇕': '横折', '㇆': '横折钩', '㇗': '竖提', '𠃊': '竖折',
    '㇙': '竖弯钩', '㇄': '竖弯', '㇁': '弯钩', '㇂': '斜钩',
    '㇃': '卧钩', '㇟': '竖折折钩', '㇉': '撇折', '㇊': '竖折撇',
    '㇈': '横折弯钩', '㇋': '横折折', '㇌': '横折弯',
    '㇎': '横斜弯钩', '㇍': '横折折折钩', '㇜': '撇点',
    '乚': '竖弯钩', '乛': '横钩', '𠃋': '撇折',
}

STROKE_MAP = {}  # 笔画字符 -> 类号 '1'-'6'
for _c, _f in STROKE_CHAR_FEATURE.items():
    STROKE_MAP[_c] = FEATURE_CLASS[_f]

# CJK 部首区字符/片假名形近件 → 标准字根 (用于 IDS 兜底数据)
CJK_RADICAL_EQUIV = {
    '⺝': '月', '⺮': '竹', '⻊': '足', '⺕': '彐', '⺧': '牛', '⻗': '雨',
    '⺊': '卜', '⺶': '羊', '⺷': '羊', '⺇': '几', '⺆': '冂', 'ㄇ': '冂',
    '𠂇': '右', '𧘇': '衣', '⺁': '厂', '⺀': '冫', 'キ': '手', '⼹': '彐',
    '𠤎': '匕', '⺈': '角', '⺌': '龸', '⺍': '龸', 'ユ': '匚', '⺽': '鼠',
    '⺄': '5', '⼀': '一', '⼃': '丿', '⼂': '丶', '⼁': '丨', '⼄': '乙',
    '⺅': '亻', '⺆': '几', '⺉': '刀', '⺋': '乛', '⺏': '文', '⺒': '弓',
    '⺓': '乛', '⺔': '㔾', '⺕': '彐', '⺖': '忄', '⺗': '心', '⺘': '扌',
    '⺙': '戈', '⺛': '户', '⺜': '日', '⺟': '母', '⺠': '一', '⺡': '氵',
    '⺢': '水', '⺣': '犬', '⺤': '爫', '⺥': '月', '⺦': '爻', '⺪': '疋',
    '⺫': '目', '⺬': '示', '⺭': '礻', '⺮': '竹', '⺯': '乂', '⺰': '糸',
    '⺱': '毌', '⺲': '一', '⺳': '四', '⺴': '一', '⺵': '一', '⺶': '羊',
    '⺸': '王', '⺹': '罒', '⺺': '一', '⻀': '艹', '⻁': '虎', '⻂': '虫',
    '⻃': '牛', '⻄': '犬', '⻅': '见', '⻆': '角', '⻇': '言', '⻈': '讠',
    '⻉': '贝', '⻋': '车', '⻌': '辶', '⻍': '辶', '⻎': '邑', '⻏': '阝',
    '⻐': '长', '⻑': '长', '⻒': '镸', '⻓': '长', '⻔': '门', '⻕': '阝',
    '⻖': '钅', '⻗': '雨', '⻘': '青', '⻙': '韭', '⻚': '页', '⻛': '风',
    '⻜': '飞', '⻝': '食', '⻞': '食', '⻟': '食', '⻠': '饣', '⻡': '耳',
    '⻢': '马', '⻣': '骨', '⻤': '鬼', '⻥': '鱼', '⻦': '鸟', '⻧': '卤',
    '⻨': '麦', '⻩': '黄', '⻪': '黾', '⻫': '齐', '⻬': '齐', '⻭': '齿',
    '⻮': '齿', '⻯': '竜', '⻰': '龙', '⻱': '龟', '⻲': '龟', '⻳': '龟',
}


def load_scheme(yaml_path=None):
    """加载奕码方案: 主根编码, 变体映射, 定制拆分, ChaiSans 复合定义."""
    yaml_path = yaml_path or f'{BASE}/sanma/奕码_小泥巴_1.2.yaml'
    data = yaml.safe_load(open(yaml_path, encoding='utf-8'))
    m = data['form']['mapping']
    main_roots = {k: v for k, v in m.items()
                  if isinstance(v, str) and len(v) == 2 and len(k) == 1}
    variant_map = {}
    for k, v in m.items():
        if isinstance(v, dict) and 'element' in v and len(k) == 1:
            e = v['element']
            if isinstance(e, str) and len(e) == 1:
                variant_map[k] = e
    # 特殊 list 映射: '6' -> [5的大码, i] => 'wi'; '冖' -> [c, 宀的小码] => 'cb'
    special = {'6': 'wi', '冖': 'cb'}

    # 官方定制拆分 (analysis.customize): 字 -> 根列表
    customize = {}
    for ch, parts in (data.get('analysis', {}).get('customize') or {}).items():
        if isinstance(parts, list):
            customize[ch] = list(parts)

    # 字形定制 (glyph_customization): 字 -> {operator, operandList(码点)}
    glyph_cust = {}
    for ch, spec in (data['data'].get('glyph_customization') or {}).items():
        if isinstance(spec, dict) and 'operator' in spec:
            ops = ''.join(chr(o) if isinstance(o, int) else str(o)
                          for o in spec.get('operandList', []))
            glyph_cust[ch] = spec['operator'] + ops

    return main_roots, variant_map, special, customize, glyph_cust, data


def load_chai_rep(rep_path=None):
    """ChaiSans 字库 -> {char: [glyph,...]} (原始 glyph 列表)."""
    rep_path = rep_path or f'{BASE}/chai_data/repertoire_all.json'
    rep = json.load(open(rep_path, encoding='utf-8'))
    by = {}
    for entry in rep:
        cp = entry.get('unicode')
        if cp is None:
            continue
        try:
            glyphs = json.loads(entry['glyphs'])
        except (json.JSONDecodeError, TypeError):
            continue
        if glyphs:
            by[chr(cp)] = glyphs
    return by


def compound_candidates(glyphs):
    """从 glyph 列表提取复合定义候选: [(op, [operand chars]), ...] G源优先."""
    cands = []
    for g in glyphs:
        if g.get('type') in ('compound', 'spliced_component'):
            ops = [chr(o) if isinstance(o, int) else o
                   for o in g.get('operandList', [])]
            cands.append((g.get('operator'), ops, 'G' in g.get('tags', [])))
    # G 源优先
    cands.sort(key=lambda c: 0 if c[2] else 1)
    return [(op, ops) for op, ops, _ in cands]


IDS_OPS = {'⿰': 2, '⿱': 2, '⿲': 3, '⿳': 3, '⿴': 2, '⿵': 2, '⿶': 2,
           '⿷': 2, '⿸': 2, '⿹': 2, '⿺': 2, '⿻': 2, '⿼': 2, '': 2}

# 后写包围件: ⿺辶X / ⿺廴X 中辶廴实际后写, 根序放末尾 (连续笔顺).
# 其余 ⿺ 包围件 (瓜/毛/气等) 先写, 保持 IDS 顺序.
LATE_SURROUND = {'辶', '廴'}


class ChaiSplitter:
    """基于 ChaiSans 复合定义的拆分器 (多候选 + 换序 + 笔画兜底)."""

    MAX_SEG = 12  # DP 段最大笔画数

    def __init__(self, main_roots, variant_map, special, chai_rep,
                 customize=None, glyph_cust=None, extra_ids=None):
        self.main_roots = main_roots
        self.variant_map = variant_map
        self.special = special
        self.chai_rep = chai_rep
        self.customize = customize or {}
        self.glyph_cust = glyph_cust or {}
        self.extra_ids = extra_ids or {}
        # 根集合 = 主根 + 变体原字 + 笔画类字符 + 特殊
        self.root_glyphs = set(main_roots) | set(variant_map) | \
            set(STROKE_MAP) | set(special) | set('123456')
        # 复合定义多候选缓存
        self._cand_cache = {}
        self.cache = {}
        self._strokes_cache = {}
        # 根笔画字典 (DP 兜底用)
        self.root_strokes = {}
        self._build_root_strokes()

    # ---------- 初始化 ----------

    def _build_root_strokes(self):
        """构建 DP 兜底用的根笔画字典 (仅主根, 防变体形近冒充)."""
        # 主根
        for g in self.main_roots:
            feats = self.char_strokes(g)
            if feats:
                self.root_strokes.setdefault(feats, g)
        # 笔画类号 (兜底, 不覆盖已有)
        for f, cls in FEATURE_CLASS.items():
            self.root_strokes.setdefault((f,), cls)
        # 类序列字典 (形近归并: 竖钩≡竖 等), 键 = 类号序列
        self.root_classes = {}
        for feats, root in self.root_strokes.items():
            cls_seq = tuple(FEATURE_CLASS.get(f, '5') for f in feats)
            if cls_seq not in self.root_classes:
                self.root_classes[cls_seq] = root

    def char_strokes(self, ch, depth=0):
        """提取字符笔画 feature 序列 (tuple), 失败 None."""
        if ch in self._strokes_cache:
            return self._strokes_cache[ch]
        if depth > 12:
            return None
        glyphs = self.chai_rep.get(ch)
        if not glyphs:
            self._strokes_cache[ch] = None
            return None
        ordered = sorted(glyphs,
                         key=lambda g: 0 if 'G' in g.get('tags', []) else 1)
        result = None
        for g in ordered:
            t = g.get('type')
            r = None
            if t == 'basic_component':
                r = tuple(s.get('feature') for s in g.get('strokes', []))
                if not r:
                    r = None
            elif t == 'identity':
                src = g.get('source')
                if src:
                    r = self.char_strokes(chr(src), depth + 1)
            elif t == 'derived_component':
                src = g.get('source')
                srcst = self.char_strokes(chr(src), depth + 1) if src else None
                out, ok = [], True
                for s in g.get('strokes', []):
                    f = s.get('feature')
                    if f == 'reference':
                        i = s.get('index')
                        if srcst is not None and i is not None and i < len(srcst):
                            out.append(srcst[i])
                        else:
                            ok = False
                            break
                    else:
                        out.append(f)
                r = tuple(out) if ok and out else None
            elif t in ('compound', 'spliced_component'):
                out, ok = [], True
                for o in g.get('operandList', []):
                    oc = chr(o) if isinstance(o, int) else o
                    st = self.char_strokes(oc, depth + 1)
                    if st is None:
                        ok = False
                        break
                    out.extend(st)
                r = tuple(out) if ok and out else None
            if r:
                result = r
                break
        self._strokes_cache[ch] = result
        return result

    # ---------- 规范化 ----------

    def is_root(self, g):
        return g in self.root_glyphs

    def norm(self, g):
        """字形归一: 变体→主根; 笔画字→类号; CJK部首区→标准."""
        if g in self.variant_map:
            g = self.variant_map[g]
        if g in STROKE_MAP:
            return STROKE_MAP[g]
        if g in self.special:
            return g  # '冖'/'6' 特殊编码根
        if g in CJK_RADICAL_EQUIV:
            g2 = CJK_RADICAL_EQUIV[g]
            if g2 in self.variant_map:
                g2 = self.variant_map[g2]
            return g2
        return g

    def _norm_root(self, g):
        """归一为可编码根字形 (主根/类号/特殊)."""
        g2 = self.norm(g)
        if g2 in self.variant_map:
            g2 = self.variant_map[g2]
        return g2

    # ---------- 候选获取 ----------

    def candidates(self, ch):
        """字的拆分候选: [(kind, data)] kind in {'flat','ids'}."""
        if ch in self._cand_cache:
            return self._cand_cache[ch]
        cands = []
        if ch in self.customize:
            cands.append(('flat', list(self.customize[ch])))
        if ch in self.glyph_cust:
            cands.append(('ids', self.glyph_cust[ch]))
        if ch in self.chai_rep:
            for op, ops in compound_candidates(self.chai_rep[ch]):
                cands.append(('ids', op + ''.join(ops)))
        if ch in self.extra_ids and not cands:
            cands.append(('ids', self.extra_ids[ch]))
        self._cand_cache[ch] = cands
        return cands

    # ---------- 拆分主逻辑 ----------

    def leaves(self, ch):
        """拆分为主根叶序列 (带缓存/环路保护)."""
        return self._expand(ch, frozenset())

    def _expand(self, ch, visited):
        if ch in self.cache:
            return self.cache[ch]
        if ch in visited:
            return [ch]  # 环路
        g = self.norm(ch)
        if g in self.root_glyphs and self.norm(g) == g:
            self.cache[ch] = [g]
            return [g]
        vis = visited | {ch}
        # 多候选择: 全叶为根 且 根数最少 (根少优先)
        best = None
        for kind, data in self.candidates(ch):
            if kind == 'flat':
                out = self._expand_flat(data, vis)
            else:
                tree = parse_ids(data)
                if tree is None:
                    continue
                out = self._expand_tree(tree, vis)
            if out is None:
                continue
            if all(self._encodable(l) for l in out):
                if best is None or len(out) < len(best):
                    best = out
        if best is not None:
            self.cache[ch] = best
            return best
        # derived 结构化拆分 / 笔画级兜底
        for fb in (self._derived_split(ch), self._stroke_fallback(ch)):
            if fb is not None:
                self.cache[ch] = fb
                return fb
        # 未知叶: 用候选展开(允许未知叶)或原字
        for kind, data in self.candidates(ch):
            if kind == 'flat':
                out = self._expand_flat(data, vis, lax=True)
            else:
                tree = parse_ids(data)
                if tree is None:
                    continue
                out = self._expand_tree(tree, vis, lax=True)
            if out is not None:
                self.cache[ch] = out
                return out
        self.cache[ch] = [g if g in self.root_glyphs else ch]
        return self.cache[ch]

    def _encodable(self, l):
        return l in self.main_roots or l in self.special

    def _expand_flat(self, parts, visited, lax=False):
        out = []
        for r in parts:
            r2 = self.norm(r)
            if r2 in self.root_glyphs:
                out.append(self._norm_root(r2))
            else:
                sub = self._expand(r, visited)
                out.extend(sub)
        return out

    def _expand_tree(self, node, visited, lax=False):
        if node.char is not None:
            g = node.char
            g2 = self.norm(g)
            if g2 in self.root_glyphs and self.norm(g2) == g2:
                return [self._norm_root(g2)]
            if g in visited:
                return [g2 if g2 in self.root_glyphs else g]
            # 非根叶: 递归展开 (若其有复合定义)
            if self.candidates(g):
                return self._expand(g, visited)
            # derived 结构化拆分 / 笔画兜底
            for fb in (self._derived_split(g), self._stroke_fallback(g)):
                if fb is not None:
                    return fb
            return [g2 if g2 in self.root_glyphs else g]
        children = node.children
        # ⿺辶X/⿺廴X: 辶廴后写, 根序放末尾
        if node.op == '⿺' and children and \
                children[0].char in LATE_SURROUND:
            children = list(reversed(children))
        out = []
        for c in children:
            sub = self._expand_tree(c, visited, lax)
            if sub is None:
                return None
            out.extend(sub)
        return out

    # ---------- 笔画 DP 兜底 ----------

    def _derived_split(self, ch):
        """derived_component 结构化拆分: ref 连续块=源根, 新笔画逐笔成类根.

        朱 = derived(未+前置撇) → [3, 未]; 失 = derived(夫+前置撇) → [3, 夫];
        亏 = derived(丂+前置横) → [1, 丂]; 于 = derived(二+后置竖钩) → [二, 2].
        ref 分裂 (如 必 = 心中插撇) 时返回 None 走 DP.
        """
        glyphs = self.chai_rep.get(ch) or []
        ordered = sorted(glyphs,
                         key=lambda g: 0 if 'G' in g.get('tags', []) else 1)
        for g in ordered:
            if g.get('type') != 'derived_component':
                continue
            src = g.get('source')
            if not src:
                continue
            src_root = self._norm_root(chr(src))
            if not self._encodable(src_root):
                continue
            strokes = g.get('strokes', [])
            n = len(strokes)
            if n == 0 or all(s.get('feature') == 'reference' for s in strokes):
                continue
            refs = [i for i, s in enumerate(strokes)
                    if s.get('feature') == 'reference']
            k = len(refs)

            def feats2roots(idxs):
                out = []
                for i in idxs:
                    cls = FEATURE_CLASS.get(strokes[i].get('feature'))
                    if cls is None:
                        return None
                    out.append(cls)
                return out

            result = None
            if refs == list(range(k)):  # 源在前, 新笔画在后
                new = feats2roots(range(k, n))
                if new is not None:
                    result = [src_root] + new
            elif refs == list(range(n - k, n)):  # 新笔画在前, 源在后
                new = feats2roots(range(0, n - k))
                if new is not None:
                    result = new + [src_root]
            else:
                return None  # ref 分裂
            return result

    def _stroke_fallback(self, ch):
        """非根部件的笔画序列 DP 分割成根.

        规则:
        - CJK 区部件禁止整段匹配 (防形近冒充: 失≠矢, 于≠干, 土口≠吉)
        - PUA 部件允许整段匹配 (PUA 通常即根字形)
        - 段匹配: 精确 feature 优先, 类序列兜底 (竖钩≡竖等形近归并)
        - 优化目标: 根数少 → 类号根少 → 最大段长 (取大优先)
        """
        feats = self.char_strokes(ch)
        if not feats:
            return None
        n = len(feats)
        if n == 0 or n > 40:
            return None
        allow_whole = ord(ch) >= 0xE000  # PUA 允许整段
        cls_seq = tuple(FEATURE_CLASS.get(f, '5') for f in feats)

        def seg_root(i, j):
            seg = feats[i:j]
            r = self.root_strokes.get(seg)
            if r is not None:
                return r, 0
            r = self.root_classes.get(cls_seq[i:j])
            if r is not None:
                return r, 1
            return None, 2

        # dp[j] = (根数, -最大段长, 类号根数)  取大优先: 最大段长优先于类号偏好
        INF = (10 ** 9, 0, 10 ** 9)
        dp = [INF] * (n + 1)
        dp[0] = (0, 0, 0)
        choice = [None] * (n + 1)
        for i in range(n):
            if dp[i] == INF:
                continue
            for j in range(i + 1, min(n, i + self.MAX_SEG) + 1):
                if j == n and i == 0 and not allow_whole:
                    continue  # 整段禁止
                root, fuzzy = seg_root(i, j)
                if root is None:
                    continue
                cand = (dp[i][0] + 1,
                        min(dp[i][1], -(j - i)),
                        dp[i][2] + (1 if root in '123456' else 0))
                if cand < dp[j]:
                    dp[j] = cand
                    choice[j] = (i, root)
        if dp[n] == INF:
            return None
        out = []
        j = n
        while j > 0:
            i, root = choice[j]
            out.append(self._norm_root(root))
            j = i
        out.reverse()
        return out


class IdsNode:
    __slots__ = ('char', 'op', 'children')

    def __init__(self, char=None, op=None, children=None):
        self.char = char
        self.op = op
        self.children = children


def parse_ids(s):
    """解析 IDS 字符串 (含 {占位符} 时失败)."""
    if not s:
        return None
    s = s.strip()
    s = re.sub(r'\[[A-Z]+\]', '', s).strip()
    if not s or '{' in s or '}' in s:
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
        return None
    return tree


def encode(leaves, main_roots, special=None):
    """奕码取码: 单根=大大小; 两根=大大小; 3+根=大大末大."""
    special = special or {}
    if not leaves:
        return None
    codes = []
    for l in leaves:
        if l in special:
            codes.append(special[l])
        elif l in main_roots:
            codes.append(main_roots[l])
        else:
            return None
    if len(leaves) == 1:
        c = codes[0]
        return c[0] + c[1] + c[1]
    if len(leaves) == 2:
        return codes[0][0] + codes[1][0] + codes[1][1]
    return codes[0][0] + codes[1][0] + codes[-1][0]


class Oracle:
    """用官方全码反推合法拆分 (码约束 + 笔画覆盖验证).

    对拆分引擎与官方码不一致的字, 在「根笔画序列与字笔画序列(类级)匹配」
    的约束下搜索编码等于官方码的根序列:
      k=1: 根编码 == oc[0:2] 且 oc[2]==oc[1]
      k=2: 根2 编码 == oc[1:3]; 根1 big==oc[0] 且笔画前缀匹配
      k>=3: 首根 big==oc[0], 次根 big==oc[1], 末根 big==oc[2], 笔顺连续分段
    """

    def __init__(self, sp, main_roots, special):
        self.sp = sp
        self.code_of = dict(main_roots)
        self.code_of.update(special)
        self.code2root = {}
        for r, c in self.code_of.items():
            self.code2root.setdefault(c, r)
        self.big2roots = {}
        for r, c in self.code_of.items():
            self.big2roots.setdefault(c[0], []).append(r)
        # 笔画索引: big -> {feats->root, cls->root}; 全局 (任意big)
        self.exact = {}
        self.cls = {}
        self.by_big = {b: ({}, {}) for b in self.big2roots}
        def add(feats, root):
            if feats in self.exact:
                return
            self.exact[feats] = root
            c = tuple(FEATURE_CLASS.get(f, '5') for f in feats)
            self.cls.setdefault(c, root)
            b = self.code_of[root][0]
            self.by_big[b][0].setdefault(feats, root)
            self.by_big[b][1].setdefault(c, root)
        for r in self.code_of:
            f = sp.char_strokes(r)
            if f:
                add(f, r)
        for v, R in sp.variant_map.items():
            if R in self.code_of:
                f = sp.char_strokes(v)
                if f:
                    add(f, R)

    def _seg(self, feats, i, j, big=None):
        """feats[i:j] 段匹配根 (精确优先, 类级兜底); big 限定大码."""
        seg = tuple(feats[i:j])
        if big is not None:
            ex, cl = self.by_big.get(big, ({}, {}))
            r = ex.get(seg)
            if r is not None:
                return r
            return cl.get(tuple(FEATURE_CLASS.get(f, '5') for f in seg))
        r = self.exact.get(seg)
        if r is not None:
            return r
        return self.cls.get(tuple(FEATURE_CLASS.get(f, '5') for f in seg))

    def _cls(self, feats):
        return tuple(FEATURE_CLASS.get(f, '5') for f in feats)

    def correct(self, ch, oc):
        """返回与官方码 oc 一致的根序列, 找不到返回 None."""
        feats = self.sp.char_strokes(ch)
        # k=1
        if oc[1] == oc[2]:
            r = self.code2root.get(oc[0] + oc[1])
            if r is not None:
                f = self.sp.char_strokes(r) or ()
                if feats == f or (feats and self._cls(feats) == self._cls(f)):
                    return [r]
                # 变体字形
                for v, R in self.sp.variant_map.items():
                    if R == r:
                        vf = self.sp.char_strokes(v)
                        if vf and feats and self._cls(feats) == self._cls(vf):
                            return [r]
        if not feats:
            return None
        n = len(feats)
        # k=2
        r2 = self.code2root.get(oc[1] + oc[2])
        if r2 is not None:
            f2s = [self.sp.char_strokes(r2) or ()]
            for v, R in self.sp.variant_map.items():
                if R == r2:
                    vf = self.sp.char_strokes(v)
                    if vf:
                        f2s.append(vf)
            for f2 in f2s:
                for r1 in self.big2roots.get(oc[0], []):
                    f1 = self.sp.char_strokes(r1) or ()
                    if self._cls(feats) == self._cls(f1 + f2):
                        return [r1, r2]
                # 根1 走变体笔画
                for v, R in self.sp.variant_map.items():
                    if self.code_of.get(R, '  ')[0] == oc[0]:
                        f1 = self.sp.char_strokes(v)
                        if f1 and self._cls(feats) == self._cls(f1 + f2):
                            return [R, r2]
        # k>=3: DP 分段 (笔顺连续), 首/次/末根大码约束
        res = self._dp3(feats, oc)
        if res is not None:
            return res
        return None

    def _dp3(self, feats, oc):
        """首根big=oc[0], 次根big=oc[1], 末根big=oc[2] 的连续分段 DP."""
        n = len(feats)
        if n < 3:
            return None
        INF = (10 ** 9,)
        # dp[(i, phase)] = (segs, -maxlen); phase 0=未取首根 1=已取首 2=已取次
        best = {}
        parent = {}

        def relax(i, phase, cand, seg_info):
            key = (i, phase)
            if key not in best or cand < best[key]:
                best[key] = cand
                parent[key] = seg_info

        relax(0, 0, (0, 0), None)
        order = []
        for i in range(n):
            for phase in (0, 1, 2):
                key = (i, phase)
                if key not in best:
                    continue
                base = best[key]
                for j in range(i + 1, min(n, i + self.sp.MAX_SEG) + 1):
                    if phase == 0:
                        r = self._seg(feats, i, j, big=oc[0])
                        if r is None:
                            continue
                        if j >= n:
                            continue  # 首根不能是末根
                        relax(j, 1, (base[0] + 1, min(base[1], -(j - i))),
                              (i, phase, r))
                    elif phase == 1:
                        r = self._seg(feats, i, j, big=oc[1])
                        if r is None:
                            continue
                        if j >= n:
                            continue  # 次根不能是末根 (k>=3)
                        relax(j, 2, (base[0] + 1, min(base[1], -(j - i))),
                              (i, phase, r))
                    else:
                        # 中段: 任意根, j<n
                        r = self._seg(feats, i, j)
                        if r is not None and j < n:
                            relax(j, 2, (base[0] + 1, min(base[1], -(j - i))),
                                  (i, phase, r))
                        # 末段: big=oc[2], j==n
                        if j == n:
                            r = self._seg(feats, i, j, big=oc[2])
                            if r is not None:
                                relax(j, 3, (base[0] + 1,
                                             min(base[1], -(j - i))),
                                      (i, phase, r))
        key = (n, 3)
        if key not in best:
            return None
        out = []
        while key in parent and parent[key] is not None:
            i, phase, r = parent[key]
            out.append(r)
            key = (i, phase)
        out.reverse()
        return out if len(out) >= 3 else None


def build():
    """构建完整拆分器 (一键)."""
    main_roots, variant_map, special, customize, glyph_cust, _ = load_scheme()
    rep = load_chai_rep()
    return ChaiSplitter(main_roots, variant_map, special, rep,
                        customize=customize, glyph_cust=glyph_cust), \
        main_roots, special


if __name__ == '__main__':
    sp, main_roots, special = build()
    for ch in ['攀', '楙', '懋', '这', '造', '亏', '必', '国', '汉']:
        print(ch, sp.leaves(ch))
