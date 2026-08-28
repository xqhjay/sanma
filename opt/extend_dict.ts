import { readFileSync, writeFileSync } from 'fs'

// 125 个官方码表有、hanzi-chai 词典没有的字（部首字符+生僻字），补上读音使其可进入拆分管线
const extra: Record<string, string> = {
  匚: 'fang1', 堀: 'ku1', 謦: 'qing3', 坶: 'mu4', 丿: 'pie3', 乇: 'tuo2', 垅: 'long3',
  艹: 'ao3', 廾: 'gong3', 飚: 'biao1', 嬲: 'niao3', 茇: 'ba2', 菸: 'yan1', 冖: 'mi4',
  蠛: 'mie4', 卩: 'jie2', 螓: 'qin2', 丨: 'gun3', 憝: 'dui4', 蚵: 'he2', 蟓: 'xiang4',
  齄: 'zha1', 泶: 'xue2', 跫: 'qiong2', 勹: 'bao1', 冫: 'bing1', 阝: 'fu3', 阢: 'wu4',
  巛: 'chuan1', 冂: 'jiong1', 凵: 'kan3', 囗: 'wei2', 囝: 'jian3', 疋: 'pi3', 搿: 'ge2',
  揎: 'xuan1', 挢: 'jiao3', 擗: 'pi4', 摺: 'zhe2', 拚: 'pan4', 扌: 'shou3', 揞: 'an3',
  欷: 'xi1', 揲: 'she2', 捱: 'ai2', 髟: 'biao1', 谘: 'zi1', 诶: 'ei1', 弪: 'jing4',
  彡: 'shan1', 讠: 'yan2', 屮: 'che4', 哜: 'ji4', 咭: 'ji1', 砦: 'zhai4', 箝: 'qian2',
  氽: 'tun3', 簦: 'deng1', 後: 'hou4', 宀: 'mian2', 舡: 'chuan2', 礻: 'shi4', 丌: 'ji1',
  舨: 'ban3', 夂: 'zhi3', 攵: 'pu1', 佧: 'ka3', 亻: 'ren2', 忄: 'xin1', 辶: 'chuo4',
  渖: 'shen3', 厶: 'si1', 氵: 'shui3', 沲: 'duo2', 彐: 'ji4', 廴: 'yin3', 猓: 'guo3',
  刂: 'dao1', 軎: 'wei4', 猸: 'mei2', 犭: 'quan3', 亠: 'tou2', 甙: 'dai4', 窆: 'bian3',
  榀: 'pin3', 麴: 'qu1', 楱: 'zou4', 镙: 'luo2', 钅: 'jin1', 钸: 'bu1', 钶: 'ke1',
  镟: 'xuan4', 疒: 'ne4', 礤: 'ca3', 痖: 'ya3', 硷: 'jian3', 砩: 'fu2', 磺: 'huang2',
  矽: 'xi1', 榘: 'ju3', 肜: 'rong2', 膪: 'chuang4', 膣: 'zhi4', 朊: 'wan3', 臁: 'lian2',
  馀: 'yu2', 饣: 'shi2', 攴: 'pu1', 灬: 'huo3', 虍: 'hu1', 熳: 'man4', 肀: 'yu4',
  庀: 'pi3', 缋: 'hui4', 衤: 'yi1', 缏: 'bian4', 丬: 'qiang2', 纟: 'si1', 糸: 'mi4',
  缍: 'duo3', 丶: 'zhu3', 鳋: 'sao1', 鲶: 'nian2', 鳆: 'fu4', 醣: 'tang2',
}

const base = readFileSync('/workspace/opt/node_modules/hanzi-chai/dist/data/dictionary.txt', 'utf8')
const lines = base.split(/\r?\n/)
const known = new Set(lines.map((l) => l.split('\t')[0]))
const additions: string[] = []
for (const [ch, py] of Object.entries(extra)) {
  if (!known.has(ch)) additions.push(`${ch}\t${py}\t0`)
}
writeFileSync('/workspace/opt/dictionary_ext.txt', base.replace(/\n$/, '') + '\n' + additions.join('\n') + '\n')
console.log(`扩展词典完成: 新增 ${additions.length} 字（原有 ${known.size}）`)
