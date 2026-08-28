// 端到端验证：SA布局(layout_X.json) → 重建字根组 → 生成码表 → 字劫真实测评
// 用法: npx tsx verify_opt.ts C   (验证 layout_C.json)
import { readFileSync, writeFileSync } from 'fs'
import { loadSchemeData, loadChars, fastEval, createContext, KEYS, KEY_IDX, SchemeData, GroupInfo, EvalWeights } from './core'
import { loadFreq, evalTable, printStats } from './eval_table'
import { genTables } from './gen_table'

const tag = process.argv[2] ?? 'C'
// 各SA run的权重（与启动env一致）
const RUN_W: Record<string, EvalWeights> = {
  A: { cd2: 1000, w2: 3000, scMid: 20000, scTotal: 1200, prefix: 0, infeasible: 2e6 },
  B: { cd2: 1000, w2: 3000, scMid: 20000, scTotal: 2500, prefix: 0, infeasible: 2e6 },
  C: { cd2: 1000, w2: 4000, scMid: 20000, scTotal: 800, prefix: 0, infeasible: 2e6 },
  D: { cd2: 2500, w2: 6000, scMid: 20000, scTotal: 600, prefix: 0, infeasible: 2e6 },
  E: { cd2: 1500, w2: 5000, scMid: 20000, scTotal: 750, prefix: 0, infeasible: 2e6 },
  F: { cd2: 2000, w2: 5500, scMid: 20000, scTotal: 900, prefix: 0, infeasible: 2e6 },
  G: { cd2: 1500, w2: 4500, scMid: 20000, scTotal: 1000, prefix: 0, infeasible: 2e6 },
  H: { cd2: 1200, w2: 5000, scMid: 20000, scTotal: 1000, prefix: 0, infeasible: 2e6 },
}
const W = RUN_W[tag]
const layout = JSON.parse(readFileSync(`/workspace/opt/layout${tag && tag !== 'official' ? '_' + tag : ''}.json`, 'utf8'))

const sd = loadSchemeData('/workspace/奕码_1.2.yaml')
const freqMap = loadFreq()

// ===== 重建字根组 =====
const promoEls = new Set<string>((layout.promos ?? []).map((p: any) => p.el))
const groups: GroupInfo[] = []
const groupOfElement = new Map<string, number>()

// 基组：newCode 覆盖
layout.base.forEach((b: any) => {
  const old = sd.groups.find((g) => g.code === b.code)!
  const elements = old.elements.filter((e) => !promoEls.has(e))
  const id = groups.length
  groups.push({ ...old, id, code: b.newCode, elements })
  for (const el of elements) groupOfElement.set(el, id)
})
// 提升组
for (const p of layout.promos ?? []) {
  const id = groups.length
  groups.push({ id, code: p.code, elements: [p.el], direct: [p.el], primary: p.el, small: p.code[1] })
  groupOfElement.set(p.el, id)
}

// ===== 校验 =====
// 1. 码位唯一
const used = new Map<string, number>()
for (const g of groups) used.set(g.code, (used.get(g.code) ?? 0) + 1)
const dup = [...used.entries()].filter(([, c]) => c > 1)
if (dup.length) console.log('!! 码位冲突:', JSON.stringify(dup))
// 2. 5/6大码联动
const g5 = groupOfElement.get('5')!, g6 = groupOfElement.get('6')!
if (groups[g5].code[0] !== groups[g6].code[0]) console.log('!! 5/6大码联动被破坏: 5=' + groups[g5].code + ' 6=' + groups[g6].code)
// 3. 音托校验（提升组小码=读音）
console.log(`组数=${groups.length}（基组240 + 提升${(layout.promos ?? []).length}）`)
for (const p of layout.promos ?? []) {
  const g = groups.find((x) => x.code === p.code)!
  if (g.elements[0] !== p.el) console.log('!! 提升组元素异常', p.el, p.code)
}

// ===== 编码数组 =====
const NG = groups.length
const big = new Uint8Array(NG)
const small = new Uint8Array(NG)
groups.forEach((g, i) => {
  big[i] = KEY_IDX.get(g.code[0])!
  small[i] = KEY_IDX.get(g.code[1])!
})

// ===== 加载拆分并快速评估 =====
const newSd: SchemeData = { ...sd, groups, groupOfElement }
const chars = loadChars('/workspace/opt/splits_1.2.json', newSd, freqMap)
const top = chars.filter((c) => c.rank > 0).sort((a, b) => a.rank - b.rank)
const ctx = createContext(top)
const r = fastEval(ctx, big, small, W, true)
console.log('快速评估: cd2_1500=' + r.cd2_1500 + ' w2=' + r.w2_1500.toFixed(2) + '% scMid=' + r.sc_1501_3000 +
  ' scTot=' + r.sc_total + ' sc_1500=' + r.sc_1500 + ' prefixes=' + r.prefixes)
if (layout.metrics) {
  const m = layout.metrics
  const ok = r.cd2_1500 === m.cd2_1500 && Math.abs(r.w2_1500 - m.w2_1500) < 0.01 && r.sc_total === m.sc_total
  console.log(ok ? '✓ 与SA保存的指标一致' : '!! 指标漂移: SA=' + JSON.stringify(m))
}

// ===== 生成码表并真实测评 =====
const { s42, sanDing, yijian } = genTables({ sd: newSd, chars, top, big, small, weights: W }, KEYS)
writeFileSync(`/workspace/opt/gen_42_${tag}.txt`, s42)
writeFileSync(`/workspace/opt/gen_sd_${tag}.txt`, sanDing)
console.log('\n一简(三定):', [...yijian.entries()].map(([k, c]) => k + '=' + c).join(' '))

printStats(`四二顶(${tag})`, evalTable(s42, freqMap))
printStats(`三定(${tag})`, evalTable(sanDing, freqMap))
