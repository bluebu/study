// 页面截图 —— 改完排版自检用的那一把尺子。
//
// 为什么非要有这个文件：Chrome headless 的 `--window-size` **模拟不了手机视口**。
// 它的布局视口恒为 500px，`--window-size` 只是把 500px 的渲染结果裁成那个尺寸；
// `--dump-dom` 量出来的 innerWidth 也永远是 500，`--headless=new` 一样。
// 而 review 那几个页面都有 media query，量它们必须用真实视口 —— 所以走 playwright。
//
// 用法：
//   node tools/shot.mjs <url> <out.png> [宽=390]              整页
//   node tools/shot.mjs <url> <out.png> [宽] --el "<选择器>"    只截一个元素
//   node tools/shot.mjs <url> <out.png> [宽] --clip <y> <高>    按 CSS 坐标截一段
//   node tools/shot.mjs <url> --probe   [宽]                   不截图，只报尺寸和溢出
//
// 跑完一定会打两行 `innerWidth` / `scrollWidth`：
//   · innerWidth 拿不到你要的宽度 = 视口没模拟上，量出来的全是白量
//   · scrollWidth > innerWidth = 横向溢出（打印单在手机上最容易犯，见 CLAUDE.md）
//
// ⚠️ **别把它接进 `| head -N`**：head 读够行数就关管道，node 会在写 PNG 的半路上
//    被掐死，落一个截断的坏图 —— 而它看着像是页面出了问题。要过滤就 `> log 2>&1`
//    之后再看，或者用 --probe（那个只输出几行，随便管）。
//
// 依赖：`npm i playwright-core`（浏览器本体用系统里已有的 Chromium 缓存，不另下）。

import { chromium } from 'playwright-core';

const argv = process.argv.slice(2);
const flag = (name) => {
  const i = argv.indexOf(name);
  return i === -1 ? null : argv.slice(i + 1);
};

const probe = argv.includes('--probe');
const positional = argv.filter((a, i) =>
  !a.startsWith('--') && !(i > 0 && argv[i - 1].startsWith('--')));
const [url, out] = probe ? [positional[0], null] : positional;
const width = Number(positional[probe ? 1 : 2]) || 390;
const el = flag('--el')?.[0] ?? null;
const clip = flag('--clip');

if (!url || (!probe && !out)) {
  console.error('用法：node tools/shot.mjs <url> <out.png> [宽=390] [--el 选择器 | --clip y 高]');
  console.error('     node tools/shot.mjs <url> --probe [宽=390]');
  process.exit(2);
}

const browser = await chromium.launch({ channel: 'chromium' });
// isMobile 要开：不开的话 media query 和 dpr 都跟桌面走，量出来的仍旧不是手机上的样子
const page = await browser.newPage({
  viewport: { width, height: 900 },
  isMobile: true,
  deviceScaleFactor: 2,
});
await page.goto(url, { waitUntil: 'networkidle' });

const size = await page.evaluate(() => ({
  inner: innerWidth,
  scroll: document.documentElement.scrollWidth,
  height: document.documentElement.scrollHeight,
}));
console.log(`innerWidth  = ${size.inner}${size.inner === width ? '' : '   ⚠️ 和要的宽度对不上，视口没模拟上'}`);
console.log(`scrollWidth = ${size.scroll}${size.scroll > size.inner ? `   ⚠️ 横向溢出 ${size.scroll - size.inner}px` : ''}`);
console.log(`scrollHeight= ${size.height}`);

if (!probe) {
  if (el) {
    const node = await page.$(el);
    if (!node) {
      console.error(`找不到元素：${el}`);
      await browser.close();
      process.exit(1);
    }
    await node.screenshot({ path: out });
  } else if (clip) {
    const [y, h] = clip.map(Number);
    await page.screenshot({ path: out, fullPage: true, clip: { x: 0, y, width, height: h } });
  } else {
    await page.screenshot({ path: out, fullPage: true });
  }
  console.log(`→ ${out}`);
}

await browser.close();
