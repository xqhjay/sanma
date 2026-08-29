import json

lines = open('/tmp/chs_roots2pua.txt', encoding='utf-8').read().split('\n')
mapping = {}
for line in lines:
    if not line.strip():
        continue
    # 格式: {名称}<tab或空格>PUA字符
    parts = line.split('\t') if '\t' in line else None
    if parts is None:
        # 按第一个空格分割
        idx = line.find(' ')
        if idx < 0: continue
        parts = [line[:idx], line[idx+1:].strip()]
    name = parts[0].strip()
    pua = parts[1].strip() if len(parts) > 1 else ''
    if name and pua:
        mapping[name] = pua

print('entries:', len(mapping))
for k, v in list(mapping.items())[:30]:
    print(json.dumps(k, ensure_ascii=False), '->', ' '.join(f'U+{ord(c):04X}' for c in v))

# 检查奕码yaml中的PUA是否都能解析
import yaml
d = yaml.safe_load(open('/workspace/sanma/奕码_1.2.yaml', encoding='utf-8'))
m = d['form']['mapping']
pua_in_yaml = set()
for k in m:
    for ch in k:
        if 0xE000 <= ord(ch) <= 0xF8FF:
            pua_in_yaml.add(ch)
print()
print('yaml中的PUA数:', len(pua_in_yaml))
resolved = set()
unresolved = []
for p in pua_in_yaml:
    found = False
    for name, pv in mapping.items():
        if p in pv:
            resolved.add(p); found = True; break
    if not found:
        unresolved.append(p)
print('已解析:', len(resolved), '未解析:', len(unresolved))
for p in unresolved[:30]:
    print(f'  U+{ord(p):04X}')

# 保存完整映射
with open('/workspace/data_roots2pua.json', 'w', encoding='utf-8') as f:
    json.dump(mapping, f, ensure_ascii=False, indent=1)
