/* 打卡评价 · 点一下听读音
 *
 * 绿的（原文）→ 浏览器念标准音；红的（实读）→ 播她自己读的那一段。
 *
 * 为什么要有这个：**看字是分不出元音的**。seat / set、niece / nice、
 * hut / heart 写在纸上一目了然，差在哪儿只有耳朵知道 —— 而这一类恰恰是
 * 她错得最多的（8/31 那份 18 处错里 9 处是元音）。
 *
 * 录音**只有本地预览才有**（录音不进仓库，见 DATA.md 的「素材」那一档）。
 * 线上没有 <audio>，点红词就退回去念那个词 —— 听「这个错词读起来是什么样」，
 * 照样能和绿词对比出差在哪。所以这个脚本两边都能跑，不需要判断环境。
 */
(() => {
  'use strict';

  const synth = window.speechSynthesis;
  let voice = null;

  /* 音色挑选 —— 手法照搬老站语法栏目（../english/grammar/assets/app.js）。
     **不挑就会沙哑**：mac 上默认往往落到系统自带的 compact 音色，颗粒感很重；
     Enhanced / Premium（系统设置里下载过的高清版）和 Edge 的 Natural 系列
     才是清亮的。挑不到就不设 voice，交给浏览器按 lang 自己选 ——
     宁可音色一般，也别因为挑不到就不念。 */
  const GOOD = [
    /\((?:Premium|Enhanced)\)/i,                    // macOS 下载过的高清版，最优先
    /Natural/i,                                     // Edge 的 Online (Natural) 系列
    /\b(?:Ava|Samantha|Allison|Susan|Zoe|Evan)\b/i, // macOS / iOS 里好听的几个
    /Google US English/i,
    /\bAlex\b/i,
  ];

  /* mac 自带一堆**特效音色**（Boing / Bubbles / Jester / Zarvox…）和上世纪的
     MacinTalk 老音色（Albert / Fred / Ralph / Kathy），沙哑或者干脆是怪声。
     必须显式躲开：`getVoices()` 的英文第一名恰好就是 **Albert** ——
     不排除的话，「挑不到好的就用第一个」反而稳稳选中最难听的那个。 */
  const BAD = /\b(?:Albert|Bad News|Bahh|Bells|Boing|Bubbles|Cellos|Fred|Good News|Jester|Junior|Kathy|Organ|Ralph|Superstar|Trinoids|Whisper|Wobble|Zarvox)\b/i;

  // Chrome 第一次 getVoices() 常常是空的，要等 voiceschanged 再挑一次
  const loadVoice = () => {
    if (!synth) return;
    const all = synth.getVoices();
    if (!all.length) return;
    const en = all.filter((v) => /^en[-_]/i.test(v.lang || ''));
    const us = en.filter((v) => /^en[-_]US/i.test(v.lang || ''));
    const pool = (us.length ? us : en).filter((v) => !BAD.test(v.name || ''));
    voice = GOOD.reduce((hit, re) => hit || pool.find((v) => re.test(v.name || '')), null)
            || pool[0] || null;
  };
  loadVoice();
  if (synth) synth.addEventListener('voiceschanged', loadVoice);

  const clear = () => {
    document.querySelectorAll('.say.on').forEach((el) => el.classList.remove('on'));
  };

  const stopAll = () => {
    if (synth) synth.cancel();
    document.querySelectorAll('audio.rec').forEach((a) => a.pause());
    clear();
  };

  const say = (el, word) => {
    if (!synth || !word) return;
    const u = new SpeechSynthesisUtterance(word);
    u.lang = 'en-US';
    if (voice) u.voice = voice;
    /* rate / pitch 和老站语法栏目取同一档。**别再往下调**：原先 0.75
       听着沙哑 —— 慢速会把合成音拉出颗粒感，不是音色的锅。
       0.85 已经比正常语速慢，分辨元音够用了。 */
    u.rate = 0.85;
    u.pitch = 1.05;
    el.classList.add('on');
    u.onend = u.onerror = clear;
    // 兜底：个别浏览器 onend 不触发，状态会一直亮着（老站也留了这一手）
    setTimeout(clear, Math.max(1600, word.length * 140));
    synth.speak(u);
  };

  const play = (el, audio, from, to) => {
    const PAD = 0.35;           // 前后各留一点，别一上来就切进词中间
    audio.currentTime = Math.max(0, from - PAD);
    el.classList.add('on');
    audio.play().then(() => {
      /* 用 rAF 盯着停，**别用 timeupdate** —— 它每 ~250 毫秒才响一次，
         一个词也就半秒，够漏进下一个词了。 */
      const tick = () => {
        if (audio.paused) return clear();
        if (audio.currentTime >= to + PAD) {
          audio.pause();
          return clear();
        }
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }).catch(() => {
      // 软链断了 / 浏览器不让自动播 —— 退回去念这个词，别让点击没反应
      clear();
      say(el, el.dataset.say);
    });
  };

  document.addEventListener('click', (e) => {
    const el = e.target.closest('.say');
    if (!el) return;
    e.preventDefault();
    stopAll();

    const clip = el.dataset.clip;
    const audio = clip && el.closest('article') &&
                  el.closest('article').querySelector('audio.rec');
    if (audio) {
      const [from, to] = clip.split(',').map(Number);
      play(el, audio, from, to);
    } else {
      say(el, el.dataset.say);
    }
  });
})();
