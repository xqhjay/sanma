"""ChaiSans 曲线拓扑的 Python 精确移植 (bezier.ts).

曲线类型: h/v 线性, c/z 三次贝塞尔(平撇平点平捺), a 圆弧(圈).
关系: 交(相交), 连(端点重合/点在线段内), 离散(平行/垂直 + 区间5级比较).
区间关系: 先于=-1 部分先于=-0.5 重叠=0 部分后于=0.5 后于=1.
坐标为整数, 端点相等为精确比较.
"""
from __future__ import annotations


def dist(p1, p2):
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def is_collinear_on_segment(from_pt, to_pt, point):
    """点 point 是否严格在线段 from→to 内 (共线且在中间)."""
    u = sub(to_pt, point)
    v = sub(from_pt, point)
    return cross(u, v) == 0 and dot(u, v) < 0


class Interval:
    __slots__ = ('lo', 'hi')

    def __init__(self, a, b):
        self.lo, self.hi = (a, b) if a < b else (b, a)

    def compare(self, other: 'Interval'):
        if self.hi < other.lo:
            return -1
        if self.lo > other.hi:
            return 1
        if self.lo < other.lo and self.hi < other.hi:
            return -0.5
        if self.lo > other.lo and self.hi > other.hi:
            return 0.5
        return 0


class Curve:
    def start_end(self):
        raise NotImplementedError

    def orientation(self):
        raise NotImplementedError

    def kind(self):
        raise NotImplementedError

    def intervals(self):
        s, e = self.start_end()
        return (Interval(s[0], e[0]), Interval(s[1], e[1]))

    def main_cross_intervals(self):
        x, y = self.intervals()
        return (x, y) if self.orientation() == 'horizontal' else (y, x)

    def length(self):
        s, e = self.start_end()
        return dist(s, e)

    # ---------- 关系 ----------
    def relation(self, c: 'Curve'):
        rel = self._connected(c)
        if rel is not None:
            return rel
        if self.kind() == 'linear' and c.kind() == 'linear':
            return self._linear_general(c)
        return self._general(c)

    def _connected(self, c: 'Curve'):
        a_s, a_e = self.start_end()
        b_s, b_e = c.start_end()
        if a_s == b_s:
            return ('连', '前', '前')
        if a_s == b_e:
            return ('连', '前', '后')
        if a_e == b_s:
            return ('连', '后', '前')
        if a_e == b_e:
            return ('连', '后', '后')
        if self.kind() == 'linear':
            if is_collinear_on_segment(a_s, a_e, b_s):
                return ('连', '中', '前')
            if is_collinear_on_segment(a_s, a_e, b_e):
                return ('连', '中', '后')
        if c.kind() == 'linear':
            if is_collinear_on_segment(b_s, b_e, a_s):
                return ('连', '前', '中')
            if is_collinear_on_segment(b_s, b_e, a_e):
                return ('连', '后', '中')
        return None

    def _linear_general(self, c: 'Curve'):
        a_s, a_e = self.start_end()
        b_s, b_e = c.start_end()
        v = sub(a_e, a_s)
        v1 = sub(b_s, a_s)
        v2 = sub(b_e, a_s)
        vc = cross(v, v1) * cross(v, v2)
        u = sub(b_e, b_s)
        u1 = sub(a_s, b_s)
        u2 = sub(a_e, b_s)
        uc = cross(u, u1) * cross(u, u2)
        if vc < 0 and uc < 0:
            return ('交',)
        return self._discrete(c)

    def _general(self, c: 'Curve'):
        inter = self._intersection(c)
        if inter is None:
            return self._discrete(c)
        a_s, a_e = self.start_end()
        b_s, b_e = c.start_end()
        ERR = 3
        if dist(inter, a_s) < ERR:
            return ('连', '前', '中')
        if dist(inter, a_e) < ERR:
            return ('连', '后', '中')
        if dist(inter, b_s) < ERR:
            return ('连', '中', '前')
        if dist(inter, b_e) < ERR:
            return ('连', '中', '后')
        return ('交',)

    def _intersection(self, c: 'Curve'):
        a_s, a_e = self.start_end()
        b_s, b_e = c.start_end()
        ax, ay = self.intervals()
        bx, by = c.intervals()
        if ax.compare(bx) in (-1, 1) or ay.compare(by) in (-1, 1):
            return None
        if self.length() < 1 and c.length() < 1:
            return ((a_s[0] + a_e[0] + b_s[0] + b_e[0]) / 4,
                    (a_s[1] + a_e[1] + b_s[1] + b_e[1]) / 4)
        a1, a2 = self._bisect()
        b1, b2 = c._bisect()
        return (a1._intersection(b1) or a1._intersection(b2)
                or a2._intersection(b1) or a2._intersection(b2))

    def _discrete(self, c: 'Curve'):
        if self.orientation() == c.orientation():
            am, ac = self.main_cross_intervals()
            bm, bc = c.main_cross_intervals()
            return ('平行', am.compare(bm), ac.compare(bc))
        ax, ay = self.intervals()
        bx, by = c.intervals()
        return ('垂直', ax.compare(bx), ay.compare(by))


class Linear(Curve):
    __slots__ = ('orient', 'p1', 'p2')

    def __init__(self, orientation, p1, p2):
        self.orient = orientation
        self.p1, self.p2 = p1, p2

    def start_end(self):
        return self.p1, self.p2

    def orientation(self):
        return self.orient

    def kind(self):
        return 'linear'

    def _bisect(self):
        mid = ((self.p1[0] + self.p2[0]) / 2, (self.p1[1] + self.p2[1]) / 2)
        return (Linear(self.orient, self.p1, mid), Linear(self.orient, mid, self.p2))


class Cubic(Curve):
    __slots__ = ('orient', 'ps')

    def __init__(self, orientation, p0, p1, p2, p3):
        self.orient = orientation
        self.ps = [p0, p1, p2, p3]

    def start_end(self):
        return self.ps[0], self.ps[3]

    def orientation(self):
        return self.orient

    def kind(self):
        return 'cubic'

    def _bisect(self):
        p0, p1, p2, p3 = self.ps
        p01 = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
        p12 = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        p23 = ((p2[0] + p3[0]) / 2, (p2[1] + p3[1]) / 2)
        a = ((p01[0] + p12[0]) / 2, (p01[1] + p12[1]) / 2)
        b = ((p12[0] + p23[0]) / 2, (p12[1] + p23[1]) / 2)
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        return (Cubic(self.orient, p0, p01, a, m), Cubic(self.orient, m, b, p23, p3))


class Arc(Curve):
    __slots__ = ('s',)

    def __init__(self, start):
        self.s = start

    def start_end(self):
        return self.s, self.s

    def orientation(self):
        return 'horizontal'

    def kind(self):
        return 'arc'

    def _bisect(self):
        return (self, self)


def create_curve(prev_pos, draw):
    cmd = draw['command']
    pl = draw['parameterList']
    if cmd == 'h':
        return Linear('horizontal', prev_pos, (prev_pos[0] + pl[0], prev_pos[1]))
    if cmd == 'v':
        return Linear('vertical', prev_pos, (prev_pos[0], prev_pos[1] + pl[0]))
    if cmd in ('c', 'z'):
        p1 = (prev_pos[0] + pl[0], prev_pos[1] + pl[1])
        p2 = (prev_pos[0] + pl[2], prev_pos[1] + pl[3])
        p3 = (prev_pos[0] + pl[4], prev_pos[1] + pl[5])
        orient = 'vertical' if cmd == 'c' else 'horizontal'
        return Cubic(orient, prev_pos, p1, p2, p3)
    if cmd == 'a':
        return Arc(prev_pos)
    raise ValueError(f'未知命令 {cmd}')


class StrokeGraphic:
    """笔画图形: feature + 曲线列表. 关系为曲线对的元组列表."""

    __slots__ = ('feature', 'curves')

    def __init__(self, spec):
        self.feature = spec['feature']
        self.curves = []
        prev = (spec['start'][0], spec['start'][1])
        for d in spec.get('curveList', []):
            cv = create_curve(prev, d)
            prev = cv.start_end()[1]
            self.curves.append(cv)

    def relation(self, other: 'StrokeGraphic'):
        return tuple(c1.relation(c2) for c1 in self.curves for c2 in other.curves)


class Topology:
    """笔画拓扑矩阵: matrix[i][j] = i 与 j 的关系 (元组), 用于根匹配精确比较."""

    __slots__ = ('n', 'matrix')

    def __init__(self, strokes: list[StrokeGraphic]):
        n = len(strokes)
        self.n = n
        self.matrix = [[None] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    self.matrix[i][j] = ()
                else:
                    self.matrix[i][j] = strokes[i].relation(strokes[j])
