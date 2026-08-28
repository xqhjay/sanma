import { readFileSync, writeFileSync } from 'fs'
import { load } from 'js-yaml'
import * as chai from 'hanzi-chai'

export function normalizeConfig(config: any) {
  const cfg = JSON.parse(JSON.stringify(config))
  const gc = cfg?.data?.glyph_customization
  if (gc) for (const k of Object.keys(gc)) if (Array.isArray(gc[k])) gc[k] = gc[k][0]
  return cfg
}

export function cp(ch: string) {
  return 'U+' + ch.codePointAt(0)!.toString(16).toUpperCase().padStart(4, '0')
}

export interface SplitEntry {
  char: string
  roots: string[]        // 字根序列（含PUA）
  rootIndices: number[]  // 每个字根用到的码位 index 序列（0=大码,1=小码）
  seq: { element: string; index: number }[]
  freq: number
}

export function loadScheme(yamlPath: string) {
  const rawConfig = load(readFileSync(yamlPath, 'utf8')) as any
  const config = normalizeConfig(rawConfig)
  const dict = chai.获取词典("/workspace/opt/dictionary_ext.txt")
  const repResult: any = chai.获取字库(config)
  if (repResult?.ok !== true) throw new Error('字库错误: ' + repResult?.error?.message)
  const analysisResult: any = chai.获取字形分析结果(config, repResult.value, dict)
  if (analysisResult?.ok !== true) throw new Error('分析错误: ' + analysisResult?.error?.message)
  const pinyin = chai.获取拼音分析结果(config, dict)
  const assembled = chai.获取组装结果(config, pinyin, analysisResult.value as any)
  return { config, assembled }
}

// 解析 form.mapping：元素 → 码位列表
export function buildResolver(mapping: Record<string, any>) {
  const resolveAt = (el: string, index: number, depth = 0): string => {
    if (depth > 10) throw new Error(`映射解析过深: ${cp(el)}`)
    const v = mapping[el]
    if (v === undefined) throw new Error(`映射缺失: ${cp(el)} (${el})`)
    if (typeof v === 'string') return v[index]
    if (Array.isArray(v)) {
      const item = v[index]
      if (item === undefined) throw new Error(`映射越界: ${cp(el)}[${index}]`)
      if (typeof item === 'string') return item
      return resolveAt(item.element, item.index, depth + 1)
    }
    // {element: X} 别名
    return resolveAt(v.element, index, depth + 1)
  }
  const codeOf = (el: string): string => resolveAt(el, 0) + resolveAt(el, 1)
  return { resolveAt, codeOf }
}

// ===== 主流程 =====
const yamlPath = process.argv[2] || '/workspace/奕码_1.2.yaml'
const outPath = process.argv[3] || '/workspace/opt/splits_1.2.json'
const { config, assembled } = loadScheme(yamlPath)
const resolver = buildResolver(config.form.mapping)

const entries: any[] = []
let noResolve = 0
const elemUsage = new Map<string, number>()
for (const item of assembled as any[]) {
  if ([...item.词].length !== 1) continue
  const seq: { element: string; index: number }[] = item.元素序列
  for (const s of seq) elemUsage.set(s.element, (elemUsage.get(s.element) ?? 0) + 1)
  let code: string
  try {
    code = seq.map((s) => resolver.resolveAt(s.element, s.index)).join('')
  } catch (e: any) {
    noResolve++
    if (noResolve <= 10) console.error('解析失败', item.词, e.message)
    continue
  }
  entries.push({ char: item.词, seq, code, freq: item.频率 })
}
console.log(`共 ${entries.length} 字，编码解析失败 ${noResolve}`)

// 元素使用统计：哪些映射键从未被使用
const unused: string[] = []
for (const k of Object.keys(config.form.mapping)) {
  if (!elemUsage.has(k)) unused.push(k)
}
console.log(`映射键总数 ${Object.keys(config.form.mapping).length}，未直接使用 ${unused.length}`)
console.log('未使用样例:', unused.slice(0, 30).map(cp).join(' '))

// 与官方三定码表比对
const official = new Map<string, string>()
for (const line of readFileSync('/workspace/奕码三定-官方最新修正版-1.2.txt', 'utf8').split(/\r?\n/)) {
  const m = line.match(/^(\S+)\t(.+)$/)
  if (m && m[2].length === 3) official.set(m[1], m[2])
}
let match = 0, mismatch = 0, mineOnly = 0, officialOnly = 0
const mismatchList: string[] = []
for (const e of entries) {
  const off = official.get(e.char)
  if (off === undefined) { mineOnly++; continue }
  if (off === e.code) match++
  else { mismatch++; if (mismatchList.length < 30) mismatchList.push(`${e.char}: mine=${e.code} off=${off}`) }
}
for (const [ch] of official) if (!entries.find((e) => e.char === ch)) officialOnly++
console.log(`\n与官方1.2三定全码比对: 匹配=${match} 不匹配=${mismatch} 我有他无=${mineOnly} 他有我无=${officialOnly}`)
console.log(mismatchList.join('\n'))

writeFileSync(outPath, JSON.stringify(entries, null, 0))
console.log(`拆分+编码已写入 ${outPath}`)
