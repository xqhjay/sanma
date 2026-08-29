import re

js = open('/tmp/chs.js', encoding='utf-8', errors='ignore').read()

# 找 Ro, Ir, vh, UN, uv, Mm, ai 的定义
for name in ['function Ro', 'function Ir', 'function vh', 'function UN', 'function uv', 'function Mm', 'const ai', 'var ai', 'let ai']:
    idx = js.find(name)
    if idx >= 0:
        print(f'=== {name} @ {idx}:')
        print(js[idx:idx+1800])
        print()
        print('------')
