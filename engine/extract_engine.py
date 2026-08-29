# -*- coding: utf-8 -*-
"""从 chs.js 中提取字劫拆分引擎 (bn/Tn/nb 类等) 供 Node.js 运行"""
import re

js = open('/tmp/chs.js', encoding='utf-8', errors='ignore').read()

# 1. ug 常量 (IDS 操作符)
i_ug = js.find('ug={')
ug_code = js[i_ug:js.find('}', i_ug)+1]

# 2. bn 类 + Tn 函数 (从 class bn 到 const Iy 前)
i_bn = js.find('class bn{')
i_mf = js.find('const Iy=')
bn_tn = js[i_bn:i_mf]

# 3. Iy 表 + Mf + Ao 函数
i_iy = js.find('const Iy=')
i_o = js.find('class _o{')
mf_ao = js[i_iy:i_o]

# 4. Gy/qy 函数
i_gy = js.find('function Gy(')
i_qy = js.find('function qy(')
gy = js[i_gy:i_qy]
m = re.search(r'function \w+\(', js[i_qy+10:])
qy = js[i_qy:i_qy+10+m.start()] if m else js[i_qy:i_qy+2000]

# 5. dg 函数
i_dg = js.find('function dg()')
m = re.search(r'function \w+\(', js[i_dg+15:])
dg = js[i_dg:i_dg+15+m.start()] if m else js[i_dg:i_dg+500]

# 6. Ti 函数 + nb 类 (Ti 紧贴 nb 之前)
i_ti = js.find('function Ti(')
i_nb = js.find('class nb{')
ti = js[i_ti:i_nb]

# 7. nb 类: 从 class nb 到 'let Pu=new Map'
i_pu = js.find('let Pu=new Map')
nb_class = js[i_nb:i_pu]

out = f'''// 提取自 chs.hertz.ltd 的拆分引擎 (自动提取生成)
// localStorage shim
const _store = new Map();
const localStorage = {{
  getItem: (k) => _store.has(k) ? _store.get(k) : null,
  setItem: (k, v) => _store.set(k, String(v)),
  removeItem: (k) => _store.delete(k),
}};

{ug_code}

{bn_tn}

{mf_ao}

{gy}

{qy}

{dg}

{ti}

{nb_class}

module.exports = {{ bn, Tn, Ti, nb, ug }};
'''
open('/workspace/engine/split_engine.js', 'w', encoding='utf-8').write(out)
print('written /workspace/engine/split_engine.js, nb len:', len(nb_class))
