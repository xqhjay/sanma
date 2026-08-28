// 模拟退火优化器：大码布局重排 + 副根提升（拆分归并组）
// 目标: cd2_1500↑ w2_1500↑ scMid↓ scTotal↓, 硬约束 sc_1500=0, 组数≤320
import { readFileSync, writeFileSync } from 'fs'
import { loadSchemeData, loadChars, fastEval, createContext, KEYS, KEY_IDX, EvalWeights, EvalResult } from './core'
import { loadFreq } from './eval_table'

// ===== 拼音音托 =====
const pyDict = new Map<string, string>()
for (const line of readFileSync('/workspace/opt/dictionary_ext.txt', 'utf8').split(/\r?\n/)) {
  const [ch, py] = line.split('\t')
  if (ch && py) pyDict.set(ch, py)
}
// 手工补充常见部件读音（有明确读音的著名变体）
const manualPy: Record<string, string> = { '⺩': 'wang2', '訁': 'yan2', '覀': 'xi1', '牜': 'niu2', '亼': 'ji2' }
for (const [k, v] of Object.entries(manualPy)) if (!pyDict.has(k)) pyDict.set(k, v)
export function yintuoKey(pinyin: string): number | null {
  if (!pinyin || !/^[a-z]+[1-5]$/.test(pinyin)) return null
  const py = pinyin.slice(0, -1)
  let c: string | null = null
  if (py.startsWith('zh')) c = py.replace(/^zh/, '')[0] ?? null
  else if (py.startsWith('ch')) c = 'c'
  else if (py.startsWith('sh')) c = 's'
  else if (py === 'yi') c = 'i'
  else if (py === 'yu') c = 'v'
  else if (py === 'wu') c = 'u'
  else c = py[0]
  return c ? KEY_IDX.get(c) ?? null : null
}

// ===== 权重 =====
export const W: EvalWeights = {
  cd2: parseFloat(process.env.W_CD2 ?? '1000'),
  w2: parseFloat(process.env.W_W2 ?? '3000'),
  scMid: parseFloat(process.env.W_SCMD ?? '20000'),
  scTotal: parseFloat(process.env.W_SCT ?? '1200'),
  prefix: 0, infeasible: 2e6,
}
const TAG = process.env.TAG ?? ''

// ===== 载入 =====
const sd = loadSchemeData('/workspace/奕码_1.2.yaml')
const freqMap = loadFreq()
const chars = loadChars('/workspace/opt/splits_1.2.json', sd, freqMap)
const top = chars.filter((c) => c.rank > 0).sort((a, b) => a.rank - b.rank)
const ctx = createContext(top)
const BASE = sd.groups.length // 240

// splits元素序列
const splits: any[] = JSON.parse(readFileSync('/workspace/opt/splits_1.2.json', 'utf8'))
const seqOf = new Map<string, string[]>()
for (const e of splits) seqOf.set(e.char, e.seq.map((s: any) => s.element))

// ===== 候选提升元素（top6000加权使用频次） =====
const useFreq = new Map<string, number>()
for (const e of splits) {
  const f = freqMap.get(e.char) ?? 0
  if (f <= 0) continue
  const seen = new Set<string>()
  for (const s of e.seq) if (!seen.has(s.element)) { seen.add(s.element); useFreq.set(s.element, (useFreq.get(s.element) ?? 0) + f) }
}

export interface PromoCand { el: string; fromGroup: number; small: number; freq: number }
const strokeSet = new Set(['1', '2', '3', '4', '5', '6'])
export const promoCands: PromoCand[] = []
for (const g of sd.groups) {
  for (const el of g.elements) {
    if (el === g.primary) continue
    if (strokeSet.has(el)) continue
    if (sd.bigAlias.has(el)) continue
    const py = pyDict.get(el)
    if (!py) continue
    const sm = yintuoKey(py)
    if (sm === null) continue
    const f = useFreq.get(el) ?? 0
    if (f < 40000) continue
    promoCands.push({ el, fromGroup: g.id, small: sm, freq: f })
  }
}
promoCands.sort((a, b) => b.freq - a.freq)
const NP = promoCands.length
console.log(`基组数=${BASE} 提升候选=${NP} 组数上限=320`)

// ===== 状态 =====
const NG = BASE + NP
export const big = new Uint8Array(NG)
export const small = new Uint8Array(NG)
sd.groups.forEach((g, i) => {
  big[i] = KEY_IDX.get(g.code[0])!
  small[i] = KEY_IDX.get(g.code[1])!
})
promoCands.forEach((c, i) => { small[BASE + i] = c.small; big[BASE + i] = 255 })

// 元素 → (top下标, 位置) 索引
const elemCharPos = new Map<string, number[]>()
top.forEach((e, i) => {
  const seq = seqOf.get(e.ch)!
  seq.forEach((el, pos) => {
    let arr = elemCharPos.get(el)
    if (!arr) { arr = []; elemCharPos.set(el, arr) }
    arr.push(i, pos)
  })
})

// code占用
const codeUsed = new Uint8Array(676)
for (let g = 0; g < BASE; g++) codeUsed[big[g] * 26 + small[g]]++

// '6'跟随'5'联动
const g5 = sd.groupOfElement.get('5')!, g6 = sd.groupOfElement.get('6')!
const linked: [number, number][] = g5 !== g6 ? [[g5, g6]] : []
const partnersOf = (g: number): number[] => {
  for (const [a, b] of linked) if (a === g) return [a, b]; else if (b === g) return [a, b]
  return [g]
}

// ctx G数组
const groupOfElement = new Map(sd.groupOfElement)
function rebuildG() {
  top.forEach((e, i) => {
    const seq = seqOf.get(e.ch)!
    ctx.G1[i] = groupOfElement.get(seq[0])!
    ctx.G2[i] = groupOfElement.get(seq[1])!
    ctx.G3[i] = groupOfElement.get(seq[2])!
  })
}
rebuildG()

// ===== 提升开关 =====
function applyPromo(slot: number, k: number): boolean {
  const c = promoCands[slot - BASE]
  const code = k * 26 + c.small
  if (codeUsed[code] > 0) return false
  big[slot] = k
  codeUsed[code]++
  active.set(slot, c)
  const ecp = elemCharPos.get(c.el)!
  for (let j = 0; j < ecp.length; j += 2) {
    const i = ecp[j], pos = ecp[j + 1]
    if (pos === 0) ctx.G1[i] = slot
    else if (pos === 1) ctx.G2[i] = slot
    else ctx.G3[i] = slot
  }
  groupOfElement.set(c.el, slot)
  return true
}
function removePromo(slot: number): number {
  const c = active.get(slot)!
  const k = big[slot]
  codeUsed[k * 26 + small[slot]]--
  active.delete(slot)
  big[slot] = 255
  const ecp = elemCharPos.get(c.el)!
  for (let j = 0; j < ecp.length; j += 2) {
    const i = ecp[j], pos = ecp[j + 1]
    if (pos === 0) ctx.G1[i] = c.fromGroup
    else if (pos === 1) ctx.G2[i] = c.fromGroup
    else ctx.G3[i] = c.fromGroup
  }
  groupOfElement.set(c.el, c.fromGroup)
  return k
}
const active = new Map<number, PromoCand>()

// ===== 评估 =====
export function evaluate(): EvalResult { return fastEval(ctx, big, small, W) }
function score(): number { return fastEval(ctx, big, small, W).score }

// ===== 移动原语 =====
function moveGroup(g: number, k: number): boolean {
  const gs = partnersOf(g)
  if (gs.every((x) => big[x] === k)) return false
  for (const x of gs) if (codeUsed[k * 26 + small[x]] > 0) return false
  const oldBigs = gs.map((x) => big[x])
  gs.forEach((x, i) => {
    codeUsed[oldBigs[i] * 26 + small[x]]--
    codeUsed[k * 26 + small[x]]++
    big[x] = k
  })
  return true
}
function undoMoveGroup(g: number, oldBigs: number[]): void {
  const gs = partnersOf(g)
  gs.forEach((x, i) => {
    codeUsed[big[x] * 26 + small[x]]--
    codeUsed[oldBigs[i] * 26 + small[x]]++
    big[x] = oldBigs[i]
  })
}
function swapGroups(g1: number, g2: number): boolean {
  if (big[g1] === big[g2]) return false
  const gs1 = partnersOf(g1), gs2 = partnersOf(g2)
  if (gs1.some((x) => gs2.includes(x))) return false
  const k1 = big[g1], k2 = big[g2]
  for (const x of gs1) codeUsed[big[x] * 26 + small[x]]--
  for (const x of gs2) codeUsed[big[x] * 26 + small[x]]--
  let ok = true
  for (const x of gs1) if (codeUsed[k2 * 26 + small[x]] > 0) ok = false
  if (ok) for (const x of gs2) if (codeUsed[k1 * 26 + small[x]] > 0) ok = false
  if (ok) {
    for (const x of gs1) { big[x] = k2; codeUsed[k2 * 26 + small[x]]++ }
    for (const x of gs2) { big[x] = k1; codeUsed[k1 * 26 + small[x]]++ }
  } else {
    for (const x of gs1) codeUsed[k1 * 26 + small[x]]++
    for (const x of gs2) codeUsed[k2 * 26 + small[x]]++
  }
  return ok
}
function undoSwap(g1: number, g2: number) {
  const gs1 = partnersOf(g1), gs2 = partnersOf(g2)
  // 交换后: gs1在k2_orig, gs2在k1_orig → 恢复需互换回去
  const k1 = big[gs2[0]], k2 = big[gs1[0]]
  for (const x of gs1) { codeUsed[big[x] * 26 + small[x]]--; big[x] = k1; codeUsed[k1 * 26 + small[x]]++ }
  for (const x of gs2) { codeUsed[big[x] * 26 + small[x]]--; big[x] = k2; codeUsed[k2 * 26 + small[x]]++ }
}

// ===== 快照/恢复 =====
interface Snapshot { big: Uint8Array; activeSlots: number[] }
function snap(): Snapshot { return { big: big.slice(), activeSlots: [...active.keys()] } }
function restore(s: Snapshot) {
  for (const slot of [...active.keys()]) removePromo(slot)
  big.set(s.big)
  codeUsed.fill(0)
  for (let g = 0; g < BASE; g++) codeUsed[big[g] * 26 + small[g]]++
  for (const slot of s.activeSlots) {
    if (!applyPromo(slot, s.big[slot])) throw new Error('快照恢复失败 slot=' + slot)
  }
}

function rnd(n: number) { return Math.floor(Math.random() * n) }

// ===== SA =====
function saPhase(iters: number, T0: number, Tend: number, allowPromo: boolean, label: string) {
  const alpha = Math.pow(Tend / T0, 1 / iters)
  let T = T0
  let cur = score()
  let best = cur
  let bestSnap = snap()
  let accepted = 0
  const t0 = Date.now()
  for (let it = 0; it < iters; it++) {
    T *= alpha
    const r = Math.random()
    if (allowPromo && r < 0.05) {
      const inactive: number[] = []
      for (let s = BASE; s < NG; s++) if (!active.has(s)) inactive.push(s)
      const wantActivate = Math.random() < 0.65 && inactive.length > 0 && BASE + active.size < 320
      if (wantActivate) {
        const slot = inactive[rnd(inactive.length)]
        let bestK = -1, bestS = -Infinity
        for (let k = 0; k < 26; k++) {
          if (!applyPromo(slot, k)) continue
          const s = score()
          if (s > bestS) { bestS = s; bestK = k }
          removePromo(slot)
        }
        if (bestK >= 0 && applyPromo(slot, bestK)) {
          if (bestS >= cur || Math.random() < Math.exp((bestS - cur) / T)) { accepted++; cur = bestS }
          else removePromo(slot)
        }
      } else if (active.size > 0) {
        const slots = [...active.keys()]
        const slot = slots[rnd(slots.length)]
        const k = removePromo(slot)
        const s = score()
        if (s >= cur || Math.random() < Math.exp((s - cur) / T)) { accepted++; cur = s }
        else applyPromo(slot, k)
      }
    } else if (r < 0.68) {
      // 单组移动（含激活的提升组）
      let g: number
      if (allowPromo && active.size > 0 && Math.random() < 0.15) {
        const slots = [...active.keys()]
        g = slots[rnd(slots.length)]
      } else g = rnd(BASE)
      const k = rnd(26)
      const oldBigs = partnersOf(g).map((x) => big[x])
      if (!moveGroup(g, k)) continue
      const s = score()
      if (s >= cur || Math.random() < Math.exp((s - cur) / T)) { accepted++; cur = s }
      else undoMoveGroup(g, oldBigs)
    } else {
      const g1 = rnd(BASE), g2 = rnd(BASE)
      if (g1 === g2) continue
      if (!swapGroups(g1, g2)) continue
      const s = score()
      if (s >= cur || Math.random() < Math.exp((s - cur) / T)) { accepted++; cur = s }
      else undoSwap(g1, g2)
    }
    if (cur > best) { best = cur; bestSnap = snap() }
    if (it % 50000 === 0 && it > 0) {
      const real = score()
      if (Math.abs(real - cur) > 1) console.log(`  !!状态漂移 cur=${cur.toFixed(0)} real=${real.toFixed(0)}`)
      cur = real
      const r2 = fastEval(ctx, big, small, W)
      console.log(`[${label}] it=${it} T=${T.toFixed(1)} best=${best.toFixed(0)} cd2=${r2.cd2_1500} w2=${r2.w2_1500.toFixed(2)} scMid=${r2.sc_1501_3000} scTot=${r2.sc_total} sc15=${r2.sc_1500} promos=${active.size} acc=${(accepted / it * 100).toFixed(1)}% ${((Date.now() - t0) / 1000) | 0}s`)
    }
  }
  restore(bestSnap)
  console.log(`[${label}] 完成 best=${best.toFixed(0)} 用时${((Date.now() - t0) / 1000).toFixed(0)}s`)
  return best
}

// ===== 贪心提升 pass =====
function greedyPromoPass() {
  for (let s = BASE; s < NG; s++) {
    if (active.has(s)) continue
    if (BASE + active.size >= 320) break
    const prev = score()
    let bestK = -1, bestS = prev
    for (let k = 0; k < 26; k++) {
      if (!applyPromo(s, k)) continue
      const v = score()
      if (v > bestS) { bestS = v; bestK = k }
      removePromo(s)
    }
    if (bestK >= 0) {
      applyPromo(s, bestK)
      const c = promoCands[s - BASE]
      console.log(`  提升 ${c.el} → ${KEYS[bestK]}${KEYS[c.small]} Δ=${(bestS - prev).toFixed(0)} score=${bestS.toFixed(0)}`)
    }
  }
}

// ===== 提升剪枝 =====
function prunePromos() {
  for (const slot of [...active.keys()]) {
    const cur = score()
    const k = removePromo(slot)
    const s = score()
    if (s >= cur - 1e-9) {
      console.log(`  剪枝 ${promoCands[slot - BASE].el} (Δ=${(s - cur).toFixed(0)})`)
    } else {
      applyPromo(slot, k)
    }
  }
}

// ===== 爬山精修 =====
function hillClimb(maxRounds = 8) {
  let cur = score()
  for (let round = 0; round < maxRounds; round++) {
    let improved = false
    // 单组最佳键（基组+激活组）
    const allGroups: number[] = []
    for (let g = 0; g < BASE; g++) allGroups.push(g)
    for (const slot of active.keys()) allGroups.push(slot)
    for (const g of allGroups) {
      const gs = partnersOf(g)
      const oldBigs = gs.map((x) => big[x])
      if (gs.length > 1 && gs.some((x) => !allGroups.includes(x))) continue
      let bestK = oldBigs[0], bestS = cur
      for (let k = 0; k < 26; k++) {
        if (oldBigs.every((b) => b === k)) continue
        if (!moveGroup(g, k)) continue
        const s = score()
        if (s > bestS + 1e-9) { bestS = s; bestK = k }
        undoMoveGroup(g, oldBigs)
      }
      if (bestK !== oldBigs[0]) {
        if (moveGroup(g, bestK)) { cur = bestS; improved = true }
      }
    }
    // 交换（基组×基组、基组×激活组）
    const actSlots = [...active.keys()]
    for (let g1 = 0; g1 < BASE; g1++) {
      for (let g2 = g1 + 1; g2 < BASE; g2++) {
        if (big[g1] === big[g2]) continue
        if (!swapGroups(g1, g2)) continue
        const s = score()
        if (s > cur + 1e-9) { cur = s; improved = true }
        else undoSwap(g1, g2)
      }
      for (const slot of actSlots) {
        if (big[g1] === big[slot]) continue
        if (!swapGroups(g1, slot)) continue
        const s = score()
        if (s > cur + 1e-9) { cur = s; improved = true }
        else undoSwap(g1, slot)
      }
    }
    console.log(`[爬山] round=${round} score=${cur.toFixed(0)}`)
    if (!improved) break
  }
  return cur
}

// ===== 温启动：从已保存布局恢复 =====
const FROM = process.env.FROM ?? ''
function warmStart() {
  const lay = JSON.parse(readFileSync(FROM, 'utf8'))
  for (const b of lay.base) {
    const g = sd.groups.find((x) => x.code === b.code)
    if (!g) throw new Error('温启动基组缺失: ' + b.code)
    // 逐partner设置大码（5/6联动组共享大码）
    for (const p of partnersOf(g.id)) big[p] = KEY_IDX.get(b.newCode[0])!
    small[g.id] = KEY_IDX.get(b.newCode[1])!
  }
  codeUsed.fill(0)
  for (let g = 0; g < BASE; g++) codeUsed[big[g] * 26 + small[g]]++
  // 校验码位唯一
  for (let c = 0; c < 676; c++) if (codeUsed[c] > 1) throw new Error('温启动码位冲突')
  // 恢复promos
  for (const p of lay.promos ?? []) {
    const slot = BASE + promoCands.findIndex((c) => c.el === p.el)
    if (slot < BASE) throw new Error('温启动提升根不在候选: ' + p.el)
    if (!applyPromo(slot, KEY_IDX.get(p.code[0])!)) throw new Error('温启动提升失败: ' + p.el + ' ' + p.code)
  }
  console.log(`温启动 ${FROM}: promos=${active.size}`)
}

// ===== 主流程 =====
function fmt(r: EvalResult) {
  return `cd2_1500=${r.cd2_1500} w2=${r.w2_1500.toFixed(2)}% scMid=${r.sc_1501_3000} scTot=${r.sc_total} sc_1500=${r.sc_1500} 组数=${BASE + active.size} 前缀=${r.prefixes}`
}
const SCALE = parseFloat(process.env.SCALE ?? '1')
const REFINE = process.env.REFINE === '1'
function main() {
  if (FROM) warmStart()
  console.log('=== 初始（官方布局）===', fmt(evaluate()))
  if (!REFINE) {
    saPhase(Math.round(300000 * SCALE), 8000, 30, false, 'P1-大码SA')
    console.log('P1后:', fmt(evaluate()))
    greedyPromoPass()
    console.log('P2后:', fmt(evaluate()))
  }
  saPhase(Math.round(500000 * SCALE), REFINE ? 600 : 4000, 20, true, REFINE ? 'R1-精修SA' : 'P3-联合SA')
  console.log('P3后:', fmt(evaluate()))
  hillClimb(SCALE >= 0.5 ? 8 : 2)
  console.log('P4后:', fmt(evaluate()))
  prunePromos()
  hillClimb(SCALE >= 0.5 ? 4 : 1)
  console.log('P5后(剪枝+精修):', fmt(evaluate()))

  const layout = {
    base: sd.groups.map((g, i) => ({ code: g.code, primary: g.primary, elements: g.elements, newCode: KEYS[big[i]] + KEYS[small[i]] })),
    promos: [...active.entries()].map(([slot, c]) => ({ el: c.el, fromGroup: c.fromGroup, code: KEYS[big[slot]] + KEYS[small[slot]], freq: c.freq })),
    metrics: (() => { const r = evaluate(); return { cd2_1500: r.cd2_1500, w2_1500: r.w2_1500, sc_1501_3000: r.sc_1501_3000, sc_total: r.sc_total, sc_1500: r.sc_1500, prefixes: r.prefixes } })(),
  }
  writeFileSync(`/workspace/opt/layout${TAG}.json`, JSON.stringify(layout, null, 1))
  console.log('\n=== 最终 ===', fmt(evaluate()))
  console.log('提升字根数:', layout.promos.length, layout.promos.map((p) => `${p.el}→${p.code}`).join(' '))
}
main()
