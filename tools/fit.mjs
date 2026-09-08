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
// 换页点已经定死的单子（教材总览是「一单元一页」）用它做另一件事：**逐页报溢出**。
// 每页的内容一旦高过纸，页脚会被挤到下一页，PDF 里多出一张只印页码的白纸 ——
// 这在 HTML 源码里看不出来，得量。
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
// 视口给足横版 A4（1123×794）：竖版的单子照样量得准，.sheet 的宽高是 mm 钉死的
const p = await b.newPage({ viewport: { width: 1123, height: 794 } });
await p.emulateMedia({ media: 'print' });
await p.goto('file://' + process.argv[2], { waitUntil: 'networkidle' });
// 逐页量：内容 vs 可用高。溢出的那页会把页脚挤到下一张纸上
const sheets = await p.evaluate(() => [...document.querySelectorAll('.sheet')].map(s => {
  const cs = getComputedStyle(s);
  const avail = s.getBoundingClientRect().height
    - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
  const used = [...s.children].reduce((a, c) => a + c.getBoundingClientRect().height, 0);
  return { rows: s.querySelectorAll('tbody tr').length, avail, used };
}));

const r = await p.evaluate(() => {
  // 关掉撑满，量各行的自然高度
  document.querySelectorAll('.scroll').forEach(s => s.style.flex = '0 0 auto');
  document.querySelectorAll('table').forEach(t => t.style.height = 'auto');
  const h = el => el ? +el.getBoundingClientRect().height.toFixed(1) : 0;
  const sheet = document.querySelector('.sheet');
  const cs = getComputedStyle(sheet);
  const pad = parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom);
  return {
    // 纸高从 .sheet 自己读 —— 竖版 297mm / 横版 210mm，别写死
    sheetH: +sheet.getBoundingClientRect().height.toFixed(1), pad: +pad.toFixed(1),
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

if (sheets.length > 1) {
  console.log(`\n=== 这份单子现在是 ${sheets.length} 页，逐页看装得下装不下 ===`);
  let bad = 0;
  sheets.forEach((x, k) => {
    const over = x.used - x.avail;
    if (over > 0) bad++;
    console.log(`  第 ${k + 1} 页  ${x.rows} 行  内容 ${x.used.toFixed(0)} / 可用 ` +
      `${x.avail.toFixed(0)}  ` + (over > 0
        ? `⚠️ 超出 ${over.toFixed(0)}px —— 页脚会被挤到下一张纸上`
        : `剩 ${(-over).toFixed(0)}`));
  });
  console.log(bad ? `  ⚠️ ${bad} 页装不下：收内容或者收这一页的附属块（摘要 / 小结）的间距`
                  : '  八页都装得下。余量 <30px 的页要留神：线上字体折行会差一两行');
}

const avail = r.sheetH - r.pad;
console.log(`纸高 ${r.sheetH}（${(r.sheetH / 96 * 25.4).toFixed(0)}mm）可用高 ${avail.toFixed(1)}  页头 ${r.head}  摘要 ${r.sum}  note ${r.note}  表头 ${r.thead}  小结 ${r.tail}  页脚 ${r.foot}`);
const total = r.rows.reduce((a, x) => a + x.h, 0);
console.log(`35 行 + 3 分组行 自然总高 ${total.toFixed(1)}  =  ${(total / avail).toFixed(2)} 页的量`);

// 装页：页 1 有摘要 + note，末页要钉小结。
// **目标按「剩余内容 / 剩余容量」动态算**，不是固定比例：固定比例会在最后一页
// 装不完（余量分早了），贪心又反过来把零头全留给末页 —— 实测末页 3 行被拉 153%，
// 那就是「空半页」的来路。
function caps(nPages) {
  return Array.from({ length: nPages }, (_, k) => {
    let cap = avail - r.head - r.foot - r.thead;
    if (k === 0) cap -= r.sum + r.note;
    if (k === nPages - 1) cap -= r.tail;
    return cap;
  });
}

function pack(nPages, balanced = false) {
  const cap = caps(nPages);
  const pages = []; let i = 0;
  for (let pg = 0; pg < nPages; pg++) {
    const rest = r.rows.slice(i).reduce((a, x) => a + x.h, 0);
    const restCap = cap.slice(pg).reduce((a, x) => a + x, 0);
    const target = balanced && pg < nPages - 1 ? rest * (cap[pg] / restCap) : cap[pg];
    let used = 0; const take = [];
    while (i < r.rows.length) {
      // 分组行不许落在页底当孤儿：它后面至少还得跟一行
      const need = r.rows[i].group ? r.rows[i].h + (r.rows[i + 1]?.h || 0) : r.rows[i].h;
      if (used + need > cap[pg] && take.length) break;
      // 够到目标就收手，把余量留给后面的页（越过目标反而更接近就多收这一行）
      if (take.length && used >= target) break;
      if (take.length && used + need > target &&
          (used + need - target) > (target - used)) break;
      used += r.rows[i].h; take.push(r.rows[i].label); i++;
    }
    pages.push({ pg: pg + 1, cap: +cap[pg].toFixed(0), used: +used.toFixed(0),
                 slack: +(cap[pg] - used).toFixed(0),
                 stretch: used ? `${((cap[pg] / used - 1) * 100).toFixed(0)}%` : '—',
                 n: take.length, last: take[take.length - 1] });
  }
  return { pages, left: r.rows.length - i };
}

// 装到装完为止，报最少页数和每页的断点
for (let n = 1; n <= 20; n++) {
  if (pack(n).left) continue;                      // 贪心装不完就加一页
  let { pages, left } = pack(n, true);             // 装得下再按剩余容量均摊
  if (left) ({ pages, left } = pack(n));           // 均摊万一装不完，退回贪心
  if (left) continue;
  console.log(`\n=== ${n} 页装完（按剩余容量均摊，拉伸尽量一致）===`);
  for (const x of pages) console.log(`  第 ${x.pg} 页  容量 ${x.cap}  ${x.n} 行占 ${x.used}  剩 ${x.slack}  行高拉 ${x.stretch}  末行 ${x.last}`);
  console.log('\nspec 里的 [分页] 放在这几行之后：' +
    pages.slice(0, -1).map(x => x.last).join('、'));
  break;
}
