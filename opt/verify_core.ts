// 验证：官方布局 + 最优二简分配 → 快速评估 vs 官方基线
import { loadSchemeData, loadChars, fastEval, createContext, KEY_IDX } from './core'
import { loadFreq } from './eval_table'

const sd = loadSchemeData('/workspace/奕码_1.2.yaml')
const freqMap = loadFreq()
const chars = loadChars('/workspace/opt/splits_1.2.json', sd, freqMap)
const top = chars.filter((c) => c.rank > 0).sort((a, b) => a.rank - b.rank)
console.log(`组数=${sd.groups.length} top6000=${top.length} 全部=${chars.length}`)

// 官方布局
const big = new Uint8Array(sd.groups.length)
const small = new Uint8Array(sd.groups.length)
sd.groups.forEach((g, i) => {
  big[i] = KEY_IDX.get(g.code[0])!
  small[i] = KEY_IDX.get(g.code[1])!
})

const ctx = createContext(top)
// 计时
const t0 = Date.now()
const N = 200
for (let i = 0; i < N; i++) fastEval(ctx, big, small)
const dt = (Date.now() - t0) / N
console.log(`单次评估耗时 ${dt.toFixed(3)}ms`)

const r = fastEval(ctx, big, small, undefined, true)
console.log('\n官方布局 + 最优二简分配（快速评估）:')
console.log(`前1500二码字=${r.cd2_1500} (官方563)`)
console.log(`前1500二码加权=${r.w2_1500.toFixed(2)}% (官方70.06%)`)
console.log(`1501~3000出简重=${r.sc_1501_3000} (官方5)`)
console.log(`总出简重=${r.sc_total} (官方324)`)
console.log(`前1500出简重=${r.sc_1500} (须0)`)
console.log(`前缀覆盖=${r.prefixes}/676`)
console.log(`score=${r.score.toFixed(0)}`)

// 每键组数分布
const load: Record<string, number> = {}
sd.groups.forEach((g) => { load[g.code[0]] = (load[g.code[0]] ?? 0) + 1 })
console.log('\n每键组数:', JSON.stringify(load))

// 未使用组（top6000中未出现的元素组）—— 删减候选
const used = new Set<number>()
for (const c of chars) c.g.forEach((g) => used.add(g))
const unusedGroups = sd.groups.filter((g) => !g.elements.some((e) => used.has(sd.groupOfElement.get(e)!)))
console.log(`\n完全未使用的组: ${unusedGroups.length}`)
for (const g of unusedGroups) {
  console.log(`  ${g.code}: ${g.elements.map((e) => e.codePointAt(0) > 0xe000 ? 'U+' + e.codePointAt(0).toString(16) : e).join(',')}`)
}
