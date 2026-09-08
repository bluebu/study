// 打印单的换页点该挑在哪儿 —— A4 分页 + 每页排满，靠这把尺子量。
//
// 为什么非要有这个文件：一页装几行是**行高**定的，不是行数定的。教材总览的
// 「其他要求」列照抄课后题原话，折 2 行还是 7 行随内容变，机器猜不出来 ——
// 所以换页点是人写在 spec 里的（`[分页]`），而这个脚本负责告诉人「写在哪一行后面」。
//
// 它在 print 媒介下量出页头 / 摘要 / 表头 / 小结 / 页脚的开销和每一行的自然高度，
// 然后报：最少几页装得完、每页断在哪一行、各页的行高要拉多少。
// **按容量均摊**，不是贪心装满前几页 —— 贪心会把零头全留给末页
// （实测末页 3 行被拉 153%，看着就是空半页）。
//
// 用法：
//   node tools/fit.mjs dist/chinese/overview/g4a.html      （或 make fit URL=…）
//
// 报出来的「[分页] 放在这几行之后」直接抄进 spec，再 make pdf 逐页 Read 复核。
// 改了字号、行距、列宽、摘要条数，都要重新量一遍。
//
// 依赖：`npm i playwright-core`（和 tools/shot.mjs 共用）。

import { chromium } from 'playwright-core';
const b = await chromium.launch({ channel: 'chromium' });
const p = await b.newPage({ viewport: { width: 794, height: 1123 } });
await p.emulateMedia({ media: 'print' });
await p.goto('file://' + process.argv[2], { waitUntil: 'networkidle' });
const r = await p.evaluate(() => {
  // 关掉撑满，量各行的自然高度
  document.querySelectorAll('.scroll').forEach(s => s.style.flex = '0 0 auto');
  document.querySelectorAll('table').forEach(t => t.style.height = 'auto');
  const h = el => el ? +el.getBoundingClientRect().height.toFixed(1) : 0;
  const sheet = document.querySelector('.sheet');
  const cs = getComputedStyle(sheet);
  const pad = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
  return {
    sheetH: 1122.52, pad: +pad.toFixed(1),
    head: h(document.querySelector('.head')),
    sum: h(document.querySelector('.sum')),
    note: h(document.querySelector('.note')),
    thead: h(document.querySelector('thead')),
    tail: h(document.querySelector('.tail')),
    foot: h(document.querySelector('.foot')),
    rows: [...document.querySelectorAll('tbody tr')].map(tr => ({
      label: (tr.querySelector('td.no')?.textContent || 'G:' + tr.textContent.trim()).trim(),
      h: h(tr), group: tr.classList.contains('group'),
    })),
  };
});
await b.close();

const avail = r.sheetH - r.pad;
console.log(`A4 可用高 ${avail.toFixed(1)}  页头 ${r.head}  摘要 ${r.sum}  note ${r.note}  表头 ${r.thead}  小结 ${r.tail}  页脚 ${r.foot}`);
const total = r.rows.reduce((a, x) => a + x.h, 0);
console.log(`35 行 + 3 分组行 自然总高 ${total.toFixed(1)}  =  ${(total / avail).toFixed(2)} 页的量`);

// 装页：页 1 有摘要 + note，末页要钉小结。
// ratio<1 时按「容量 × ratio」均摊 —— 页数一定的情况下，各页拉伸一致才好看，
// 贪心装满前几页会把零头全留给末页（实测末页 3 行被拉 101%）
function pack(nPages, ratio = 1) {
  const pages = []; let i = 0;
  for (let pg = 1; pg <= nPages; pg++) {
    const last = pg === nPages;
    let cap = avail - r.head - r.foot - r.thead;
    if (pg === 1) cap -= r.sum + r.note;
    if (last) cap -= r.tail;
    const left = nPages - pg + 1;                 // 含本页，还剩几页
    const target = left === 1 ? cap : cap * ratio;
    let used = 0; const take = [];
    while (i < r.rows.length) {
      // 分组行不许落在页底当孤儿：它后面至少还得跟一行
      const need = r.rows[i].group ? r.rows[i].h + (r.rows[i + 1]?.h || 0) : r.rows[i].h;
      if (used + need > cap && take.length) break;
      // 够到目标就收手，把余量留给后面的页（越过目标反而更近就多收这一行）
      if (used >= target && take.length) break;
      if (used + need > target && take.length && (used + need - target) > (target - used)) break;
      used += r.rows[i].h; take.push(r.rows[i].label); i++;
    }
    pages.push({ pg, cap: +cap.toFixed(0), used: +used.toFixed(0),
                 slack: +(cap - used).toFixed(0), stretch: `${((cap / used - 1) * 100).toFixed(0)}%`,
                 n: take.length, last: take[take.length - 1] });
  }
  return { pages, left: r.rows.length - i };
}
// 装到装完为止，报最少页数和每页的断点
for (let n = 1; n <= 20; n++) {
  if (pack(n).left) continue;                      // 先用贪心判断这个页数够不够
  const capTotal = pack(n).pages.reduce((a, x) => a + x.cap, 0);
  const { pages, left } = pack(n, Math.min(1, total / capTotal));
  if (left) continue;
  console.log(`\n=== ${n} 页装完（各页按容量均摊，拉伸尽量一致）===`);
  for (const x of pages) console.log(`  第 ${x.pg} 页  容量 ${x.cap}  ${x.n} 行占 ${x.used}  剩 ${x.slack}  行高拉 ${x.stretch}  末行 ${x.last}`);
  console.log('\nspec 里的 [分页] 放在这几行之后：' +
    pages.slice(0, -1).map(x => x.last).join('、'));
  break;
}
