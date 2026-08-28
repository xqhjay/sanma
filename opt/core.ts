// 核心数据模块：字根组结构 + top6000拆分数据 + 快速评估器
import { readFileSync } from 'fs'
import { load } from 'js-yaml'

export const KEYS = [...'qwertyuiopasdfghjklzxcvbnm']
export const KEY_IDX = new Map(KEYS.map((k, i) => [k, i]))

// ===== 字根组结构 =====
export interface GroupInfo {
  id: number
  code: string            // 官方码位（大码+小码），如 'ei'
  elements: string[]      // 归并到该组的所有元素（含别名副根）
  direct: string[]        // 直接定义编码的元素（str2 / arr 局部定义）
  primary: string         // 主根（首个直接定义元素）
  small: string           // 小码字母
}

export interface SchemeData {
  groups: GroupInfo[]
  groupOfElement: Map<string, number>   // 元素 -> 组id
  aliasOf: Map<string, { element: string; index?: number }[]> // 元素定义结构（用于重新生成YAML）
  rawMapping: Record<string, any>
  // 特殊联动：'6'的大码 = '5'的大码
  bigAlias: Map<string, { element: string }>  // element -> {element: 其大码来源}
}

export function loadSchemeData(yamlPath: string): SchemeData {
  const raw = load(readFileSync(yamlPath, 'utf8')) as any
  const mapping = raw.form.mapping
  // 解析每个元素的 (大码,小码)
  const resolve = (el: string, memo = new Set<string>()): [string, string] => {
    if (memo.has(el)) throw new Error('循环别名: ' + el)
    memo.add(el)
    const v = mapping[el]
    if (v === undefined) throw new Error('映射缺失: ' + el)
    if (typeof v === 'string') {
      if (v.length === 2) return [v[0], v[1]]
      if (v.length === 1) return [v[0], v[0]] // meta键
      throw new Error('str?: ' + el)
    }
    if (Array.isArray(v)) {
      const parts: string[] = []
      for (const item of v) {
        if (typeof item === 'string') parts.push(item)
        else {
          const r = resolve(item.element, new Set(memo))
          parts.push(r[item.index ?? 0])
        }
      }
      return [parts[0], parts[1]]
    }
    return resolve(v.element, new Set(memo))
  }

  const groupMap = new Map<string, GroupInfo>()
  const groupOfElement = new Map<string, number>()
  const aliasOf = new Map<string, any>()
  const bigAlias = new Map<string, { element: string }>()

  for (const [el, v] of Object.entries(mapping)) {
    if (typeof v === 'string' && v.length === 1) continue // meta键（首字母-x）跳过
    if (el.startsWith('首字母')) continue // 拼音侧meta键跳过
    let code: string
    try { code = resolve(el).join('') } catch { continue }
    if (code[0] === code[0].toLowerCase() && !KEY_IDX.has(code[0])) continue
    // 记录大码联动（arr且第0项为别名）
    if (Array.isArray(v) && v[0] && typeof v[0] === 'object' && v[0].element) {
      bigAlias.set(el, { element: v[0].element })
    }
    let g = groupMap.get(code)
    if (!g) {
      g = { id: groupMap.size, code, elements: [], direct: [], primary: '', small: code[1] }
      groupMap.set(code, g)
    }
    g.elements.push(el)
    const isDirect = typeof v === 'string' || Array.isArray(v)
    if (isDirect) g.direct.push(el)
    groupOfElement.set(el, g.id)
    aliasOf.set(el, v)
  }
  const groups = [...groupMap.values()]
  for (const g of groups) {
    g.primary = g.direct[0] ?? g.elements[0]
  }
  return { groups, groupOfElement, aliasOf, rawMapping: mapping, bigAlias }
}

// ===== 拆分数据（top6000 + 全部） =====
export interface CharEntry {
  ch: string
  g: [number, number, number]   // 三元素的组id
  idx: [number, number, number] // 三元素的码位（0大1小）
  freq: number
  rank: number                  // kc6000名次（非top6000为0）
}

export function loadChars(splitsPath: string, sd: SchemeData, freqMap: Map<string, number>): CharEntry[] {
  const splits: any[] = JSON.parse(readFileSync(splitsPath, 'utf8'))
  const ranks = new Map<string, number>()
  ;[...freqMap.entries()].sort((a, b) => b[1] - a[1]).forEach(([c], i) => ranks.set(c, i + 1))
  const out: CharEntry[] = []
  for (const e of splits) {
    const g: [number, number, number] = [0, 0, 0]
    const idx: [number, number, number] = [0, 0, 0]
    let ok = true
    e.seq.forEach((s: any, i: number) => {
      const gid = sd.groupOfElement.get(s.element)
      if (gid === undefined) { ok = false; return }
      g[i] = gid
      idx[i] = s.index
    })
    if (!ok) throw new Error('拆分元素缺组: ' + e.char)
    out.push({ ch: e.char, g, idx, freq: freqMap.get(e.char) ?? e.freq, rank: ranks.get(e.char) ?? 0 })
  }
  return out
}

// ===== 快速评估器 =====
// 布局 big[组id] = 键索引(0-25)；小码 small[组id] = 键索引
export interface EvalResult {
  cd2_1500: number
  w2_1500: number          // %
  sc_1500: number
  sc_1501_3000: number
  sc_total: number
  prefixes: number         // top6000覆盖的二码前缀数
  feasible: boolean        // sc_1500 === 0
  score: number
  // 二简分配：prefixInt -> charIdx（供码表生成，needDetails时填充）
  simpleOf: Map<number, number> | null
}

export interface EvalWeights {
  cd2: number       // 每个前1500二码字
  w2: number        // 加权比重每1%
  scMid: number     // 每个1501~3000出简重
  scTotal: number   // 每个总出简重
  prefix: number    // 每个未覆盖前缀
  infeasible: number // 每个前1500出简重（硬约束）
}

export const DEFAULT_WEIGHTS: EvalWeights = {
  cd2: 1000, w2: 30, scMid: 5000, scTotal: 100, prefix: 2000, infeasible: 2e6,
}

// 段落: rank -> section (0:1-300 1:301-500 2:501-1500 3:1501-3000 4:3001-6000 5:非top6000)
export function sectionOf(rank: number): number {
  if (rank === 0) return 5
  if (rank <= 300) return 0
  if (rank <= 500) return 1
  if (rank <= 1500) return 2
  if (rank <= 3000) return 3
  return 4
}

// 预计算上下文（平坦化数组，避免对象属性访问）
export interface EvalContext {
  n: number
  G1: Uint16Array; G2: Uint16Array; G3: Uint16Array; I2: Uint8Array; I3: Uint8Array
  FREQ: Float64Array; SEC: Uint8Array; CH: string[]
  total1500freq: number
  // 每前缀字符索引（rank序）：counting sort结果
  pCount: Int32Array; pStart: Int32Array; pLen: Int32Array; pIdx: Int32Array
  code3: Int32Array
  // 每前缀的组结构（扫描时构建）
  // scratch
  champOf: Int32Array; secondOf: Int32Array; stamp: Int32Array; curStamp: number
  candArr: Int32Array
}

export function createContext(top: CharEntry[]): EvalContext {
  const n = top.length
  const ctx: EvalContext = {
    n,
    G1: new Uint16Array(n), G2: new Uint16Array(n), G3: new Uint16Array(n),
    I2: new Uint8Array(n), I3: new Uint8Array(n),
    FREQ: new Float64Array(n), SEC: new Uint8Array(n), CH: new Array(n),
    total1500freq: 0,
    pCount: new Int32Array(678), pStart: new Int32Array(678), pLen: new Int32Array(678),
    pIdx: new Int32Array(n),
    code3: new Int32Array(n),
    champOf: new Int32Array(32768), secondOf: new Int32Array(32768),
    stamp: new Int32Array(32768), curStamp: 0,
    candArr: new Int32Array(n),
  }
  for (let i = 0; i < n; i++) {
    const e = top[i]
    ctx.G1[i] = e.g[0]; ctx.G2[i] = e.g[1]; ctx.G3[i] = e.g[2]
    ctx.I2[i] = e.idx[1]; ctx.I3[i] = e.idx[2]
    ctx.FREQ[i] = e.freq; ctx.SEC[i] = sectionOf(e.rank); ctx.CH[i] = e.ch
    if (e.rank > 0 && e.rank <= 1500) ctx.total1500freq += e.freq
  }
  return ctx
}

// 计算三码整数数组并按前缀分桶（rank序保持）
// code3 = (c1<<10)|(c2<<5)|c3；prefix = c1*26+c2（稠密，0..675）
function bucketByPrefix(ctx: EvalContext, big: Uint8Array, small: Uint8Array): number {
  const { n, G1, G2, G3, I2, I3, code3, pCount, pStart, pLen, pIdx } = ctx
  pCount.fill(0)
  for (let i = 0; i < n; i++) {
    const c1 = big[G1[i]]
    const c2 = I2[i] ? small[G2[i]] : big[G2[i]]
    const c3 = I3[i] ? small[G3[i]] : big[G3[i]]
    code3[i] = (c1 << 10) | (c2 << 5) | c3
    pCount[c1 * 26 + c2]++
  }
  let acc = 0, nPre = 0
  for (let p = 0; p < 676; p++) {
    pStart[p] = acc
    pLen[p] = pCount[p]
    if (pCount[p] > 0) nPre++
    acc += pCount[p]
  }
  for (let p = 0; p < 676; p++) pCount[p] = pStart[p] // 游标
  for (let i = 0; i < n; i++) {
    const c = code3[i]
    const p = (c >> 10) * 26 + ((c >> 5) & 31)
    pIdx[pCount[p]++] = i
  }
  return nPre
}

export function fastEval(
  ctx: EvalContext,
  big: Uint8Array,
  small: Uint8Array,
  w: EvalWeights = DEFAULT_WEIGHTS,
  needDetails = false,
): EvalResult {
  const nPre = bucketByPrefix(ctx, big, small)
  const { n, code3, pStart, pLen, pIdx, SEC, FREQ, champOf, secondOf, stamp, candArr } = ctx
  ctx.curStamp++
  const st = ctx.curStamp

  let cd2_1500 = 0, w2sum = 0, sc_1500 = 0, sc_1501_3000 = 0, sc_total = 0
  const simpleOf = needDetails ? new Map<number, number>() : null
  const wCd2 = w.cd2, wW2 = w.w2 / ctx.total1500freq * 100, wScMid = w.scMid,
    wScTotal = w.scTotal, wInf = w.infeasible

  for (let p = 0; p < 676; p++) {
    const s = pStart[p], len = pLen[p]
    if (len === 0) continue
    const e = s + len
    // 扫描前缀内字符（rank序），建组结构：champ/second per code3
    let nGroups = 0
    let nCand = 0
    // 段落计数
    let secAll0 = 0, secAll1 = 0, secAll2 = 0, secAll3 = 0
    for (let k = s; k < e; k++) {
      const i = pIdx[k]
      const sec = SEC[i]
      if (sec === 0) secAll0++
      else if (sec === 1) secAll1++
      else if (sec === 2) secAll2++
      else if (sec === 3) secAll3++
      const c3 = code3[i]
      if (stamp[c3] !== st) {
        stamp[c3] = st
        champOf[c3] = i
        secondOf[c3] = -1
        nGroups++
        // 组冠军是二简候选
        candArr[nCand++] = i
      } else if (secondOf[c3] === -1) {
        secondOf[c3] = i
        if (sec <= 2) candArr[nCand++] = i // 前1500非冠军也可能是候选
      } else if (sec <= 2) {
        candArr[nCand++] = i
      }
    }
    // base free = 各组champ。miss按段落：非champ数
    // 候选评估：x=champ(Gx) → extra=second(Gx)；x≠champ → extra=x
    // miss_sec = secAll_sec - champ_sec
    let champSec0 = 0, champSec1 = 0, champSec2 = 0, champSec3 = 0
    for (let k = s; k < e; k++) {
      const i = pIdx[k]
      if (champOf[code3[i]] !== i) continue
      const sec = SEC[i]
      if (sec === 0) champSec0++
      else if (sec === 1) champSec1++
      else if (sec === 2) champSec2++
      else if (sec === 3) champSec3++
    }
    const miss1500 = secAll0 - champSec0 + secAll1 - champSec1 + secAll2 - champSec2
    const missMid = secAll3 - champSec3
    const missAll = len - nGroups

    let bestGain = -Infinity, bestX = -1
    for (let ci = 0; ci < nCand; ci++) {
      const x = candArr[ci]
      const c3x = code3[x]
      const isChamp = champOf[c3x] === x
      let extra = -1
      if (isChamp) extra = secondOf[c3x]
      else extra = x
      const extraSec = extra >= 0 ? SEC[extra] : -1
      const resc1500 = extraSec >= 0 && extraSec <= 2 ? 1 : 0
      const rescMid = extraSec === 3 ? 1 : 0
      const infeas = miss1500 - resc1500
      const scMid = missMid - rescMid
      const scAll = missAll - (extra >= 0 ? 1 : 0)
      const xSec = SEC[x]
      const cd2 = xSec <= 2 ? 1 : 0
      const w2 = cd2 ? FREQ[x] : 0
      const gain = wCd2 * cd2 + wW2 * w2 - wScMid * scMid - wScTotal * scAll - wInf * infeas
      if (gain > bestGain) { bestGain = gain; bestX = x }
    }
    // 应用最优（重算一次精确值）
    const x = bestX
    const c3x = code3[x]
    const isChamp = champOf[c3x] === x
    const extra = isChamp ? secondOf[c3x] : x
    // free集：champs + extra(若≠-1)。x本身：若isChamp已在champs；否则=extra
    for (let k = s; k < e; k++) {
      const i = pIdx[k]
      if (champOf[code3[i]] === i) continue // 组冠军免
      if (i === x) continue // 二简免
      if (i === extra) continue // 组内第二(二简为组冠军时)免
      const sec = SEC[i]
      if (sec <= 2) sc_1500++
      else if (sec === 3) sc_1501_3000++
      sc_total++
    }
    if (SEC[x] <= 2) { cd2_1500++; w2sum += FREQ[x] }
    if (simpleOf) simpleOf.set(p, x)
  }

  const feasible = sc_1500 === 0
  const score = w.cd2 * cd2_1500 + w.w2 * (w2sum / ctx.total1500freq * 100)
    - w.scMid * sc_1501_3000 - w.scTotal * sc_total
    - w.prefix * (676 - nPre) - (feasible ? 0 : 1e12) - w.infeasible * sc_1500
  return {
    cd2_1500, w2_1500: w2sum / ctx.total1500freq * 100, sc_1500, sc_1501_3000, sc_total,
    prefixes: nPre, feasible, score, simpleOf,
  }
}
