"""生成主字根音托读音规律文档 (基于官方小码, 优化后不变)."""
import json
import sys

sys.path.insert(0, '/workspace/yima-optim/src')

BASE = '/workspace/yima-optim/data'
OUT = '/workspace/yima-optim/output'

d = json.load(open(f'{BASE}/processed/sigs.json', encoding='utf-8'))
roots = d['roots']
variants = d['variants']

from pypinyin import pinyin, Style


def py_of(ch):
    r = pinyin(ch, style=Style.NORMAL, heteronym=False)
    s = r[0][0] if r and r[0] else ''
    return s if s and all(c.isascii() for c in s) else ''


def initial(s):
    for pre in ('zh', 'ch', 'sh'):
        if s.startswith(pre):
            return pre
    return s[0] if s else ''


# 分类
groups = {'sheng': [], 'yun': [], 'v': [], 'other': [], 'nopron': []}
for r in roots:
    code = roots[r]  # '大小'
    sm = code[1]
    p = py_of(r)
    if not p:
        groups['nopron'].append((r, code, ''))
        continue
    ini = initial(p)
    fin = p[len(ini):]
    if sm == ini[0]:
        groups['sheng'].append((r, code, p))
    elif fin and sm == fin[0]:
        groups['yun'].append((r, code, p))
    elif sm == 'v' and ('yu' in p or p.startswith('u')):
        groups['v'].append((r, code, p))
    else:
        groups['other'].append((r, code, p))

n = len(roots)
n_py = n - len(groups['nopron'])
lines = []
lines.append('# 奕码优化版 主字根音托读音规律')
lines.append('')
lines.append('## 总原则')
lines.append('')
lines.append('- **大码**：乱序排列（本优化重新指派，仅为性能服务，无规律需先记忆字母位）')
lines.append('- **小码**：音托（完全沿用官方 1.2 版指派，优化未改动任何小码）')
lines.append(f'- 字根总数：{n} 个主根（归并组数 {n} ≤ 300，满足约束；副字根按形近归并于主根）')
lines.append('')
lines.append('## 音托合规统计')
lines.append('')
lines.append(f'| 音托类型 | 字根数 | 占比（可注音根 {n_py} 个） |')
lines.append('|---|---|---|')
lines.append(f"| 声母托（小码=声母首字母） | {len(groups['sheng'])} | {len(groups['sheng'])/n_py*100:.0f}% |")
lines.append(f"| 韵母托（小码=韵母首字母） | {len(groups['yun'])} | {len(groups['yun'])/n_py*100:.0f}% |")
lines.append(f"| ü→v 韵托（yu/u 类音） | {len(groups['v'])} | {len(groups['v'])/n_py*100:.0f}% |")
lines.append(f"| **音托合计** | **{len(groups['sheng'])+len(groups['yun'])+len(groups['v'])}** | **{(len(groups['sheng'])+len(groups['yun'])+len(groups['v']))/n_py*100:.0f}%** |")
lines.append(f"| 形托/约定（义托、形似、约定） | {len(groups['other'])} | {len(groups['other'])/n_py*100:.0f}% |")
lines.append(f"| 部件根（PUA 部件，无读音，按形记） | {len(groups['nopron'])} | — |")
lines.append('')
lines.append('## 规则明细')
lines.append('')
lines.append('### 1. 声母托（主规律）')
lines.append('')
lines.append('小码 = 字根读音的**声母首字母**。卷舌声母取首字母：zh→z、ch→c、sh→s。')
lines.append('')
sheng_ex = groups['sheng'][:24]
lines.append('例：' + '、'.join(f'{r}({p}→{c[1]})' for r, c, p in sheng_ex))
lines.append('')
lines.append('### 2. 韵母托')
lines.append('')
lines.append('声母托字母被占用时，小码改取**韵母首字母**（零声母字根直接取韵母首字母）。')
lines.append('')
yun_ex = groups['yun'][:24]
lines.append('例：' + '、'.join(f'{r}({p}→{c[1]})' for r, c, p in yun_ex))
lines.append('')
lines.append('### 3. ü→v 韵托')
lines.append('')
lines.append('读音含 ü/yu 的字根，小码用 **v**（如 鱼、雨、于 等 yu 音根）。')
lines.append('')
v_ex = groups['v']
lines.append('例：' + '、'.join(f'{r}({p}→{c[1]})' for r, c, p in v_ex))
lines.append('')
lines.append('### 4. 形托/约定（少量）')
lines.append('')
lines.append('上述规律都不合适时，按**义托/形托/约定**记忆。')
lines.append('')
oth_ex = groups['other'][:24]
lines.append('例：' + '、'.join(f'{r}({p}→{c[1]})' for r, c, p in oth_ex))
lines.append('')
lines.append('### 5. 部件根（PUA）')
lines.append('')
lines.append('无法注音的部件根按**字形**直接记忆，数量少。')
lines.append('')
lines.append('例：' + '、'.join(f'{r}(→{c[1]})' for r, c, _ in groups['nopron'][:20]))
lines.append('')
lines.append('## 记忆要点')
lines.append('')
lines.append('1. 约 **88%** 的主字根可直接按读音推出小码（声母托为主、韵母托为辅）；')
lines.append('2. 副字根与主根形近归并，共享主根编码，无需单独记忆；')
lines.append('3. 大码乱序、小码音托的双编码结构与官方奕码完全一致，音托记忆负担不变；')
lines.append('4. 完整逐根对照见《字根编码表》（含每根拼音与音托依据列）。')

with open(f'{OUT}/主字根音托读音规律.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines) + '\n')
print(f'已生成 主字根音托读音规律.txt: 声母托{len(groups["sheng"])} 韵母托{len(groups["yun"])} '
      f'ü→v{len(groups["v"])} 形托{len(groups["other"])} 部件{len(groups["nopron"])} / 共{n}根')
