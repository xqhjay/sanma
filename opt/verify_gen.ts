// 交叉验证：官方布局 → 生成码表 → 字劫测评 ≈ 快速评估结果
import { writeFileSync } from 'fs'
import { loadSchemeData, loadChars, fastEval, createContext, KEY_IDX, KEYS } from './core'
import { loadFreq, evalTable, printStats } from './eval_table'
import { genTables } from './gen_table'

const sd = loadSchemeData('/workspace/奕码_1.2.yaml')
const freqMap = loadFreq()
const chars = loadChars('/workspace/opt/splits_1.2.json', sd, freqMap)
const top = chars.filter((c) => c.rank > 0).sort((a, b) => a.rank - b.rank)

const big = new Uint8Array(sd.groups.length)
const small = new Uint8Array(sd.groups.length)
sd.groups.forEach((g, i) => {
  big[i] = KEY_IDX.get(g.code[0])!
  small[i] = KEY_IDX.get(g.code[1])!
})

const ctx = createContext(top)
const r = fastEval(ctx, big, small, undefined, true)
console.log('快速评估: cd2_1500=%d w2=%.2f%% sc_mid=%d sc_total=%d sc_1500=%d prefixes=%d',
  r.cd2_1500, r.w2_1500, r.sc_1501_3000, r.sc_total, r.sc_1500, r.prefixes)

const { s42, sanDing, yijian } = genTables({ sd, chars, top, big, small }, KEYS)
writeFileSync('/workspace/opt/gen_42_official.txt', s42)
writeFileSync('/workspace/opt/gen_sd_official.txt', sanDing)
console.log('\n一简(三定):', [...yijian.entries()].map(([k, c]) => k + '=' + c).join(' '))

console.log('\n===== 自产四二顶（官方布局+最优二简）=====')
printStats('四二顶', evalTable(s42, freqMap))
console.log('\n===== 自产三定（官方布局+最优二简+一简）=====')
printStats('三定', evalTable(sanDing, freqMap))
