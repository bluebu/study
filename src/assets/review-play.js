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

  /* Chrome 第一次 getVoices() 常常是空的，要等 voiceschanged 再挑一次。
     挑不到就不设 voice，交给浏览器按 lang 自己选 —— 别因为挑不到就不念。 */
  const loadVoice = () => {
    if (!synth) return;
    const en = synth.getVoices().filter((v) => /^en[-_]/i.test(v.lang));
    voice = en.find((v) => /^en[-_]US/i.test(v.lang)) || en[0] || null;
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
    u.rate = 0.75;              // 慢一点 —— 这是拿来分辨元音的，不是听语流
    el.classList.add('on');
    u.onend = u.onerror = clear;
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
