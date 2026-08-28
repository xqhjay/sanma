import { readFileSync } from 'fs'
import { loadSchemeData } from './core'
const sd = loadSchemeData('/workspace/奕码_1.2.yaml')
const splits: any[] = JSON.parse(readFileSync('/workspace/opt/splits_1.2.json', 'utf8'))
const freqMap = new Map<string, number>()
for (const line of readFileSync('/workspace/CHS/data/kc6000.txt', 'utf8').split(/\r?\n/)) {
  const m = line.match(/^(\S+)\t(\d+)$/)
  if (m && m[1].length === 1) freqMap.set(m[1], parseInt(m[2]))
}
const use = new Map<string, { f: number; chars: string[] }>()
for (const e of splits) {
  const f = freqMap.get(e.char) ?? 0
  if (!f) continue
  for (const s of e.seq) {
    let u = use.get(s.element)
    if (!u) { u = { f: 0, chars: [] }; use.set(s.element, u) }
    u.f += f
    if (u.chars.length < 6 && !u.chars.includes(e.char)) u.chars.push(e.char)
  }
}
const cands: any[] = []
for (const g of sd.groups) {
  for (const el of g.elements) {
    if (el === g.primary) continue
    if ('123456'.includes(el)) continue
    const u = use.get(el)
    if (!u || u.f < 300000) continue
    cands.push({ el, g: g.code, primary: g.primary, f: u.f, chars: u.chars.join(''), cp: el.codePointAt(0)! })
  }
}
cands.sort((a, b) => b.f - a.f)
for (const c of cands) console.log('U+' + c.cp.toString(16).toUpperCase().padStart(4, '0'), JSON.stringify(c.el), '组=' + c.g, '主根=' + c.primary, '频=' + c.f, '例:' + c.chars)
