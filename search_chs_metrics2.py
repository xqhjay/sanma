import re

js = open('/tmp/chs.js', encoding='utf-8', errors='ignore').read()

# 找 simpleCollision 的计算
print("=== simpleCollision 出现处:")
for m in re.finditer(r'simpleCollision', js):
    s = js[max(0, m.start()-250):m.start()+250].replace('\n', ' ')
    print(' *', s)
    print()

print("=== brief2 出现处:")
for m in re.finditer(r'brief2', js):
    s = js[max(0, m.start()-200):m.start()+200].replace('\n', ' ')
    print(' *', s)
    print()
