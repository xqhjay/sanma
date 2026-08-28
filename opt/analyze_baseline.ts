import { readFileSync } from 'fs'
import { evalTable, loadFreq, printStats } from './eval_table'

const freqMap = loadFreq()
const freqRank = new Map<string, number>()
;[...freqMap.entries()].sort((a, b) => b[1] - a[1]).forEach(([c], i) => freqRank.set(c, i + 1))

// 1. 官方表原样测评已得基线。现在用我的拆分重建表（同码、同频降序），看数字是否一致
const splits: any[] = JSON.parse(readFileSync('/workspace/opt/splits_1.2.json', 'utf8'))

// 生成与官方四二顶同构的表：全码 + 二简（每前缀取频次最高者，仅在top6000内竞争? 官方规则是全部字中频次最高）
// 官方表二简：676个二码字 = 每个前缀组的频次冠军。用词典频次还是kc6000？验证：官方二码字集合 vs 用kc6000算的冠军
const official2 = new Map<string, string>()
for (const line of readFileSync('/workspace/奕码四二顶-官方最新修正版-1.2.txt', 'utf8').split(/\r?\n/)) {
  const m = line.match(/^(.)\t(.+)$/)
  if (m && m[2].length === 2) official2.set(m[2], m[1])
}
// 我算的冠军（用kc6000频次，不在kc6000的算0）
const freq = (c: string) => freqMap.get(c) ?? 0
const prefixBest = new Map<string, { ch: string; f: number }>()
for (const e of splits) {
  const p = e.code.slice(0, 2)
  const f = freq(e.char)
  const cur = prefixBest.get(p)
  if (!cur || f > cur.f || (f === cur.f && e.char < cur.ch)) prefixBest.set(p, { ch: e.char, f })
}
let agree = 0, disagree = 0
const disList: string[] = []
for (const [p, { ch }] of prefixBest) {
  const off = official2.get(p)
  if (off === ch) agree++
  else { disagree++; if (disList.length < 15) disList.push(`${p}: 官方=${off}(rank${freqRank.get(off ?? '') ?? '-'}) 我的=${ch}(rank${freqRank.get(ch) ?? '-'})`) }
}
console.log(`二简归属比对: 一致=${agree} 不一致=${disagree}`)
console.log(disList.join('\n'))

// 2. 官方表同码组内排序：验证是否频次降序
const codeChars = new Map<string, string[]>()
for (const line of readFileSync('/workspace/奕码四二顶-官方最新修正版-1.2.txt', 'utf8').split(/\r?\n/)) {
  const m = line.match(/^(.)\t(.+)$/)
  if (m && m[2].length === 3) {
    if (!codeChars.has(m[2])) codeChars.set(m[2], [])
    codeChars.get(m[2])!.push(m[1])
  }
}
let sortedGroups = 0, unsortedGroups = 0
for (const [code, chars] of codeChars) {
  if (chars.length < 2) continue
  const inFreq = chars.filter((c) => freqMap.has(c))
  if (inFreq.length < 2) continue
  let ok = true
  for (let i = 1; i < inFreq.length; i++) if (freq(inFreq[i]) > freq(inFreq[i - 1])) { ok = false; break }
  if (ok) sortedGroups++
  else unsortedGroups++
}
console.log(`\n官方表同码组内排序（限top6000成员）: 频次降序组=${sortedGroups} 非降序组=${unsortedGroups}`)

// 3. 1501~3000 的 5 个出简重字是谁
async function main() {
  const { parseCodeTable, evaluateScheme } = await import('/workspace/CHS/src/utils/evaluate.ts')
  const content = readFileSync('/workspace/奕码四二顶-官方最新修正版-1.2.txt', 'utf8')
  const { codeMap, codeToChars } = parseCodeTable(content, 't.txt')
  const result: any = evaluateScheme(codeMap, freqMap, ";'456789", 4, undefined, codeToChars)
  const line4 = result.lines[3] // 1501~3000
  console.log('\n1501~3000 出简重字:')
  for (const it of line4.items) {
    if (it.simpleCollision > 1) {
      console.log(`${it.char}(rank${freqRank.get(it.char)}) 码=${it.code} 冲突位=${it.simpleCollision} 组=${codeToChars.get(it.longestCode)?.join(',')}`)
    }
  }
  // 3001~6000 出简重样例
  const line5 = result.lines[4]
  const l5 = line5.items.filter((it: any) => it.simpleCollision > 1)
  console.log(`\n3001~6000 出简重 ${l5.length} 个，样例:`)
  for (const it of l5.slice(0, 10)) {
    console.log(`${it.char}(rank${freqRank.get(it.char)}) 码=${it.code} 组=${codeToChars.get(it.longestCode)?.join(',')}`)
  }
  // 组大小分布
  const sizeDist: Record<number, number> = {}
  for (const [, chars] of codeToChars) {
    const n = chars.filter((c) => freqMap.has(c)).length
    if (n >= 2) sizeDist[n] = (sizeDist[n] ?? 0) + 1
  }
  console.log('\ntop6000内同码组大小分布:', JSON.stringify(sizeDist))
  // 大组列表
  const bigGroups = [...codeToChars.entries()].filter(([, cs]) => cs.filter((c) => freqMap.has(c)).length >= 5)
  console.log('≥5字同码组:', bigGroups.length)
  for (const [code, cs] of bigGroups.slice(0, 15)) {
    console.log(`  ${code}: ${cs.map((c) => `${c}(${freqRank.get(c) ?? '-'})`).join(' ')}`)
  }
}
main()
