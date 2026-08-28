import { readFileSync } from 'fs'
const official = new Set<string>()
for (const line of readFileSync('/workspace/奕码三定-官方最新修正版-1.2.txt', 'utf8').split(/\r?\n/)) {
  const m = line.match(/^(.)\t(.+)$/)
  if (m && m[2].length === 3) official.add(m[1])
}
const mine = new Set<string>(JSON.parse(readFileSync('/workspace/opt/splits_1.2.json', 'utf8')).map((e: any) => e.char))
const missing = [...official].filter(c => !mine.has(c))
console.log('缺失字数:', missing.length)
console.log(missing.map(c => `${c}(U+${c.codePointAt(0)!.toString(16)})`).join(' '))
// 字典里有没有这些字
const dictLines = readFileSync('/workspace/opt/node_modules/hanzi-chai/dist/data/dictionary.txt', 'utf8').split(/\r?\n/)
console.log('字典行数:', dictLines.length)
console.log('字典前3行:', dictLines.slice(0, 3))
const inDict = missing.filter(c => dictLines.some(l => l.startsWith(c)))
console.log('缺失但在字典中:', inDict.length)
