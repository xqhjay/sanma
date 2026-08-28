// 生成优化版字根图: 官方grand.tsx分组串 + 新布局 → yima_opt.tsx
// 用法: npx tsx gen_diagram.ts F
import { readFileSync, writeFileSync } from 'fs'
import { loadSchemeData } from './core'

const tag = process.argv[2] ?? 'F'
const layout = JSON.parse(readFileSync(`/workspace/opt/layout_${tag}.json`, 'utf8'))
const sd = loadSchemeData('/workspace/奕码_1.2.yaml')

// ===== 提取官方grand.tsx的mapping =====
const src = readFileSync('/workspace/research/diagram/src/grand.tsx', 'utf8')
const start = src.indexOf('const mapping = {')
const objStart = src.indexOf('{', start)
let depth = 0, end = -1
for (let i = objStart; i < src.length; i++) {
  if (src[i] === '{') depth++
  else if (src[i] === '}') { depth--; if (depth === 0) { end = i; break } }
}
const officialMapping = eval('(' + src.slice(objStart, end + 1) + ')') as Record<string, string>
console.log('官方字根图分组串数:', Object.keys(officialMapping).length)

// ===== 新码位映射 =====
const newCodeByOld = new Map<string, string>()
for (const b of layout.base) newCodeByOld.set(b.code, b.newCode)
const promoEls = new Set<string>((layout.promos ?? []).map((p: any) => p.el))
const promoByEl = new Map<string, string>()
for (const p of layout.promos) promoByEl.set(p.el, p.code)

// ===== 适配官方分组串 =====
const newMapping: Record<string, string> = {}
const promoCodes = new Set<string>()
let dropped = 0, unknown = 0
for (const [charsStr, oldCode] of Object.entries(officialMapping)) {
  const newCode = newCodeByOld.get(oldCode)
  if (!newCode) { unknown++; continue }
  const kept = [...charsStr].filter((ch) => !promoEls.has(ch))
  if (kept.length === 0) { dropped++; continue }
  // 主根若被提升则重新选组内首元素（官方串首位是主根展示）
  newMapping[kept.join('')] = newCode
}
for (const [el, code] of promoByEl) {
  newMapping[el] = code
  promoCodes.add(code)
}
console.log(`适配后分组串: ${Object.keys(newMapping).length}（丢弃空串${dropped} 官方码位未识别${unknown}）`)

// ===== 覆盖校验: YAML非meta元素必须全被覆盖 =====
const covered = new Set<string>()
for (const charsStr of Object.keys(newMapping)) for (const ch of charsStr) covered.add(ch)
const missing: string[] = []
for (const [el, v] of Object.entries(sd.rawMapping)) {
  if (el.startsWith('首字母')) continue
  if (typeof v === 'string' && v.length === 1) continue
  if (!covered.has(el)) missing.push(el)
}
console.log('未覆盖YAML元素:', missing.length, missing.slice(0, 10).map((c) => 'U+' + c.codePointAt(0)!.toString(16)))

// 码位重复校验
const cnt = new Map<string, number>()
for (const c of Object.values(newMapping)) cnt.set(c, (cnt.get(c) ?? 0) + 1)
const dups = [...cnt.entries()].filter(([, c]) => c > 1)
console.log('图内同码位分组串数(正常,官方也拆分显示):', dups.length)

// ===== 生成tsx =====
const promoArr = [...promoCodes].map((c) => `"${c}"`).join(', ')
const tsx = `// 奕码·优化版 字根图（自动生成：基于官方grand.tsx布局 + SA优化码位）
const mapping = ${JSON.stringify(newMapping, null, 2)} as Record<string, string>;

// 新增独立根的码位（标注绿色）
const PROMO_CODES = new Set([${promoArr}]);

const ROWS = [
  ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
  ["a", "s", "d", "f", "g", "h", "j", "k", "l"],
  ["z", "x", "c", "v", "b", "n", "m"],
];

const CELL_WIDTH = 102;
const CELL_PADDING = 7;
const GAP_X = 8;
const GAP_Y = 8;
const MARGIN_X = 24;
const MARGIN_Y = 24;
const INFO_HEIGHT = 44;
const FONT_FAMILY = '"ChaiSans-Regular", "Noto Sans CJK SC", sans-serif';
const CHAR_SIZE = 12;
const ENTRY_HEIGHT = 18;
const LABEL_Y = 22;
const INITIAL_Y = LABEL_Y + 6;
const ANNOT_SIZE = 10;
const ANNOT_CHAR_WIDTH = 8;
const GROUP_GAP = 4;

const COLOR_PRIMARY = "#1e3a8a";
const COLOR_ACCENT = "#2563eb";
const COLOR_SECONDARY = "#3b82f6";
const COLOR_PROMO = "#059669";
const COLOR_TEXT = "#0f172a";
const COLOR_SURFACE = "#eff6ff";
const COLOR_BORDER = "#bfdbfe";
const COLOR_BG = "white";

interface Group {
  chars: string[];
  annotation: string;
  promo: boolean;
}

const groupsByKey = new Map<string, Group[]>();
for (const [charsStr, code] of Object.entries(mapping)) {
  const key = code[0];
  const annotation = code[1];
  const chars = [...charsStr].filter((ch) => ch.trim());
  const list = groupsByKey.get(key) ?? [];
  list.push({ chars, annotation, promo: PROMO_CODES.has(code) });
  groupsByKey.set(key, list);
}
for (const groups of groupsByKey.values()) {
  groups.sort((a, b) => a.annotation.localeCompare(b.annotation));
}

function groupWidth(group: Group): number {
  let w = 0;
  for (let i = 0; i < group.chars.length; i++) {
    w += i === 0 ? CHAR_SIZE : Math.round(CHAR_SIZE * 0.7);
  }
  return w + ANNOT_CHAR_WIDTH + GROUP_GAP;
}

function layoutGroups(groups: Group[], availWidth: number) {
  const placed: { group: Group; lineIdx: number; xOff: number }[] = [];
  let lineIdx = 0;
  let xOff = 0;
  for (const group of groups) {
    const gw = groupWidth(group);
    if (xOff > 0 && xOff + gw > availWidth) {
      lineIdx++;
      xOff = 0;
    }
    placed.push({ group, lineIdx, xOff });
    xOff += gw;
  }
  return placed;
}

const AVAIL_WIDTH = CELL_WIDTH - 2 * CELL_PADDING;
const MAX_LINES = Math.max(
  1,
  ...[...groupsByKey.values()].map((groups) => {
    const placed = layoutGroups(groups, AVAIL_WIDTH);
    return placed.length > 0 ? placed[placed.length - 1].lineIdx + 1 : 0;
  }),
);
const CELL_HEIGHT = INITIAL_Y + MAX_LINES * ENTRY_HEIGHT + 4;

const MAX_COLS = Math.max(...ROWS.map((r) => r.length));
const SVG_W = MARGIN_X * 2 + MAX_COLS * (CELL_WIDTH + GAP_X) - GAP_X;
const KEYS_TOP = MARGIN_Y + INFO_HEIGHT;
const SVG_H = KEYS_TOP + ROWS.length * (CELL_HEIGHT + GAP_Y) - GAP_Y + MARGIN_Y;

const ROW_OFFSETS = [0, 0.5, 1];
const LEGEND_FONT_SIZE = 12;
const LEGEND_LINE_HEIGHT = 17;
const LEGEND_PADDING = 10;
const LEGEND_RULES = [
  "单字根字：字根 + 音托 + 音托",
  "两字根字：首根 + 次根 + 音托",
  "多字根字：首根 + 次根 + 末根",
  "绿色小码 = 新增独立根",
];
const LAST_ROW_KEYS = ROWS[ROWS.length - 1].length;
const LEGEND_BOX_X =
  MARGIN_X + (ROW_OFFSETS[2] + LAST_ROW_KEYS) * (CELL_WIDTH + GAP_X);
const LEGEND_BOX_Y = KEYS_TOP + (ROWS.length - 1) * (CELL_HEIGHT + GAP_Y);
const LEGEND_BOX_WIDTH = 2 * CELL_WIDTH + GAP_X;
const LEGEND_BOX_HEIGHT = CELL_HEIGHT;

interface GrandKeyCellProps {
  keyLetter: string;
  x: number;
  y: number;
  groups?: Group[];
}

function GrandKeyCell({ keyLetter, x, y, groups = [] }: GrandKeyCellProps) {
  const placed = layoutGroups(groups, AVAIL_WIDTH);
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={CELL_WIDTH}
        height={CELL_HEIGHT}
        rx={4}
        fill={COLOR_SURFACE}
        stroke={COLOR_BORDER}
        strokeWidth={0.8}
      />
      <text
        x={x + CELL_PADDING}
        y={y + LABEL_Y}
        className="key-label"
        fill={COLOR_PRIMARY}
      >
        {keyLetter.toUpperCase()}
      </text>
      {placed.map(({ group, lineIdx, xOff: gxOff }) => {
        const lineY =
          y + INITIAL_Y + lineIdx * ENTRY_HEIGHT + ENTRY_HEIGHT * 0.8;
        const charPositions: { ch: string; cx: number; fs: number }[] = [];
        let cx = x + CELL_PADDING + gxOff;
        for (let i = 0; i < group.chars.length; i++) {
          const fs = i === 0 ? CHAR_SIZE : Math.round(CHAR_SIZE * 0.7);
          charPositions.push({ ch: group.chars[i], cx, fs });
          cx += fs;
        }
        const annotX = cx;
        return (
          <g key={group.chars[0] + group.annotation}>
            {charPositions.map(({ ch, cx: charCx, fs }) => (
              <text
                key={ch}
                x={charCx}
                y={lineY}
                fontSize={fs}
                fill={group.promo ? COLOR_PROMO : COLOR_TEXT}
              >
                {ch}
              </text>
            ))}
            <text
              x={annotX}
              y={lineY}
              fontSize={ANNOT_SIZE}
              fill={group.promo ? COLOR_PROMO : COLOR_ACCENT}
            >
              {group.annotation}
            </text>
          </g>
        );
      })}
    </g>
  );
}

interface DiagramProps {
  fontFaceCSS?: string;
}

export default function 奕码优化版({ fontFaceCSS }: DiagramProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="297mm"
      height="210mm"
      viewBox={\`0 0 \${SVG_W} \${SVG_H}\`}
      preserveAspectRatio="xMidYMid meet"
    >
      <title>字根图</title>
      <style>{\`\\
\${fontFaceCSS ?? ""}\\
text { font-family: \${FONT_FAMILY}; }\\
.key-label { font-size: 16px; font-weight: bold; }\\
.info-title { font-size: 32px; fill: \${COLOR_PRIMARY}; }\\
.info-meta { font-size: 14px; fill: \${COLOR_SECONDARY}; }\\
\`}</style>
      <rect x={0} y={0} width={SVG_W} height={SVG_H} fill={COLOR_BG} />
      <text
        x={MARGIN_X * 2}
        y={MARGIN_Y + INFO_HEIGHT * 0.4}
        className="info-meta"
      >
        大码乱序、小码音托的三码单字方案（优化版）
      </text>
      <text
        x={SVG_W / 2}
        y={MARGIN_Y + INFO_HEIGHT * 0.4}
        className="info-title"
        textAnchor="middle"
      >
        奕码·优化版
      </text>
      <text
        x={SVG_W - MARGIN_X * 2}
        y={MARGIN_Y + INFO_HEIGHT * 0.4}
        className="info-meta"
        textAnchor="end"
      >
        小泥巴(原作) · SA优化 · v2.0
      </text>
      {ROWS.map((row, ri) =>
        row.map((key, ci) => {
          const offset = (ROW_OFFSETS[ri] ?? 0) * (CELL_WIDTH + GAP_X);
          const x = MARGIN_X + ci * (CELL_WIDTH + GAP_X) + offset;
          const y = KEYS_TOP + ri * (CELL_HEIGHT + GAP_Y);
          return (
            <GrandKeyCell
              key={key}
              keyLetter={key}
              x={x}
              y={y}
              groups={groupsByKey.get(key)}
            />
          );
        }),
      )}
      <g>
        <rect
          x={LEGEND_BOX_X}
          y={LEGEND_BOX_Y}
          width={LEGEND_BOX_WIDTH}
          height={LEGEND_BOX_HEIGHT}
          fill={COLOR_SURFACE}
          stroke={COLOR_BORDER}
          strokeWidth={0.8}
          rx={4}
        />
        <text
          x={LEGEND_BOX_X + LEGEND_PADDING}
          y={LEGEND_BOX_Y + LEGEND_PADDING + LEGEND_LINE_HEIGHT * 0.8}
          fontSize={LEGEND_FONT_SIZE}
          fontWeight="bold"
          fill={COLOR_PRIMARY}
        >
          取码规则
        </text>
        {LEGEND_RULES.map((line, i) => (
          <text
            key={line}
            x={LEGEND_BOX_X + LEGEND_PADDING}
            y={LEGEND_BOX_Y + LEGEND_PADDING + LEGEND_LINE_HEIGHT * (i + 1.8)}
            fontSize={LEGEND_FONT_SIZE}
            fill={i === LEGEND_RULES.length - 1 ? COLOR_PROMO : COLOR_PRIMARY}
          >
            {line}
          </text>
        ))}
      </g>
    </svg>
  );
}
`
writeFileSync('/workspace/research/diagram/src/yima_opt.tsx', tsx)
console.log('已生成 /workspace/research/diagram/src/yima_opt.tsx')
