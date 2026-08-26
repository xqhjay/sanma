"""冲刺 SA: 以 mid 为起点, 推高 M2=0 下的 M1 上限."""
import sys
import time
import numpy as np

sys.path.insert(0, '/workspace/yima-optim/src')
from optimize2 import Optimizer, sa, polish

BASE = '/workspace/yima-optim/data'

opt = Optimizer()
init = np.load(f'{BASE}/processed/big_mid.npy')
kw = dict(w_m1=60.0, w_m2=3000.0, w_m3=50.0)

_, d = opt.score(init, detail=True, **kw)
print(f'[sprint] init: M1={d["M1"]} C15={d["C1500"]} M2={d["M2"]} M3={d["M3"]}', flush=True)

t0 = time.time()
big = init
for i, (steps, t0_, t1_) in enumerate([(80000, 40.0, 0.5), (50000, 3.0, 0.1)]):
    best, big = sa(opt, big=big, steps=steps, t0=t0_, t1=t1_,
                   seed=61 + i, log_every=25000, **kw)
    _, d = opt.score(big, detail=True, **kw)
    print(f'[sprint] phase{i+1} ({time.time()-t0:.0f}s): M1={d["M1"]} C15={d["C1500"]} '
          f'M2={d["M2"]} M3={d["M3"]}', flush=True)

best, big = polish(opt, big, rounds=10, **kw)
_, d = opt.score(big, detail=True, **kw)
print(f'[sprint] FINAL: M1={d["M1"]} C15={d["C1500"]} M2={d["M2"]} M3={d["M3"]}', flush=True)
np.save(f'{BASE}/processed/big_sprint.npy', big)
print(f'[sprint] saved ({time.time()-t0:.0f}s)', flush=True)
