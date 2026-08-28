// 提升候选分析：副根/多主根次根 使用统计 + 拼音音托
import { readFileSync } from 'fs'
import { loadSchemeData } from './core'

const sd = loadSchemeData('/workspace/奕码_1.2.yaml')
const splits: any[] = JSON.parse(readFileSync('/workspace/opt/splits_1.2.json', 'utf8'))
const freqMap = new Map<string, number>()
for (const line of readFileSync('/workspace/CHS/data/kc6000.txt', 'utf8').split(/\r?\n/)) {
  const m = line.match(/^(\S+)\t(\d+)$/)
  if (m && m[1].length === 1) freqMap.set(m[1], parseInt(m[2]))
}

// 拼音字典
const pyDict = new Map<string, string>()
for (const line of readFileSync('/workspace/opt/dictionary_ext.txt', 'utf8').split(/\r?\n/)) {
  const [ch, py] = line.split('\t')
  if (ch && py) pyDict.set(ch, py)
}
function yintuo(pinyin: string): string | null {
  if (!pinyin || !/^[a-z]+[1-5]$/.test(pinyin)) return null
  const py = pinyin.slice(0, -1)
  if (py.startsWith('zh')) return py.replace(/^zh/, '')[0] ?? null
  if (py.startsWith('ch')) return 'c'
  if (py.startsWith('sh')) return 's'
  if (py === 'yi') return 'i'
  if (py === 'yu') return 'v'
  if (py === 'wu') return 'u'
  return py[0]
}

// 使用统计：每个元素在 top6000 与全部中的使用次数和字频
const useCnt = new Map<string, number>()
const useTop = new Map<string, number>()
const useFreq = new Map<string, number>()
for (const e of splits) {
  const f = freqMap.get(e.char) ?? 0
  const seen = new Set<string>()
  for (const s of e.seq) {
    useCnt.set(s.element, (useCnt.get(s.element) ?? 0) + 1)
    if (f > 0) useFreq.set(s.element, (useFreq.get(s.element) ?? 0) + f)
    if (!seen.has(s.element)) { seen.add(s.element); useTop.set(s.element, (useTop.get(s.element) ?? 0) + 1) }
  }
}

const strokeSet = new Set(['1', '2', '3', '4', '5', '6'])
const cands: any[] = []
for (const g of sd.groups) {
  const primary = g.primary
  for (const el of g.direct.slice(1).concat(g.elements.filter((e) => !g.direct.includes(e)))) {
    if (strokeSet.has(el)) continue
    const py = pyDict.get(el) ?? null
    cands.push({
      el, group: g.code, primary, isDirect: g.direct.includes(el),
      cnt: useCnt.get(el) ?? 0, freq: useFreq.get(el) ?? 0,
      py, small: py ? yintuo(py) : null,
    })
  }
}
cands.sort((a, b) => b.freq - a.freq)
console.log('候选提升元素数:', cands.length, '（有拼音:', cands.filter((c) => c.py).length, '）')
console.log('\n=== top60 候选（按top6000加权使用频次） ===')
console.log('元素  组码  组内主根  直接定义  使用次数  加权频次  拼音  音托')
for (const c of cands.slice(0, 60)) {
  console.log(`${c.el}  ${c.group}  ${c.primary}  ${c.isDirect ? '是' : '别名'}  ${c.cnt}  ${c.freq}  ${c.py ?? '-'}  ${c.small ?? '-'}`)
}
// 汇总：音托字母分布（前80候选）
const dist: Record<string, number> = {}
for (const c of cands.slice(0, 80)) if (c.small) dist[c.small] = (dist[c.small] ?? 0) + 1
console.log('\n前80候选音托分布:', JSON.stringify(dist))
console.log('前80候选无拼音数:', cands.slice(0, 80).filter((c) => !c.py).map((c) => c.el).join(' '))
