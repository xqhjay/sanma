"""端到端验证: 用字劫测评复现 (evaluator) 对比 官方 vs 优化 码表."""
import sys

sys.path.insert(0, '/workspace/yima-optim/src')
from evaluator import parse_code_table, load_freq, evaluate

BASE = '/workspace/yima-optim/data'
OUT = '/workspace/yima-optim/output'


def key_metrics(path, freq):
    cm, _ = parse_code_table(path)
    recs = evaluate(cm, freq)
    r15 = recs[:1500]
    r23 = recs[1500:3000]
    r60 = recs[:6000]

    def cnt(seg, excl=True):
        return sum(1 for r in seg if not r.get('isLack')
                   and ((r['simpleCollisionExclFull'] if excl else r['simpleCollision']) > 1))
    return dict(
        M1=sum(1 for r in r15 if not r.get('isLack') and r['codeLen'] == 2),
        C1500=cnt(r15),
        M2=cnt(r23),
        M3=cnt(r60),
        full6000=sum(1 for r in r60 if not r.get('isLack') and r['fullCollision'] > 1),
        cd2_6000=sum(1 for r in r60 if not r.get('isLack') and r['codeLen'] == 2),
        lack=sum(1 for r in r60 if r.get('isLack')),
    )


def main():
    freq = load_freq(f'{BASE}/zijie_kc6000.txt')
    tables = [
        ('官方四二顶 1.2', f'{BASE}/sanma/奕码四二顶-官方最新修正版.txt'),
    ]
    import os
    for f in sorted(os.listdir(OUT)):
        if f.startswith('奕码优化_四二顶') and f.endswith('.txt'):
            tables.append(('优化 ' + f, f'{OUT}/{f}'))
    print(f"{'表':<28} {'M1':>5} {'C1500':>6} {'M2':>4} {'M3':>5} {'6000内二码':>10} {'6000内全码重':>12} {'缺字':>4}")
    for name, path in tables:
        m = key_metrics(path, freq)
        print(f"{name:<28} {m['M1']:>5} {m['C1500']:>6} {m['M2']:>4} {m['M3']:>5} "
              f"{m['cd2_6000']:>10} {m['full6000']:>12} {m['lack']:>4}")


if __name__ == '__main__':
    main()
