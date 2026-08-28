// 码表生成器：布局 → 四二顶/三定码表
import { SchemeData, CharEntry, fastEval, createContext, sectionOf } from './core'

export interface GenInput {
  sd: SchemeData
  chars: CharEntry[]        // 全部字（含非top6000）
  top: CharEntry[]          // top6000（rank序）
  big: Uint8Array
  small: Uint8Array
  weights?: any
}

export function code3Of(e: CharEntry, big: Uint8Array, small: Uint8Array, KEYS: string[]): string {
  const c = (g: number, i: number) => KEYS[i ? small[g] : big[g]]
  return c(e.g[0], e.idx[0]) + c(e.g[1], e.idx[1]) + c(e.g[2], e.idx[2])
}

// 每前缀最优二简分配（含autoFree集合：一简字自动免出简重、不可为二简）
export function optimalSimples(
  top: CharEntry[], big: Uint8Array, small: Uint8Array, KEYS: string[],
  autoFree: Set<string> = new Set(),
  weights = { cd2: 1000, w2: 30, scMid: 5000, scTotal: 100, infeasible: 2e6 },
): Map<number, CharEntry> {
  const codeMap = new Map<CharEntry, string>()
  const byPrefix = new Map<number, CharEntry[]>()
  for (const e of top) {
    const code = code3Of(e, big, small, KEYS)
    codeMap.set(e, code)
    const p = code.charCodeAt(0) * 26 + code.charCodeAt(1) - 97 * 27
    let b = byPrefix.get(p)
    if (!b) { b = []; byPrefix.set(p, b) }
    b.push(e)
  }
  const total1500 = top.filter((c) => c.rank > 0 && c.rank <= 1500).reduce((s, c) => s + c.freq, 0)
  const res = new Map<number, CharEntry>()
  for (const [p, chars] of byPrefix) {
    // 组结构（chars已rank序）
    const groupsHere = new Map<string, CharEntry[]>()
    for (const c of chars) {
      const code = codeMap.get(c)!
      let b = groupsHere.get(code)
      if (!b) { b = []; groupsHere.set(code, b) }
      b.push(c)
    }
    const isAuto = (c: CharEntry) => autoFree.has(c.ch)
    // base free = 各组首个非autoFree字 + autoFree字
    const baseFree = new Set<CharEntry>()
    for (const [, b] of groupsHere) {
      const f = b.find((c) => !isAuto(c))
      if (f) baseFree.add(f)
    }
    for (const c of chars) if (isAuto(c)) baseFree.add(c)
    // miss统计（不含autoFree字）
    const miss = (pred: (c: CharEntry) => boolean) =>
      chars.filter((c) => !isAuto(c) && !baseFree.has(c) && pred(c)).length
    const miss1500 = miss((c) => c.rank <= 1500)
    const missMid = miss((c) => c.rank > 1500 && c.rank <= 3000)
    const missAll = chars.filter((c) => !isAuto(c) && !baseFree.has(c)).length
    // 候选：各组前两名（非autoFree）+ 前1500非autoFree字
    const cand = new Set<CharEntry>()
    for (const [, b] of groupsHere) {
      const na = b.filter((c) => !isAuto(c))
      if (na[0]) cand.add(na[0])
      if (na[1]) cand.add(na[1])
    }
    for (const c of chars) if (c.rank <= 1500 && !isAuto(c)) cand.add(c)
    let best: CharEntry | null = null, bestGain = -Infinity
    for (const x of cand) {
      const b = groupsHere.get(codeMap.get(x)!)!
      const na = b.filter((c) => !isAuto(c))
      const isChamp = na[0] === x
      let extra: CharEntry | null = null
      if (isChamp) extra = na[1] ?? null
      else extra = x
      const r1500 = extra && extra.rank > 0 && extra.rank <= 1500 ? 1 : 0
      const rMid = extra && extra.rank > 1500 && extra.rank <= 3000 ? 1 : 0
      const infeas = miss1500 - r1500
      const scMid = missMid - rMid
      const scAll = missAll - (extra ? 1 : 0)
      const cd2 = x.rank > 0 && x.rank <= 1500 ? 1 : 0
      const w2 = cd2 ? x.freq : 0
      const gain = weights.cd2 * cd2 + weights.w2 * (w2 / total1500 * 100)
        - weights.scMid * scMid - weights.scTotal * scAll - weights.infeasible * Math.max(0, infeas)
      if (gain > bestGain) { bestGain = gain; best = x }
    }
    res.set(p, best!)
  }
  return res
}

export function genTables(input: GenInput, KEYS: string[]): {
  s42: string
  sanDing: string
  yijian: Map<string, string>
  simpleChars42: Set<string>
} {
  const { chars, top, big, small } = input
  const W = input.weights
  // 1. 全字编码
  const codeOf = new Map<string, string>()
  for (const e of chars) codeOf.set(e.ch, code3Of(e, big, small, KEYS))
  const prefixOf = (code: string) => code.charCodeAt(0) * 26 + code.charCodeAt(1) - 97 * 27

  // 2. top6000排序与索引
  const ctx = createContext(top)
  const r = fastEval(ctx, big, small, W, true)
  const simpleOfTop = r.simpleOf! // prefix -> charIdx in top
  const topByCh = new Map(top.map((c) => [c.ch, c]))

  // 3. 全字按前缀分桶
  const byPrefix = new Map<number, CharEntry[]>()
  for (const e of chars) {
    const p = prefixOf(codeOf.get(e.ch)!)
    let b = byPrefix.get(p)
    if (!b) { b = []; byPrefix.set(p, b) }
    b.push(e)
  }
  // 桶内排序：rank asc（rank0最后），同rank按freq desc
  const cmp = (a: CharEntry, b: CharEntry) => {
    if ((a.rank > 0) !== (b.rank > 0)) return a.rank > 0 ? -1 : 1
    if (a.rank > 0 && a.rank !== b.rank) return a.rank - b.rank
    return b.freq - a.freq
  }
  for (const [, b] of byPrefix) b.sort(cmp)

  // 4. 二简分配（四二顶）
  const simple42 = new Map<number, CharEntry>() // prefix -> char
  for (const [p, idx] of simpleOfTop) simple42.set(p, top[idx])
  // 未覆盖前缀（无top6000字）：取桶内最高频
  for (const [p, b] of byPrefix) {
    if (!simple42.has(p)) simple42.set(p, b[0])
  }

  // 5. 一简（三定）：每键 = 形码首键为该键的最高频top6000字
  const yijian = new Map<string, string>() // key -> char
  const yijianChars = new Set<string>()
  for (let k = 0; k < 26; k++) {
    const cands = top.filter((e) => codeOf.get(e.ch)![0] === KEYS[k])
    let pick: CharEntry | undefined
    if (cands.length > 0) pick = cands[0]
    else {
      const all = chars.filter((e) => codeOf.get(e.ch)![0] === KEYS[k])
      all.sort(cmp)
      pick = all[0]
    }
    if (pick) { yijian.set(KEYS[k], pick.ch); yijianChars.add(pick.ch) }
  }

  // 6. 三定二简重分配（一简字不可为二简，自动免）
  const simpleSD = optimalSimples(top, big, small, KEYS, yijianChars, W)
  const simpleSDMap = new Map<number, CharEntry>()
  for (const [p, c] of simpleSD) simpleSDMap.set(p, c)
  for (const [p, b] of byPrefix) {
    if (!simpleSDMap.has(p)) {
      const nb = b.filter((e) => !yijianChars.has(e.ch))
      simpleSDMap.set(p, nb[0] ?? b[0])
    }
  }

  // 7. 生成行
  // 四二顶：二简行 + 全码行（组内序：非二简按频序，二简最后）
  // 三定：一简行 + 二简行 + 全码行（组内序：非简码按频序，二简/一简最后）
  const mkRows = (simple: Map<number, CharEntry>, withYijian: boolean) => {
    const rows: [string, string][] = []
    // 简码字集合（组内排最后）：二简字 + (三定时)一简字
    const simpleCharSet = new Set<string>()
    for (const [, c] of simple) simpleCharSet.add(c.ch)
    if (withYijian) for (const ch of yijianChars) simpleCharSet.add(ch)
    if (withYijian) {
      for (const [k, ch] of yijian) rows.push([ch, k])
    }
    for (const [p, c] of simple) {
      if (withYijian && yijianChars.has(c.ch)) continue
      rows.push([c.ch, codeOf.get(c.ch)!.slice(0, 2)])
    }
    // 全码行：按code分组
    const groups3 = new Map<string, CharEntry[]>()
    for (const e of chars) {
      const code = codeOf.get(e.ch)!
      let b = groups3.get(code)
      if (!b) { b = []; groups3.set(code, b) }
      b.push(e)
    }
    for (const [code, b] of groups3) {
      b.sort(cmp)
      const nonSimple = b.filter((e) => !simpleCharSet.has(e.ch))
      const simples = b.filter((e) => simpleCharSet.has(e.ch))
      for (const e of nonSimple) rows.push([e.ch, code])
      for (const e of simples) rows.push([e.ch, code])
    }
    // 排序：按code字符串序（同code保持组内序 → 稳定排序）
    const indexed = rows.map((r, i) => ({ r, i }))
    indexed.sort((a, b) => {
      const c = a.r[1] < b.r[1] ? -1 : a.r[1] > b.r[1] ? 1 : 0
      return c !== 0 ? c : a.i - b.i
    })
    return indexed.map((x) => x.r)
  }

  const rows42 = mkRows(simple42, false)
  const rowsSD = mkRows(simpleSDMap, true)
  return {
    s42: rows42.map(([ch, code]) => ch + '\t' + code).join('\n') + '\n',
    sanDing: rowsSD.map(([ch, code]) => ch + '\t' + code).join('\n') + '\n',
    yijian,
    simpleChars42: new Set([...simple42.values()].map((c) => c.ch)),
  }
}
