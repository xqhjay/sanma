// 生成优化版字根YAML：官方1.2 + SA布局(layout_X.json) → 优化版yaml
// 用法: npx tsx gen_yaml.ts C [输出路径]
import { readFileSync, writeFileSync } from 'fs'
import { load, dump } from 'js-yaml'
import { loadSchemeData } from './core'

const tag = process.argv[2] ?? 'C'
const outPath = process.argv[3] ?? `/workspace/opt/奕码_优化_${tag}.yaml`
const layout = JSON.parse(readFileSync(`/workspace/opt/layout_${tag}.json`, 'utf8'))

const raw = load(readFileSync('/workspace/奕码_1.2.yaml', 'utf8')) as any
const sd = loadSchemeData('/workspace/奕码_1.2.yaml')

// ===== finalCode: 每个元素 → 最终码位 =====
const promoCode = new Map<string, string>()
for (const p of layout.promos ?? []) promoCode.set(p.el, p.code)
const newCodeOfGroup = new Map<number, string>() // oldGroup.id -> newCode
layout.base.forEach((b: any) => {
  const g = sd.groups.find((x) => x.code === b.code)
  if (g) newCodeOfGroup.set(g.id, b.newCode)
})
const finalCode = (el: string): string | null => {
  const pc = promoCode.get(el)
  if (pc) return pc
  const gid = sd.groupOfElement.get(el)
  if (gid === undefined) return null
  return newCodeOfGroup.get(gid) ?? null
}

// ===== 修补 form.mapping =====
const mapping = raw.form.mapping as Record<string, any>
let changedStr = 0, brokenAlias = 0, fixedArr = 0, keptAlias = 0, keptArr = 0
const changes: string[] = []
for (const el of Object.keys(mapping)) {
  const v = mapping[el]
  if (el.startsWith('首字母')) continue           // 拼音meta键
  if (typeof v === 'string' && v.length === 1) continue // 笔画meta键
  const fc = finalCode(el)
  if (!fc) continue
  if (typeof v === 'string' && v.length === 2) {
    if (v !== fc) { mapping[el] = fc; changedStr++; if (changes.length < 8) changes.push(`${el}: ${v}→${fc}`) }
  } else if (v && typeof v === 'object' && !Array.isArray(v) && 'element' in v) {
    // 别名 {element: X}
    const target = finalCode(v.element)
    if (target === fc) keptAlias++
    else { mapping[el] = fc; brokenAlias++ }
  } else if (Array.isArray(v)) {
    // 数组：逐位校验 [big, small]
    let ok = true
    const nv: any[] = []
    for (let i = 0; i < 2; i++) {
      const item = v[i]
      if (typeof item === 'string') {
        if (item === fc[i]) nv.push(item)
        else { nv.push(fc[i]); ok = false }
      } else if (item && typeof item === 'object' && 'element' in item) {
        const t = finalCode(item.element)
        if (t && t[item.index ?? 0] === fc[i]) nv.push(item)
        else { nv.push(fc[i]); ok = false }
      } else { nv.push(fc[i]); ok = false }
    }
    if (ok) keptArr++
    else { mapping[el] = nv.every((x) => typeof x === 'string') ? fc : nv; fixedArr++; changes.push(`[arr] ${el} → ${fc}`) }
  }
}
console.log(`直接码改写=${changedStr} 别名保留=${keptAlias} 别名断链转直=${brokenAlias} 数组保留=${keptArr} 数组修正=${fixedArr}`)
console.log('样例:', changes.join(' | '))

// ===== 自检：用新mapping解析，必须全部等于finalCode =====
function resolveAt(el: string, index: number, depth = 0): string {
  if (depth > 10) throw new Error('解析过深: ' + el)
  const v = mapping[el]
  if (v === undefined) throw new Error('映射缺失: ' + el)
  if (typeof v === 'string') return v[index]
  if (Array.isArray(v)) {
    const item = v[index]
    if (typeof item === 'string') return item
    return resolveAt(item.element, item.index, depth + 1)
  }
  return resolveAt(v.element, index, depth + 1)
}
let checked = 0, bad = 0
for (const el of Object.keys(mapping)) {
  if (el.startsWith('首字母')) continue
  const v = mapping[el]
  if (typeof v === 'string' && v.length === 1) continue
  const fc = finalCode(el)
  if (!fc) continue
  try {
    const c = resolveAt(el, 0) + resolveAt(el, 1)
    checked++
    if (c !== fc) { bad++; if (bad <= 5) console.log('!! 不一致', JSON.stringify(el), c, '期望', fc) }
  } catch (e: any) { bad++; console.log('!! 解析失败', JSON.stringify(el), e.message) }
}
console.log(`自检: ${checked}个元素解析, 不一致=${bad}`)

// ===== 更新info并输出 =====
raw.info.name = '奕码·优化版'
raw.info.version = '2.0'
raw.info.author = '小泥巴 (原作) / SA优化'
raw.info.description = `乱序音托双编三码定长形码输入方案（基于奕码1.2优化：${layout.promos?.length ?? 0}个高频副根提升为独立字根组+大码重排）`
const out = dump(raw, { lineWidth: -1, noRefs: true })
writeFileSync(outPath, out)
console.log(`已写入 ${outPath} (${out.length}字节)`)

// ===== 码位占用统计 =====
const usedCodes = new Map<string, number>()
for (const el of Object.keys(mapping)) {
  if (el.startsWith('首字母')) continue
  const v = mapping[el]
  if (typeof v === 'string' && v.length === 1) continue
  const fc = finalCode(el)
  if (fc) usedCodes.set(fc, (usedCodes.get(fc) ?? 0) + 1)
}
const groups2 = [...usedCodes.keys()].length
console.log(`归并组数(码位数)=${groups2} / 320上限`)
const dup2 = [...usedCodes.entries()].filter(([, c]) => c > 1).length
console.log(`多元素组数=${dup2}`)
