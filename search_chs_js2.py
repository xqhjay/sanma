import re

js = open('/tmp/chs.js', encoding='utf-8', errors='ignore').read()

print("=== String.fromCharCode / fromCodePoint 上下文:")
for m in re.finditer(r'.{60}fromCharCode(?:Point)?\(.{80}', js):
    print(' ', m.group(0).replace('\n', ' '))
    print()

print("=== 0xE000/57344/59136 相关:")
for pat in [r'.{60}0xE0[0-9A-Fa-f]{2}.{60}', r'.{60}57344.{60}', r'.{60}59136.{60}', r'.{50}0xE[0-9A-Fa-f]00.{50}']:
    for m in re.finditer(pat, js):
        s = m.group(0).replace('\n', ' ')
        print(' ', s)

print()
print("=== roots2pua 处理逻辑:")
idx = js.find('roots2pua')
while idx != -1 and idx < len(js):
    print(js[max(0,idx-200):idx+300].replace('\n', ' '))
    print('---')
    idx = js.find('roots2pua', idx+1)
    if idx > 200000 and js.count('roots2pua') > 10: break
