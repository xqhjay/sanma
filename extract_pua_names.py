import os, json, glob
import xml.etree.ElementTree as ET

ufo = '/workspace/chai-font/sources/masters/ChaiSans-Regular.ufo/glyphs'
pua2name = {}
name2pua = {}
for fn in os.listdir(ufo):
    if not fn.endswith('.glif'):
        continue
    tree = ET.parse(os.path.join(ufo, fn))
    root = tree.getroot()
    gname = root.attrib.get('name', '')
    for uni in root.findall('unicode'):
        hexv = uni.attrib['hex'].upper()
        cp = int(hexv, 16)
        pua2name[cp] = gname
        name2pua.setdefault(gname, []).append(cp)

print('总字形数:', len(pua2name))

# 与奕码yaml对照
import yaml
d = yaml.safe_load(open('/workspace/sanma/奕码_1.2.yaml', encoding='utf-8'))
m = d['form']['mapping']
yaml_puas = set()
for k in m:
    for ch in k:
        if 0xE000 <= ord(ch) <= 0xF8FF:
            yaml_puas.add(ord(ch))
print('yaml PUA数:', len(yaml_puas))
resolved = yaml_puas & set(pua2name)
unresolved = yaml_puas - set(pua2name)
print('字体可解析:', len(resolved), '无法解析:', len(unresolved))
for cp in sorted(unresolved):
    print(f'  U+{cp:04X}')

# 输出解析样例
print()
print('=== yaml中PUA根的名称样例:')
main_roots = {k: v for k, v in m.items() if isinstance(v, str)}
for k, v in sorted(main_roots.items()):
    if k and 0xE000 <= ord(k[0]) <= 0xF8FF:
        cp = ord(k[0])
        nm = pua2name.get(cp, '???')
        print(f'U+{cp:04X} {nm} -> {v}')

json.dump({f'U+{k:04X}': v for k, v in pua2name.items()},
          open('/workspace/data_pua2name.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
