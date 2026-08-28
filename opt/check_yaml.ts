// 比对：新YAML驱动hanzi-chai的产出编码 === 自产码表全码
import { readFileSync } from 'fs'

const tag = process.argv[2] ?? 'C'
const splits: any[] = JSON.parse(readFileSync(`/workspace/opt/splits_opt_${tag}.json`, 'utf8'))

// 自产三定表全码（3码行）
const mine = new Map<string, string>()
for (const line of readFileSync(`/workspace/opt/gen_sd_${tag}.txt`, 'utf8').split(/\r?\n/)) {
  const m = line.match(/^(.)\t([a-z]{3})$/)
  if (m) {
    if (!mine.has(m[1])) mine.set(m[1], m[2]) // 首次出现（最短码优先）
  }
}
// splits全码（无简码概念）
let match = 0, mismatch = 0, onlyS = 0, onlyM = 0
const bad: string[] = []
for (const e of splits) {
  const m = mine.get(e.char)
  if (m === undefined) { onlyS++; continue }
  if (m === e.code) match++
  else { mismatch++; if (bad.length < 20) bad.push(`${e.char}: yaml=${e.code} mine=${m}`) }
}
for (const [ch] of mine) if (!splits.find((e) => e.char === ch)) onlyM++
console.log(`yaml拆分=${splits.length} 表内3码字=${mine.size}`)
console.log(`匹配=${match} 不匹配=${mismatch} yaml独有=${onlyS} 表独有=${onlyM}`)
console.log(bad.join('\n'))
