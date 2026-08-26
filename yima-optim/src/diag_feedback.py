"""诊断: 官方 vs 优化 四二顶码表 结构与全指标对比 (L/oe/re_ 三口径)."""
import sys
from collections import defaultdict

sys.path.insert(0, '/workspace/yima-optim/src')
from evaluator import parse_code_table, load_freq, evaluate

BASE = '/workspace/yima-optim/data'
OUT = '/workspace/yima-optim/output'


def analyze(name, path, freq):
    cm, _ = parse_code_table(path)
    # 2码条目
    two_entries = [(ch, c) for ch, codes in cm.items() for c in codes if len(c) == 2]
    prefixes = defaultdict(list)
    for ch, c in two_entries:
        prefixes[c].append(ch)
    dup2 = {c: v for c, v in prefixes.items() if len(v) > 1}
    s_chars = {ch for ch, c in two_entries}
    # 全码组
    groups = defaultdict(list)
    for ch, codes in cm.items():
        groups[max(codes, key=len)].append(ch)
    s_in_colliding = sum(1 for code, mem in groups.items()
                         if len(mem) >= 2 and any(m in s_chars for m in mem))
    n_colliding = sum(1 for mem in groups.values() if len(mem) >= 2)

    print(f'== {name} ==')
    print(f'  2码条目: {len(two_entries)}, 唯一2码前缀: {len(prefixes)}, '
          f'重复2码(二字共码): {len(dup2)}')
    for c, v in list(dup2.items())[:5]:
        print(f'    重复2码 {c}: {v}')
    print(f'  全码组(>=2字): {n_colliding}, 其中含S字的: {s_in_colliding}')

    recs = evaluate(cm, freq)

    def seg(a, b):
        return recs[a:b]

    def cnt(rec, key):
        return sum(1 for r in rec if not r.get('isLack') and r[key] > 1)

    for label, a, b in [('前1500', 0, 1500), ('1501~3000', 1500, 3000), ('3001~6000', 3000, 6000), ('前6000', 0, 6000)]:
        rec = seg(a, b)
        m1 = sum(1 for r in rec if not r.get('isLack') and r['codeLen'] == 2)
        print(f'  {label}: 二码字={m1} 出简重L={cnt(rec, "simpleCollision")} '
              f'出简重oe={cnt(rec, "simpleCollisionExclFull")} 全码重={cnt(rec, "fullCollision")}')
    print()


def main():
    freq = load_freq(f'{BASE}/zijie_kc6000.txt')
    analyze('官方四二顶 1.2', f'{BASE}/sanma/奕码四二顶-官方最新修正版.txt', freq)
    for zh in ['均衡', '极速', '低重']:
        analyze(f'优化四二顶·{zh}', f'{OUT}/奕码优化_四二顶码表_{zh}.txt', freq)


if __name__ == '__main__':
    main()
