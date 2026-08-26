"""Pareto 探索作业: 不同权重配置的 SA + 精修, 并行运行.

用法: python run_job.py <name>
配置:
  m1max    3000/200/20  M1锁死676, 压 M2/M3
  balanced  150/250/25   仅为 M2 救济牺牲 M1
  relief     25/300/30   为 M2/M3 救济牺牲 M1 (官方哲学的极限版)
"""
import sys
import time
import numpy as np

sys.path.insert(0, '/workspace/yima-optim/src')
from optimize2 import Optimizer, sa, polish

BASE = '/workspace/yima-optim/data'

CONFIGS = {
    'm1max': dict(w_m1=3000.0, w_m2=200.0, w_m3=20.0,
                  init=f'{BASE}/processed/big_sa.npy',
                  phases=[(90000, 40.0, 0.5), (60000, 3.0, 0.1)], seed=11),
    'balanced': dict(w_m1=150.0, w_m2=250.0, w_m3=25.0,
                     init=f'{BASE}/processed/big_sa.npy',
                     phases=[(100000, 120.0, 1.0), (80000, 6.0, 0.15)], seed=21),
    'relief': dict(w_m1=25.0, w_m2=300.0, w_m3=30.0,
                   init='official',
                   phases=[(110000, 200.0, 2.0), (70000, 8.0, 0.15)], seed=31),
    'mid': dict(w_m1=70.0, w_m2=300.0, w_m3=30.0,
                init=f'{BASE}/processed/big_balanced.npy',
                phases=[(100000, 60.0, 0.8), (80000, 5.0, 0.15)], seed=41),
}


def main():
    name = sys.argv[1]
    cfg = CONFIGS[name]
    kw = dict(w_m1=cfg['w_m1'], w_m2=cfg['w_m2'], w_m3=cfg['w_m3'])
    opt = Optimizer()
    print(f'[{name}] N={opt.N} R={opt.R} weights={kw}', flush=True)

    init = (opt.official_big.copy() if cfg['init'] == 'official'
            else np.load(cfg['init']))
    _, d = opt.score(init, detail=True)
    print(f'[{name}] init: M1={d["M1"]} C15={d["C1500"]} M2={d["M2"]} M3={d["M3"]}', flush=True)

    t0 = time.time()
    big = init
    best = None
    for i, (steps, t0_, t1_) in enumerate(cfg['phases']):
        best, big = sa(opt, big=big, steps=steps, t0=t0_, t1=t1_,
                       seed=cfg['seed'] + i, log_every=20000, **kw)
        _, d = opt.score(big, detail=True, **kw)
        print(f'[{name}] phase{i+1} done ({time.time()-t0:.0f}s): '
              f'M1={d["M1"]} C15={d["C1500"]} M2={d["M2"]} M3={d["M3"]}', flush=True)

    best, big = polish(opt, big, rounds=10, **kw)
    _, d = opt.score(big, detail=True, **kw)
    print(f'[{name}] FINAL({kw}): M1={d["M1"]} C15={d["C1500"]} M2={d["M2"]} M3={d["M3"]}', flush=True)
    np.save(f'{BASE}/processed/big_{name}.npy', big)
    print(f'[{name}] saved big_{name}.npy ({time.time()-t0:.0f}s)', flush=True)


if __name__ == '__main__':
    main()
