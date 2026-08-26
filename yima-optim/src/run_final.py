"""终极 SA: 以 mid 为起点, 针对 (高M1, M2=0, 低M3) 区域搜索."""
import sys
import time
import numpy as np

sys.path.insert(0, '/workspace/yima-optim/src')
from optimize2 import Optimizer, sa, polish

BASE = '/workspace/yima-optim/data'

opt = Optimizer()
init = np.load(f'{BASE}/processed/big_mid.npy')
kw = dict(w_m1=35.0, w_m2=600.0, w_m3=60.0)

_, d = opt.score(init, detail=True, **kw)
print(f'[final] init: M1={d["M1"]} C15={d["C1500"]} M2={d["M2"]} M3={d["M3"]}', flush=True)

t0 = time.time()
big = init
for i, (steps, t0_, t1_) in enumerate([(100000, 50.0, 0.6), (80000, 4.0, 0.1)]):
    best, big = sa(opt, big=big, steps=steps, t0=t0_, t1=t1_,
                   seed=51 + i, log_every=25000, **kw)
    _, d = opt.score(big, detail=True, **kw)
    print(f'[final] phase{i+1} ({time.time()-t0:.0f}s): M1={d["M1"]} C15={d["C1500"]} '
          f'M2={d["M2"]} M3={d["M3"]}', flush=True)

best, big = polish(opt, big, rounds=12, **kw)
_, d = opt.score(big, detail=True, **kw)
print(f'[final] FINAL: M1={d["M1"]} C15={d["C1500"]} M2={d["M2"]} M3={d["M3"]}', flush=True)
np.save(f'{BASE}/processed/big_final.npy', big)
print(f'[final] saved ({time.time()-t0:.0f}s)', flush=True)
