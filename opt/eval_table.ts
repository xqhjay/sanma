import { readFileSync } from 'fs'
import { parseCodeTable, evaluateScheme } from '/workspace/CHS/src/utils/evaluate.ts'

export function loadFreq(): Map<string, number> {
  const freqMap = new Map<string, number>()
  for (const line of readFileSync('/workspace/CHS/data/kc6000.txt', 'utf8').split(/\r?\n/)) {
    const m = line.match(/^(\S+)\t(\d+)$/)
    if (m && m[1].length === 1) freqMap.set(m[1], parseInt(m[2]))
  }
  return freqMap
}

export interface SectionStat {
  label: string
  totalFreq: number
  cd1: number; cd2: number; cd3: number
  cd2Weight: number          // 二码字加权比重(%)
  simpleCollision: number    // 出简重数（简全同出）
  simpleCollisionExclFull: number  // 出简重数（出简不出全）
  scWeight: number
  lack: number
}

export function evalTable(content: string, freqMap: Map<string, number>): SectionStat[] {
  const { codeMap, codeToChars } = parseCodeTable(content, 'table.txt')
  const result = evaluateScheme(codeMap, freqMap, ";'456789", 4, undefined, codeToChars)
  const lines = result.lines
  const stats: SectionStat[] = []
  const mk = (label: string, items: any[], totalFreq: number): SectionStat => {
    let cd1 = 0, cd2 = 0, cd3 = 0, w2 = 0, sc = 0, sce = 0, wsc = 0, lack = 0
    for (const it of items) {
      if (it.isLack) { lack++; continue }
      if (it.codeLen === 1) cd1++
      else if (it.codeLen === 2) { cd2++; w2 += it.freq }
      else if (it.codeLen === 3) cd3++
      if (it.simpleCollision > 1) { sc++; wsc += it.freq }
      if (it.simpleCollisionExclFull > 1) sce++
    }
    return {
      label, totalFreq, cd1, cd2, cd3,
      cd2Weight: totalFreq > 0 ? w2 / totalFreq * 100 : 0,
      simpleCollision: sc, simpleCollisionExclFull: sce,
      scWeight: totalFreq > 0 ? wsc / totalFreq * 100 : 0, lack,
    }
  }
  const labels = ['1~300', '301~500', '501~1500', '1501~3000', '3001~6000']
  lines.forEach((l: any, i: number) => stats.push(mk(labels[i], l.items, l.totalFreq)))
  // 小计: 前1500 = 前3行；总计: 全部
  const subItems = lines.slice(0, 3).flatMap((l: any) => l.items)
  const subFreq = lines.slice(0, 3).reduce((s: number, l: any) => s + l.totalFreq, 0)
  stats.push(mk('小计(1~1500)', subItems, subFreq))
  const allItems = lines.flatMap((l: any) => l.items)
  const allFreq = lines.reduce((s: number, l: any) => s + l.totalFreq, 0)
  stats.push(mk('总计(1~6000)', allItems, allFreq))
  return stats
}

export function printStats(title: string, stats: SectionStat[]) {
  console.log(`\n===== ${title} =====`)
  console.log('区间        | 二码字 | 二码加权% | 出简重(同出) | 出简重(不出全) | 缺字')
  for (const s of stats) {
    console.log(
      `${s.label.padEnd(10)} | ${String(s.cd2).padStart(4)} | ${s.cd2Weight.toFixed(2).padStart(8)} | ${String(s.simpleCollision).padStart(8)} | ${String(s.simpleCollisionExclFull).padStart(10)} | ${s.lack}`
    )
  }
}

if (process.argv[1] && process.argv[1].includes('eval_table')) {
  const freqMap = loadFreq()
  console.log('字频表字数:', freqMap.size)
  const tablePath = process.argv[2]
  const content = readFileSync(tablePath, 'utf8')
  const stats = evalTable(content, freqMap)
  printStats(tablePath, stats)
}
