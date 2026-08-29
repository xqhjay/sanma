import re

js = open('/tmp/chs.js', encoding='utf-8', errors='ignore').read()

# 找到 const de={char:V,freq:N,code:R,... 的完整函数
idx = js.find('simpleCollisionExclFull:oe,fullCollision:re')
if idx > 0:
    # 向前找函数开头
    start = js.rfind('function', 0, idx)
    # 也找更前面的上下文
    seg = js[max(0, idx-3500):idx+1500]
    print(seg)
