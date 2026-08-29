// 字劫(chs.hertz.ltd)性能评测复刻 — 用于奕码优化前后对比
// 用法: node eval_chs.js <码表文件> [--simple <简码表文件>]
// 输出 JSON 指标到 stdout
const fs = require('fs');
const engine = require('/tmp/chs_eval_engine.js');
const { cv, Te, Yt, EN, ir, Ir, Ro, Mm } = engine;

function loadFreq(path) {
  // kc6000.txt: 字\t频 (含词组, 只取单字)
  const freq = new Map();
  for (const line of fs.readFileSync(path, 'utf-8').split('\n')) {
    const p = line.split('\t');
    if (p.length >= 2 && p[0].length === 1) {
      const n = parseInt(p[1]);
      if (!isNaN(n)) freq.set(p[0], n);
    }
  }
  return freq;
}

function loadTable(path) {
  // 码表: 字\t码 (一字可多行) -> Map char -> [codes]
  const map = new Map();
  for (const line of fs.readFileSync(path, 'utf-8').split('\n')) {
    const t = line.replace(/\r$/, '');
    if (!t || t.startsWith('#')) continue;
    const p = t.split('\t');
    if (p.length >= 2 && p[0].length === 1 && /^[a-z]+$/i.test(p[1])) {
      if (!map.has(p[0])) map.set(p[0], []);
      map.get(p[0]).push(p[1].toLowerCase());
    }
  }
  return map;
}

function buildCodeToChars(tablePath) {
  // 按文件行序: code -> [chars] (与官网 Dm 解析器的 codeToChars 一致)
  const map = new Map();
  for (const line of fs.readFileSync(tablePath, 'utf-8').split('\n')) {
    const t = line.replace(/\r$/, '');
    if (!t || t.startsWith('#')) continue;
    const p = t.split(/[\t\s]+/);
    if (p.length >= 2 && p[0].length >= 1 && /^[a-z]+$/i.test(p[1])) {
      const code = p[1].toLowerCase().replace(/_/g, ' ');
      if (!map.has(code)) map.set(code, []);
      if (!map.get(code).includes(p[0])) map.get(code).push(p[0]);
    }
  }
  return map;
}

const args = process.argv.slice(2);
const tablePath = args[0];
const selKeys = process.env.SEL_KEYS || ";'456789";
const maxLen = parseInt(process.env.MAXLEN || '4');

const freq = loadFreq('/workspace/chs_data/kc6000.txt');
const table = loadTable(tablePath);
const codeToChars = buildCodeToChars(tablePath);

const result = cv(table, freq, selKeys, maxLen, undefined, codeToChars);
const lines = result.lines;

// 聚合函数(与官网渲染一致)
function agg(bucketLines, key) { return Yt(bucketLines, key); }
function cnt(bucketLines, key) { return Te(bucketLines, key).count; }
function wgt(bucketLines, key) { return Te(bucketLines, key).weight; }

const top1500 = EN(lines.slice(0, 3));   // 0-300, 300-500, 500-1500
const all = EN(lines);                    // 0-6000
const b1501_3000 = lines[3];
const top3000 = EN(lines.slice(0, 4));

const out = {
  file: tablePath,
  // 字数统计
  n_top1500: top1500.items.length,
  n_top6000: all.items.length,
  // 指标1: 前1500二码字总数
  cd2_count_top1500: cnt(top1500, 'cd2'),
  cd1_count_top1500: cnt(top1500, 'cd1'),
  cd3_count_top1500: cnt(top1500, 'cd3'),
  // 指标2: 前1500二码字加权比重(%)
  cd2_weight_top1500: top1500.totalFreq > 0 ? wgt(top1500, 'cd2') / top1500.totalFreq * 100 : 0,
  cd1_weight_top1500: top1500.totalFreq > 0 ? wgt(top1500, 'cd1') / top1500.totalFreq * 100 : 0,
  // 指标3: 1501~3000 出简重码数
  sc_count_1501_3000: cnt(b1501_3000, 'simpleCollision'),
  sc_count_top3000: cnt(top3000, 'simpleCollision'),
  // 指标4: 前6000出简重码总数
  sc_count_top6000: cnt(all, 'simpleCollision'),
  // 全码重
  fc_count_top6000: cnt(all, 'fullCollision'),
  // 指标5: 键魂键均当量 (前6000)
  ks_keyeq_top6000: agg(all, 'ksKeyEq'),
  ks_keyeq_top1500: agg(top1500, 'ksKeyEq'),
  // 指标6: 字均当量 (前6000)
  zi_eq_top6000: agg(all, 'ziEq'),
  zi_eq_top1500: agg(top1500, 'ziEq'),
  // 附加
  keyeq_top6000: agg(all, 'keyEq'),
  weighted_keylen_top6000: agg(all, 'cl'),
  brief2_count_top6000: cnt(all, 'brief2'),
  usage_balance: ir(all.usage),
};

// 明细到各桶
out.buckets = lines.map((b, i) => ({
  range: `${b.start + 1}~${b.end}`,
  totalFreq: b.totalFreq,
  cd1: cnt(b, 'cd1'), cd2: cnt(b, 'cd2'), cd3: cnt(b, 'cd3'),
  sc: cnt(b, 'simpleCollision'), fc: cnt(b, 'fullCollision'),
  ksKeyEq: agg(b, 'ksKeyEq'), ziEq: agg(b, 'ziEq'), keyEq: agg(b, 'keyEq'),
}));

console.log(JSON.stringify(out, null, 2));
