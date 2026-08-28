// 对比：我们的最优二简 vs 官方二简，找w2损失来源
import { readFileSync } from 'fs'
import { loadSchemeData, loadChars, fastEval, createContext, KEY_IDX, KEYS } from './core'
import { loadFreq } from './eval_table'

const sd = loadSchemeData('/workspace/奕码_1.2.yaml')
const freqMap = loadFreq()
const chars = loadChars('/workspace/opt/splits_1.2.json', sd, freqMap)
const top = chars.filter((c) => c.rank > 0).sort((a, b) => a.rank - b.rank)
const big = new Uint8Array(sd.groups.length)
const small = new Uint8Array(sd.groups.length)
sd.groups.forEach((g, i) => { big[i] = KEY_IDX.get(g.code[0])!; small[i] = KEY_IDX.get(g.code[1])! })

const ctx = createContext(top)
const r = fastEval(ctx, big, small, undefined, true)
const ourSimple = new Map<string, string>() // 2code -> char
for (const [p, idx] of r.simpleOf!) {
  const c1 = Math.floor(p / 26), c2 = p % 26
  ourSimple.set(KEYS[c1] + KEYS[c2], top[idx].ch)
}
// 官方二简
const offSimple = new Map<string, string>()
for (const line of readFileSync('/workspace/奕码四二顶-官方最新修正版-1.2.txt', 'utf8').split(/\r?\n/)) {
  const m = line.match(/^(.)\t(..)$/)
  if (m) offSimple.set(m[2], m[1])
}
const rankOf = new Map(top.map((c) => [c.ch, c.rank]))
const freqOf = (c: string) => freqMap.get(c) ?? 0
let both1500 = 0, loss = 0, gain = 0
const losses: string[] = [], gains: string[] = []
for (const [code, our] of ourSimple) {
  const off = offSimple.get(code)
  if (off === our) continue
  const ourR = rankOf.get(our) ?? 0, offR = rankOf.get(off!) ?? 0
  if (ourR <= 1500 && offR <= 1500) {
    both1500++
    const d = freqOf(our) - freqOf(off!)
    if (d < 0) { loss += d; if (losses.length < 15) losses.push(`${code}: 官方=${off}(${offR}) 我们的=${our}(${ourR}) Δ${d}`) }
    else if (d > 0) { gain += d; if (gains.length < 8) gains.push(`${code}: 官方=${off}(${offR}) 我们的=${our}(${ourR}) Δ${d}`) }
  }
}
console.log(`不一致前缀(双方都在前1500): ${both1500}, w2损失=${loss}, w2收益=${gain}`)
console.log('损失样例:'); console.log(losses.join('\n'))
console.log('收益样例:'); console.log(gains.join('\n'))
// 官方二简字中 rank>1500 的数量 vs 我们的
let offOut = 0, ourOut = 0
for (const [code, our] of ourSimple) {
  const off = offSimple.get(code)!
  if ((rankOf.get(our) ?? 0) > 1500) ourOut++
  if ((rankOf.get(off) ?? 0) > 1500) offOut++
}
console.log(`\n二简字在前1500外: 官方=${offOut} 我们=${ourOut}`)
