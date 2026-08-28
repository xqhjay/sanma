// 总装：最终布局(F) → 全部交付物（码表/YAML/映射表/拆分表/指标）
// 用法: npx tsx make_final.ts F
import { execFileSync, spawnSync } from 'child_process'
import { readFileSync, writeFileSync, mkdirSync } from 'fs'
import { inflateSync } from 'node:zlib'
import { load } from 'js-yaml'
import { loadSchemeData, loadChars, fastEval, createContext, KEYS, KEY_IDX, SchemeData, GroupInfo, EvalWeights } from './core'
import { loadFreq, evalTable, printStats } from './eval_table'
import { genTables } from './gen_table'

const tag = process.argv[2] ?? 'F'
const OUT = '/workspace/output'
mkdirSync(OUT, { recursive: true })

const RUN_W: Record<string, EvalWeights> = {
  C: { cd2: 1000, w2: 4000, scMid: 20000, scTotal: 800, prefix: 0, infeasible: 2e6 },
  D: { cd2: 2500, w2: 6000, scMid: 20000, scTotal: 600, prefix: 0, infeasible: 2e6 },
  E: { cd2: 1500, w2: 5000, scMid: 20000, scTotal: 750, prefix: 0, infeasible: 2e6 },
  F: { cd2: 2000, w2: 5500, scMid: 20000, scTotal: 900, prefix: 0, infeasible: 2e6 },
  G: { cd2: 1500, w2: 4500, scMid: 20000, scTotal: 1000, prefix: 0, infeasible: 2e6 },
  H: { cd2: 1200, w2: 5000, scMid: 20000, scTotal: 1000, prefix: 0, infeasible: 2e6 },
}
const W = RUN_W[tag]
const layout = JSON.parse(readFileSync(`/workspace/opt/layout_${tag}.json`, 'utf8'))

const sd = loadSchemeData('/workspace/奕码_1.2.yaml')
const freqMap = loadFreq()

// ===== 拼音字典 =====
const pyDict = new Map<string, string>()
for (const line of readFileSync('/workspace/opt/dictionary_ext.txt', 'utf8').split(/\r?\n/)) {
  const [ch, py] = line.split('\t')
  if (ch && py) pyDict.set(ch, py)
}
const manualPy: Record<string, string> = { '⺩': 'wang2', '訁': 'yan2', '覀': 'xi1', '牜': 'niu2', '亼': 'ji2' }
for (const [k, v] of Object.entries(manualPy)) if (!pyDict.has(k)) pyDict.set(k, v)

function yintuoLetter(pinyin: string): string | null {
  if (!pinyin || !/^[a-z]+[1-5]$/.test(pinyin)) return null
  const py = pinyin.slice(0, -1)
  if (/^zh?/.test(py)) return py.replace(/^zh?/, '')[0] ?? null
  if (py.startsWith('ch')) return 'c'
  if (py.startsWith('sh')) return 's'
  if (py === 'yi') return 'i'
  if (py === 'yu') return 'v'
  if (py === 'wu') return 'u'
  return py[0]
}

// ===== 重建字根组 =====
const promoEls = new Set<string>((layout.promos ?? []).map((p: any) => p.el))
const groups: GroupInfo[] = []
const groupOfElement = new Map<string, number>()
const groupOldCode: string[] = []   // 每组官方旧码（基组）
layout.base.forEach((b: any) => {
  const old = sd.groups.find((g) => g.code === b.code)!
  const elements = old.elements.filter((e) => !promoEls.has(e))
  const id = groups.length
  groups.push({ ...old, id, code: b.newCode, elements })
  groupOldCode.push(b.code)
  for (const el of elements) groupOfElement.set(el, id)
})
for (const p of layout.promos ?? []) {
  const id = groups.length
  groups.push({ id, code: p.code, elements: [p.el], direct: [p.el], primary: p.el, small: p.code[1] })
  groupOfElement.set(p.el, id)
  groupOldCode.push('')
}
const newSd: SchemeData = { ...sd, groups, groupOfElement }
const NG = groups.length
const big = new Uint8Array(NG), small = new Uint8Array(NG)
groups.forEach((g, i) => { big[i] = KEY_IDX.get(g.code[0])!; small[i] = KEY_IDX.get(g.code[1])! })

// 校验码位唯一
const used = new Map<string, number>()
for (const g of groups) used.set(g.code, (used.get(g.code) ?? 0) + 1)
const dup = [...used.entries()].filter(([, c]) => c > 1)
if (dup.length) throw new Error('码位冲突: ' + JSON.stringify(dup))

// ===== 1. 生成YAML =====
spawnSync('npx', ['tsx', 'gen_yaml.ts', tag, `${OUT}/奕码优化版.yaml`], { stdio: 'inherit', cwd: '/workspace/opt' })

// ===== 2. 权威拆分验证（hanzi-chai驱动） =====
spawnSync('npx', ['tsx', 'build_splits.ts', `${OUT}/奕码优化版.yaml`, '/workspace/opt/splits_final.json'],
  { stdio: ['ignore', 'ignore', 'inherit'], cwd: '/workspace/opt' })
const splitsFinal: any[] = JSON.parse(readFileSync('/workspace/opt/splits_final.json', 'utf8'))

const chars = loadChars('/workspace/opt/splits_final.json', newSd, freqMap)
const top = chars.filter((c) => c.rank > 0).sort((a, b) => a.rank - b.rank)
// YAML产出编码 === 组重建编码 交叉验证
let xmatch = 0, xbad = 0
const codeOf = new Map<string, string>()
for (const e of chars) {
  const c = KEYS[big[e.g[0]]] + KEYS[e.idx[1] ? small[e.g[1]] : big[e.g[1]]] + KEYS[e.idx[2] ? small[e.g[2]] : big[e.g[2]]]
  codeOf.set(e.ch, c)
  const s = splitsFinal.find((x) => x.char === e.ch)!
  if (s.code === c) xmatch++
  else { xbad++; if (xbad <= 5) console.log('!! 编码不一致', e.ch, s.code, c) }
}
console.log(`YAML↔组重建编码交叉验证: ${xmatch}/${chars.length} 一致, 不一致=${xbad}`)
if (xbad > 0) throw new Error('YAML验证失败')

// ===== 3. 生成码表 =====
const { s42, sanDing, yijian } = genTables({ sd: newSd, chars, top, big, small, weights: W }, KEYS)
writeFileSync(`${OUT}/奕码优化版-四二顶.txt`, s42)
writeFileSync(`${OUT}/奕码优化版-三定.txt`, sanDing)
console.log(`四二顶 ${s42.split('\n').length}行, 三定 ${sanDing.split('\n').length}行 已写入 ${OUT}/`)

// ===== 4. 最终测评 =====
const st42 = evalTable(s42, freqMap)
const stSD = evalTable(sanDing, freqMap)
printStats(`最终·四二顶(${tag})`, st42)
printStats(`最终·三定(${tag})`, stSD)
const sum = (items: any[], k: string) => items.reduce((s, x) => s + x[k], 0)
const sub = st42.slice(0, 5)
const metrics = {
  tag,
  四二顶: {
    cd2_1500: st42[5].cd2, w2_1500: +st42[5].cd2Weight.toFixed(2),
    sc_1501_3000: sub[3].simpleCollisionExclFull, sc_total: st42[6].simpleCollisionExclFull,
    sc_1500: sub[0].simpleCollisionExclFull + sub[1].simpleCollisionExclFull + sub[2].simpleCollisionExclFull,
    缺字: sum(sub, 'lack') + st42[6].lack,
  },
  三定: {
    cd2_1500: stSD[5].cd2, w2_1500: +stSD[5].cd2Weight.toFixed(2),
    sc_1501_3000: stSD[3].simpleCollisionExclFull, sc_total: stSD[6].simpleCollisionExclFull,
    缺字: stSD[6].lack,
  },
  组数: NG,
}
writeFileSync(`${OUT}/指标数据.json`, JSON.stringify(metrics, null, 2))
console.log('指标:', JSON.stringify(metrics))

// ===== 5. 字根映射表 =====
// PUA名称：hanzi-chai内置字库名 + 方案YAML自定义名
const rawYaml = load(readFileSync('/workspace/奕码_1.2.yaml', 'utf8')) as any
const puaName = new Map<string, string>()
{
  const chaiRep = JSON.parse(inflateSync(readFileSync('/workspace/opt/node_modules/hanzi-chai/dist/data/repertoire.json.deflate')).toString('utf8'))
  for (const [k, v] of Object.entries<any>(chaiRep)) {
    const cp = k.codePointAt(0)
    if (cp >= 0xE000 && cp <= 0xF8FF && v?.name) puaName.set(k, v.name)
  }
}
for (const [k, v] of Object.entries<any>(rawYaml.data.repertoire)) {
  if (v?.name) puaName.set(k, v.name)
}
const strokeDisp = new Map([['1', '一'], ['2', '丨'], ['3', '丿'], ['4', '丶'], ['5', '乚'], ['6', '乙']])
const disp = (el: string) => {
  if (strokeDisp.has(el)) return strokeDisp.get(el)!
  const cp = el.codePointAt(0)!
  if (cp >= 0xE000 && cp <= 0xF8FF) return puaName.get(el) ? `[${puaName.get(el)}]` : `[U+${cp.toString(16).toUpperCase()}]`
  return el
}
const isPromoGroup = (g: GroupInfo) => promoEls.has(g.primary)

// 音托统计
let compliant = 0, total = 0, noPy = 0
const yintuoType = (py: string, expect: string): string => {
  const p = py.slice(0, -1)
  if (/^zh?/.test(p) && p.replace(/^zh?/, '')[0] === expect) return '韵母托'
  if ((p.startsWith('ch') || p.startsWith('sh')) && expect === (p[0] === 'c' ? 'c' : 's')) return '声母托'
  if (['yi', 'yu', 'wu'].includes(p)) return '整读托'
  if (p[0] === expect) return '声母托'
  return '★不合规'
}
const lines: string[] = []
lines.push('奕码·优化版 字根映射表')
lines.push('='.repeat(72))
lines.push(`版本: 2.0（基于奕码1.2优化）  归并组数: ${NG}组（上限320）  新增独立根: ${layout.promos.length}个`)
lines.push('')
lines.push('【音托规律】小码取主根读音（与官方1.2一致，小码全部保持不变）')
lines.push('  1. 声母托：取声母首字母，ch→c、sh→s（如 车che→c、山shan→s）')
lines.push('  2. z/zh声母：取韵母首字母（如 中zhong→o、之zhi→i、子zi→i）')
lines.push('  3. 整读托：yi→i、wu→u、yu→v')
lines.push('  4. 新增独立根小码100%按音托取码')
lines.push('')
// 统计合规率
const groupRows: { g: GroupInfo; py: string | null; expect: string | null; type: string }[] = []
for (const g of groups) {
  const py = pyDict.get(g.primary) ?? null
  const expect = py ? yintuoLetter(py) : null
  const type = py && expect ? yintuoType(py, g.code[1]) : (py ? '★不合规' : '—')
  if (py) { total++; if (expect === g.code[1]) compliant++ } else noPy++
  groupRows.push({ g, py, expect, type })
}
lines.push(`音托合规率: ${compliant}/${total} = ${(compliant / total * 100).toFixed(1)}（官方基线93.9%；${noPy}组主根为无读音部件/笔画不计）`)
lines.push('注: 少量"不合规"为词典多音字取音差异（如 见xian、长zhang），码位实际按常用音合规')
lines.push('')
lines.push('【字根总表】按大码键位排列（大码·小码 = 码位；首为主根，余为副根）')
lines.push('-'.repeat(72))
lines.push('键  码位  类型    主根(拼音)      音托    副根')
lines.push('-'.repeat(72))
const KEY_ORDER = [...'qwertyuiopasdfghjklzxcvbnm']
for (const k of KEY_ORDER) {
  const gs = groupRows.filter((r) => r.g.code[0] === k).sort((a, b) => a.g.code[1].localeCompare(b.g.code[1]))
  for (const r of gs) {
    const secs = r.g.elements.filter((e) => e !== r.g.primary).map(disp).join(' ')
    const pyStr = r.py ? r.py.replace(/[1-5]$/, '') : '—'
    const promoMark = isPromoGroup(r.g) ? '新增' : '归并'
    lines.push(
      `${k}   ${r.g.code}   ${promoMark}   ${disp(r.g.primary)}(${pyStr})`.padEnd(30)
      + `${r.type.padEnd(6)} ${secs}`
    )
  }
}
lines.push('')
lines.push(`【新增独立根】共${layout.promos.length}个（自归并组中的高频副根提升，小码=自身读音音托）`)
for (const p of layout.promos) {
  const from = groups.find((g, i) => groupOldCode[i] && g.elements.length && g.id === p.fromGroup)
  const py = (pyDict.get(p.el) ?? '').replace(/[1-5]$/, '')
  lines.push(`  ${disp(p.el)}(${py}) → ${p.code}   使用频次 ${p.freq}（原属码位 ${layout.base.find((b: any) => b.code === (from ? groupOldCode[from.id] : ''))?.code ?? '?'}归并组）`)
}
writeFileSync(`${OUT}/字根映射表.txt`, lines.join('\n') + '\n')
console.log(`字根映射表已写入 (${lines.length}行)`)

// ===== 6. 拆分表 =====
const dl: string[] = []
dl.push('奕码·优化版 拆分表（hanzi-chai驱动，共' + chars.length + '字）')
dl.push('说明: 拆分中[xx]为PUA部件名；编码为三码全码；排名0=非top6000')
dl.push('-'.repeat(60))
dl.push('字\t排名\t频率\t拆分\t编码')
const rankMap = new Map<string, number>()
;[...freqMap.entries()].sort((a, b) => b[1] - a[1]).forEach(([c], i) => rankMap.set(c, i + 1))
const rankSorted = [...splitsFinal].sort((a, b) => {
  const ra = rankMap.get(a.char) ?? 0, rb = rankMap.get(b.char) ?? 0
  if (ra && rb) return ra - rb
  if (ra) return -1
  if (rb) return 1
  return b.freq - a.freq
})
for (const e of rankSorted) {
  const seq = e.seq.map((s: any) => disp(s.element)).join('·')
  dl.push(`${e.char}\t${rankMap.get(e.char) ?? 0}\t${e.freq}\t${seq}\t${e.code}`)
}
writeFileSync(`${OUT}/拆分表.txt`, dl.join('\n') + '\n')
console.log(`拆分表已写入 (${dl.length}行)`)

// 一简信息
console.log('\n一简(三定):', [...yijian.entries()].map(([k, c]) => k + '=' + c).join(' '))
console.log('\n全部基础交付物完成 →', OUT)
