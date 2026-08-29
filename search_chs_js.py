import re

js = open('/tmp/chs.js', encoding='utf-8', errors='ignore').read()

# 搜索 fetch/axios 数据文件引用
print("=== 数据文件引用:")
for m in re.finditer(r'["\'`]([^"\'`\s]*\.(?:txt|json|yaml|tsv|csv|gz|bin|dat|woff2?))["\'`]', js):
    print(' ', m.group(1))

print()
print("=== fetch(url 模式:")
for m in re.finditer(r'fetch\(\s*[`"\']([^`"\']+)[`"\']', js):
    print(' ', m.group(1))

print()
print("=== 包含 pua 的字符串片段:")
for m in re.finditer(r'["\'`]([^"\'`]{0,60}[pP][uU][aA][^"\'`]{0,60})["\'`]', js):
    print(' ', m.group(1))
