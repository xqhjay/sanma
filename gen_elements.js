// 奕码拆分+编码管线：从 YAML 字根集 + sky_ids 生成每个字的元素序列
// 用法: node gen_elements.js <yaml路径> [--out elements.yaml] [--table 参考码表]
const fs = require('fs');
const path = require('path');
const { bn, Tn, Ti, nb, ug } = require('/workspace/engine/split_engine.js');

// ---------- ka: 编码字符串 -> {main, sub, supplement} ----------
function ka(code) {
  // 网站引擎缺失的 ka 函数: 拆分编码字符串
  return { main: code[0] || '', sub: code[1] || '', supplement: code[2] || '' };
}

// ---------- YAML 解析 ----------
function parseYaml(text) {
  // 用简单方式调用 python 保证 YAML 解析正确? 不, 直接内嵌 js-yaml
  // 优先使用全局 js-yaml (若安装), 否则调用 python 预转换
  try {
    const yaml = require('/workspace/node_modules/js-yaml');
    return yaml.load(text);
  } catch (e) {
    const { execSync } = require('child_process');
    const tmp = '/tmp/_yaml_in.yaml';
    fs.writeFileSync(tmp, text);
    const json = execSync(`python3 -c "import yaml,json,sys; print(json.dumps(yaml.safe_load(open('${tmp}',encoding='utf-8')),ensure_ascii=False))"`).toString();
    return JSON.parse(json);
  }
}

// ---------- 从 YAML mapping 提取字根编码 ----------
function resolveCode(v, mapping, depth = 0) {
  if (depth > 10) return null;
  if (typeof v === 'string') {
    if (v.length === 2) return [v[0], v[1]];
    if (v.length === 1) return [v, null];
    return null;
  }
  if (v && typeof v === 'object' && !Array.isArray(v)) {
    if (v.element === undefined) return null;
    const base = resolveCode(mapping[v.element], mapping, depth + 1);
    if (!base) return null;
    if (v.index === 0) return [base[0], null];
    if (v.index === 1) return [null, base[1]];
    return base;
  }
  if (Array.isArray(v) && v.length === 2) {
    let da = null, db = null;
    const x = v[0], y = v[1];
    if (typeof x === 'string' && x.length >= 1) da = x[0];
    else { const r = resolveCode(x, mapping, depth + 1); if (!r) return null; da = r[0] ?? r[1]; }
    if (typeof y === 'string' && y.length >= 1) db = y[0];
    else { const r = resolveCode(y, mapping, depth + 1); if (!r) return null; db = r[1] ?? r[0]; }
    if (da && db) return [da, db];
    return null;
  }
  return null;
}

function extractRoots(yaml) {
  const mapping = yaml.form.mapping;
  const codes = new Map(); // element -> [大码, 小码]
  for (const [k, v] of Object.entries(mapping)) {
    if (k.startsWith('首字母') || k.startsWith('末字母')) continue;
    const r = resolveCode(v, mapping);
    if (r && r[0] && r[1]) codes.set(k, r);
  }
  return codes;
}

// ---------- Transformer 实现 ----------
function patternToNode(spec) {
  if (typeof spec === 'string') return { type: 'char', ch: spec };
  if (spec.id !== undefined) return { type: 'var', id: spec.id };
  return { type: 'op', op: spec.operator, children: spec.operandList.map(patternToNode) };
}

function matchPattern(pattern, node, captures) {
  if (pattern.type === 'var') {
    const prev = captures.get(pattern.id);
    if (prev !== undefined) {
      // 同一变量需匹配相同子树
      return prev.toIDS() === node.toIDS();
    }
    captures.set(pattern.id, node);
    return true;
  }
  if (pattern.type === 'char') {
    return node.isLeaf() && node.char === pattern.ch;
  }
  if (pattern.type === 'op') {
    if (node.isLeaf() || node.op !== pattern.op) return false;
    if (node.children.length !== pattern.children.length) return false;
    for (let i = 0; i < pattern.children.length; i++) {
      if (!matchPattern(pattern.children[i], node.children[i], captures)) return false;
    }
    return true;
  }
  return false;
}

function buildToNode(spec, captures) {
  if (typeof spec === 'string') return new bn(spec);
  if (spec.id !== undefined) {
    const c = captures.get(spec.id);
    if (!c) return new bn('\uFFFD');
    return c;
  }
  const children = spec.operandList.map(s => buildToNode(s, captures));
  return new bn(null, spec.operator, children);
}

class Transformer {
  constructor(rules) {
    this.rules = rules.map(r => ({ from: patternToNode(r.from), to: r.to }));
    this._listeners = [];
  }
  onRulesChange(fn) { this._listeners.push(fn); }
  getRules() { return this.rules.map(r => ({ from: r.from, to: r.to })); }
  getNamedRoots() {
    const s = new Set();
    for (const r of this.rules) this._collectChars(r.to, s);
    return [...s];
  }
  _collectChars(spec, s) {
    if (typeof spec === 'string') { s.add(spec); return; }
    if (spec.id !== undefined) return;
    for (const c of spec.operandList) this._collectChars(c, s);
  }
  transformNode(node) {
    // 自底向上: 先变换子节点, 再检查当前节点
    if (!node.isLeaf()) {
      node = new bn(null, node.op, node.children.map(c => this.transformNode(c)));
    }
    for (const rule of this.rules) {
      const captures = new Map();
      if (matchPattern(rule.from, node, captures)) {
        return buildToNode(rule.to, captures);
      }
    }
    return node;
  }
  transform(idsStr) {
    const tree = Tn(idsStr);
    if (!tree) return idsStr;
    const out = this.transformNode(tree);
    return out.toIDS();
  }
}

// ---------- 主流程 ----------
function main() {
  const args = process.argv.slice(2);
  const yamlPath = args[0];
  const yaml = parseYaml(fs.readFileSync(yamlPath, 'utf-8'));
  const rootCodes = extractRoots(yaml);

  // 1. 引擎数据加载
  const data = new nb();
  // {name} -> PUA 预处理 (sky_ids 的 {名字根} 转为 PUA 字符)
  let idsText = fs.readFileSync('/workspace/chs_data/sky_ids.txt', 'utf-8');
  const r2p = JSON.parse(fs.readFileSync('/workspace/data_roots2pua.json', 'utf-8'));
  // {X} 若 X 本身是普通字根 (如 {巴}) 则去括号
  idsText = idsText.replace(/\{[^}]+\}/g, (m) => {
    if (r2p[m] !== undefined) return r2p[m];
    const inner = m.slice(1, -1);
    if (rootCodes.has(inner)) return inner;
    return m; // 保留未知 token
  });
  data.loadSkyIDS(idsText);
  data.loadStrokes(fs.readFileSync('/workspace/chs_data/stroke.txt', 'utf-8'));
  data.loadFreq(fs.readFileSync('/workspace/chs_data/kc6000.txt', 'utf-8'));
  data.loadDict(fs.readFileSync('/workspace/chs_data/dictionary.txt', 'utf-8'));

  // 2. glyph_customization: 覆盖拆分树
  const gc = yaml.data.glyph_customization || {};
  for (const [ch, g] of Object.entries(gc)) {
    const glyphs = Array.isArray(g) ? g : [g];
    // 取第一个 Compound/SplicedComponent 类型的字形
    let ids = null;
    for (const gl of glyphs) {
      if (gl.type === 'compound' || gl.type === 'spliced_component') {
        ids = gl.operator + gl.operandList.join('');
        break;
      }
    }
    if (ids) data.decomp.set(ch, ids);
  }
  // PUA 字库字形也覆盖 (repertoire 中定义的复合字形)
  const rep = yaml.data.repertoire || {};
  for (const [ch, info] of Object.entries(rep)) {
    for (const gl of (info.glyphs || [])) {
      if (gl.type === 'compound' || gl.type === 'spliced_component') {
        data.decomp.set(ch, gl.operator + gl.operandList.join(''));
        break;
      }
    }
  }
  data._cache.clear();

  // 3. transformer
  if (yaml.data.transformers && yaml.data.transformers.length > 0) {
    const tr = new Transformer(yaml.data.transformers);
    data.setTransformer(tr);
  }

  // 4. analysis.customize: 显式拆分
  const customize = (yaml.analysis && yaml.analysis.customize) || {};
  for (const [ch, seq] of Object.entries(customize)) {
    if (!seq || seq.length === 0) continue;
    let ids;
    if (seq.length === 1) ids = seq[0];
    else if (seq.length === 2) ids = '⿰' + seq[0] + seq[1];
    else ids = '⿳' + seq[0] + seq[1] + seq.slice(2).join('');
    data.decomp.set(ch, ids);
  }
  data._cache.clear();

  // 5. 设置字根集与字根编码
  const rootCodeMap = {};
  for (const [el, [a, b]] of rootCodes) rootCodeMap[el] = a + b;
  data.setRootCodes(rootCodeMap);
  data.setRoots([...rootCodes.keys()]);

  // 6. 编码器规则 (从 YAML sources/conditions 解释执行)
  function encode(leaves) {
    // 返回元素序列 [(element, index)]
    if (leaves.length === 0) return null;
    const c2 = leaves.length >= 2;
    if (!c2) {
      return [[leaves[0], 0], [leaves[0], 1], [leaves[0], 1]];
    }
    const c3 = leaves.length >= 3;
    if (!c3) {
      return [[leaves[0], 0], [leaves[1], 0], [leaves[1], 1]];
    }
    return [[leaves[0], 0], [leaves[1], 0], [leaves[leaves.length - 1], 0]];
  }

  // 7. 对参考码表中的所有字计算
  const tablePath = args.find(a => a.startsWith('--table='))?.slice(8) || '/workspace/奕码四二顶-官方最新修正版-1.2.txt';
  const tableChars = [];
  const official = new Map();
  for (const line of fs.readFileSync(tablePath, 'utf-8').split('\n')) {
    const t = line.replace(/\r$/, '');
    if (!t) continue;
    const p = t.split('\t');
    if (p.length >= 2 && p[0].length >= 1) {
      if (!official.has(p[0])) { official.set(p[0], p[1]); if (p[1].length === 3) tableChars.push(p[0]); }
      else if (p[1].length === 3 && official.get(p[0]).length !== 3) official.set(p[0], p[1]);
    }
  }

  let match = 0, mismatch = 0, fail = 0;
  const mismatches = [];
  const freqMap = new Map();
  for (const line of fs.readFileSync('/workspace/chs_data/kc6000.txt', 'utf-8').split('\n')) {
    const p = line.split('\t');
    if (p.length >= 2 && p[0].length === 1) freqMap.set(p[0], parseInt(p[1]) || 0);
  }
  const elements = [];
  for (const ch of tableChars) {
    const freq = freqMap.get(ch) || 0;
    let leaves = [];
    try { leaves = data.decompose(ch).leaves; } catch (e) { leaves = []; }
    // 所有叶子必须是字根
    const allRoots = leaves.every(l => rootCodes.has(l));
    const seq = allRoots ? encode(leaves) : null;
    if (!seq) { fail++; if (mismatches.length < 30) mismatches.push([ch, 'FAIL', leaves.join(''), official.get(ch)]); continue; }
    const code = seq.map(([el, idx]) => {
      const rc = rootCodes.get(el);
      return idx === 0 ? rc[0] : rc[1];
    }).join('');
    if (code === official.get(ch)) match++;
    else { mismatch++; if (mismatches.length < 30) mismatches.push([ch, code, leaves.join(' '), official.get(ch)]); }
    elements.push({ ch, leaves, seq, code, freq });
  }
  console.log(`字数: ${tableChars.length}, 匹配: ${match}, 不匹配: ${mismatch}, 失败: ${fail}`);
  console.log('匹配率:', (match / tableChars.length * 100).toFixed(2) + '%');
  if (mismatches.length) console.log('样例(字, 生成码, 拆分, 官方码):');
  for (const m of mismatches.slice(0, 25)) console.log(' ', m.join(' | '));

  // 8. 输出 elements.yaml (供 chai 使用)
  const outIdx = args.indexOf('--out');
  if (outIdx >= 0 && args[outIdx + 1]) {
    const lines = ['# 奕码元素序列表 (自动生成)'];
    const sorted = [...elements].sort((a, b) => b.freq - a.freq);
    for (const e of sorted) {
      lines.push(`- 词: "${e.ch}"`);
      lines.push(`  频率: ${e.freq}`);
      lines.push('  元素序列:');
      for (const [el, idx] of e.seq) {
        lines.push(`    - {element: "${el}", index: ${idx}}`);
      }
    }
    fs.writeFileSync(args[outIdx + 1], lines.join('\n'), 'utf-8');
    console.log('已输出', args[outIdx + 1], '共', elements.length, '字');
  }

  // 同时输出拆分表 (拆分表交付物)
  const outSplit = args.indexOf('--splits');
  if (outSplit >= 0 && args[outSplit + 1]) {
    const lines = [];
    const sorted = [...elements].sort((a, b) => b.freq - a.freq);
    for (const e of sorted) lines.push(`${e.ch}\t${e.leaves.join(' ')}\t${e.code}`);
    fs.writeFileSync(args[outSplit + 1], lines.join('\n'), 'utf-8');
    console.log('已输出拆分表', args[outSplit + 1]);
  }
}

main();
