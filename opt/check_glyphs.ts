import { readFileSync } from 'fs'
import { load } from 'js-yaml'
import * as chai from 'hanzi-chai'
import { normalizeConfig } from './build_splits'

const config = normalizeConfig(load(readFileSync('/workspace/奕码_1.2.yaml', 'utf8')) as any)
const repResult: any = chai.获取字库(config)
const inner = (repResult.value as any).repertoire as Record<string, any>
const official = new Set<string>()
for (const line of readFileSync('/workspace/奕码三定-官方最新修正版-1.2.txt', 'utf8').split(/\r?\n/)) {
  const m = line.match(/^(.)\t(.+)$/)
  if (m && m[2].length === 3) official.add(m[1])
}
const mine = new Set<string>(JSON.parse(readFileSync('/workspace/opt/splits_1.2.json', 'utf8')).map((e: any) => e.char))
const missing = [...official].filter(c => !mine.has(c))
let noGlyph = 0, hasGlyph = 0
const noGlyphList: string[] = []
for (const c of missing) {
  if (inner[c]?.glyph) hasGlyph++
  else { noGlyph++; noGlyphList.push(c) }
}
console.log(`有字形: ${hasGlyph}, 无字形: ${noGlyph}`)
console.log('无字形:', noGlyphList.join(' '))
// 官方码表里这些字的编码（看是否等于字根本身的 大+小+小）
const off3 = new Map<string, string>()
for (const line of readFileSync('/workspace/奕码三定-官方最新修正版-1.2.txt', 'utf8').split(/\r?\n/)) {
  const m = line.match(/^(.)\t(.+)$/)
  if (m && m[2].length === 3) off3.set(m[1], m[2])
}
console.log('\n缺失字官方编码样例:')
for (const c of missing.slice(0, 50)) console.log(`${c} ${off3.get(c)}`)
