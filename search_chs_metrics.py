import re

js = open('/tmp/chs.js', encoding='utf-8', errors='ignore').read()

print("=== 指标名称相关字符串:")
for kw in ['出简', '重码', '当量', '键均', '字均', '二码字', '加权', '前1500', '1500', '6000', '简码']:
    positions = [m.start() for m in re.finditer(re.escape(kw), js)]
    print(f'{kw}: {len(positions)} 处')

# 提取 出简 上下文
print()
print("=== '出简' 上下文片段:")
seen = set()
for m in re.finditer(re.escape('出简'), js):
    s = js[max(0, m.start()-150):m.start()+150].replace('\n', ' ')
    key = s[100:180]
    if key not in seen:
        seen.add(key)
        print(' *', s)
        print()
