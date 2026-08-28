import { readFileSync } from 'fs'
import { load } from 'js-yaml'

const yaml = load(readFileSync('/workspace/奕码_1.2.yaml', 'utf8')) as any
const mapping: Record<string, any> = yaml.form.mapping

// 拼音字典
const pyDict = new Map<string, string>()
for (const line of readFileSync('/workspace/opt/dictionary_ext.txt', 'utf8').split(/\r?\n/)) {
  const [ch, py] = line.split('\t')
  if (ch && py) pyDict.set(ch, py)
}

function cp(ch: string) {
  return 'U+' + ch.codePointAt(0)!.toString(16).toUpperCase().padStart(4, '0')
}

// 解析映射：键 → [大码, 小码] 或 null（meta/无法解析）
function resolveCode(el: string, memo = new Map<string, [string, string] | null>()): [string, string] | null {
  if (memo.has(el)) return memo.get(el)!
  if (memo.size > 2000) return null
  memo.set(el, null) // 防环
  const v = mapping[el]
  if (v === undefined) return null
  let result: [string, string] | null = null
  if (typeof v === 'string' && v.length === 2) result = [v[0], v[1]]
  else if (typeof v === 'string' && v.length === 1) result = [v[0], v[0]] // 首字母-a: a 这类
  else if (Array.isArray(v)) {
    const parts: string[] = []
    for (const item of v) {
      if (typeof item === 'string') parts.push(item)
      else if (item && typeof item === 'object' && 'element' in item) {
        const r = resolveCode(item.element, memo)
        if (r) parts.push(r[item.index ?? 0])
      }
    }
    if (parts.length === 2) result = [parts[0], parts[1]]
  } else if (v && typeof v === 'object' && 'element' in v) {
    const r = resolveCode(v.element, memo)
    if (r) result = r
  }
  memo.set(el, result)
  return result
}

// 音托规则
function yintuo(pinyin: string): string | null {
  if (!pinyin || !/^[a-z]+[1-5]$/.test(pinyin)) return null
  const py = pinyin.slice(0, -1)
  if (py.startsWith('zh') || (py.startsWith('z') && py.length > 1)) {
    const final = py.replace(/^zh?/, '')
    return final[0] ?? null
  }
  if (py.startsWith('ch')) return 'c'
  if (py.startsWith('sh')) return 's'
  if (py === 'yi') return 'i'
  if (py === 'yu') return 'v'
  if (py === 'wu') return 'u'
  return py[0]
}

// ===== 统计 =====
const metaSet = new Set<string>()
const strokeSet = new Set(['1', '2', '3', '4', '5', '6'])
for (const k of Object.keys(mapping)) {
  if (/^(首字母|末字母)-/.test(k)) metaSet.add(k)
}

interface RootInfo {
  key: string
  code: [string, string] | null
  isAlias: boolean
  aliasTarget: string | null
  pinyin: string | null
  expectSmall: string | null
}

const roots: RootInfo[] = []
for (const k of Object.keys(mapping)) {
  if (metaSet.has(k)) continue
  const v = mapping[k]
  const isAlias = v && typeof v === 'object' && !Array.isArray(v) && 'element' in v
  const code = resolveCode(k)
  roots.push({
    key: k, code, isAlias,
    aliasTarget: isAlias ? v.element : null,
    pinyin: pyDict.get(k) ?? null,
    expectSmall: null,
  })
}

// 码位 → 根集合
const codeToRoots = new Map<string, string[]>()
for (const r of roots) {
  if (!r.code) continue
  const c = r.code.join('')
  if (!codeToRoots.has(c)) codeToRoots.set(c, [])
  codeToRoots.get(c)!.push(r.key)
}
console.log(`映射键总数: ${Object.keys(mapping).length}`)
console.log(`meta元素(首/末字母): ${metaSet.size}`)
console.log(`实际字根键: ${roots.length}（显式主根 ${roots.filter(r => !r.isAlias).length} + 别名副根 ${roots.filter(r => r.isAlias).length}）`)
console.log(`占用码位数: ${codeToRoots.size} / 650`)
console.log(`归并组数（=占用码位, 含笔画）: ${codeToRoots.size}`)

// 每码位根数分布
const dist: Record<number, number> = {}
for (const [, rs] of codeToRoots) dist[rs.length] = (dist[rs.length] ?? 0) + 1
console.log('每码位根数分布:', JSON.stringify(dist))

// 双根码位（两个不相关主根同码）
const doubleRoots: string[] = []
for (const [c, rs] of codeToRoots) {
  const nonAlias = rs.filter((r) => !mapping[r] || typeof mapping[r] === 'string' || Array.isArray(mapping[r]))
  if (rs.length >= 2) {
    const explicits = rs.filter((r) => typeof mapping[r] === 'string' || Array.isArray(mapping[r]))
    if (explicits.length >= 2) doubleRoots.push(`${c}: ${rs.join(' ')}`)
  }
}
console.log(`\n多主根同码位数: ${doubleRoots.length}`)
console.log(doubleRoots.join('\n'))

// 音托合规（主根：有显式编码且有拼音的）
let checked = 0, compliant = 0
const nonCompliant: string[] = []
for (const r of roots) {
  if (r.isAlias || !r.code || !r.pinyin) continue
  if (strokeSet.has(r.key)) continue
  checked++
  const exp = yintuo(r.pinyin)
  if (exp === r.code[1]) compliant++
  else nonCompliant.push(`${r.key}(${r.pinyin}) 小码=${r.code[1]} 期望=${exp}`)
}
console.log(`\n音托合规率: ${compliant}/${checked} = ${(compliant / checked * 100).toFixed(1)}%`)
console.log('不合规根:')
console.log(nonCompliant.join('\n'))
