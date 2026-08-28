import { readFileSync } from 'fs'
import { load } from 'js-yaml'
import * as chai from 'hanzi-chai'

// 兼容转换：新版拆分系统的 glyph_customization 数组格式 → 取首个字形定义
export function normalizeConfig(config: any) {
  const cfg = JSON.parse(JSON.stringify(config))
  const gc = cfg?.data?.glyph_customization
  if (gc) {
    for (const k of Object.keys(gc)) {
      if (Array.isArray(gc[k])) gc[k] = gc[k][0]
    }
  }
  return cfg
}

const yamlPath = process.argv[2] || '/workspace/奕码_1.2.yaml'
const rawConfig = load(readFileSync(yamlPath, 'utf8')) as any
const config = normalizeConfig(rawConfig)

const dict = chai.获取词典()
const repResult: any = chai.获取字库(config)
if (repResult?.ok !== true) { console.error('字库错误:', repResult?.error?.message); process.exit(1) }
const repertoire = repResult.value
console.log('字库 ok:', repertoire.constructor?.name)

const analysisResult: any = chai.获取字形分析结果(config, repertoire, dict)
if (analysisResult?.ok !== true) { console.error('分析错误:', analysisResult?.error?.message); process.exit(1) }
const analysis = analysisResult.value
console.log('分析 ok:', analysis.constructor?.name, analysis instanceof Map ? `size=${analysis.size}` : (Array.isArray(analysis) ? `len=${analysis.length}` : Object.keys(analysis).length))

const pinyin = chai.获取拼音分析结果(config, dict)
console.log('拼音分析 len:', pinyin.length)

const assembled = chai.获取组装结果(config, pinyin, analysis as any)
console.log('组装条目 len:', assembled.length)
console.log('样例:')
for (const item of assembled.slice(0, 3)) {
  console.log(JSON.stringify(item))
}
