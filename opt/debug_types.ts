import { readFileSync } from 'fs'
import { load } from 'js-yaml'
import * as chai from 'hanzi-chai'
import { inflate } from 'pako'

const config = load(readFileSync('/workspace/奕码_1.2.yaml', 'utf8')) as any
const repResult: any = chai.获取字库(config)
const repertoire = repResult.value
// 检查内部结构
const inner = (repertoire as any).repertoire
console.log('inner size:', Object.keys(inner).length)
// 找出非 compound 且无 strokes 的字形
const bad: string[] = []
for (const [ch, info] of Object.entries(inner as Record<string, any>)) {
  const g = info.glyph
  if (g && g.type !== 'compound' && g.strokes === undefined) bad.push(`${ch}(U+${ch.codePointAt(0)}) type=${g.type}`)
}
console.log('bad glyphs:', bad.length)
console.log(bad.slice(0, 40).join(' '))
// type 分布
const dist: Record<string, number> = {}
for (const [, info] of Object.entries(inner as Record<string, any>)) {
  const t = info.glyph?.type ?? 'none'
  dist[t] = (dist[t] ?? 0) + 1
}
console.log('type dist:', dist)
