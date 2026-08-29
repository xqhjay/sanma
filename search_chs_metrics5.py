import re

js = open('/tmp/chs.js', encoding='utf-8', errors='ignore').read()

# Extract the full cv function
idx = js.find('function cv(')
print('=== cv function (full):')
depth = 0
start = idx
i = idx
while i < len(js):
    if js[i] == '{':
        depth += 1
    elif js[i] == '}':
        depth -= 1
        if depth == 0:
            break
    i += 1
print(js[start:i+1])
