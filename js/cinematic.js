// Anime-Siegesanimation nach dem Domain Clash.
// Alles selbst gezeichnet (SVG + CSS) – keine fremden Bilder.
//
// Ablauf (Kamera-Schnitte über CSS-Klassen an .cine):
//   s1  Totale: beide Domains prallen aufeinander
//   s2  Reißschwenk auf den Sieger (er trägt den „Skin“ des Domain-Besitzers)
//   s3  Cut-in: Fingerzeichen + „領域展開 – DOMAIN EXPANSION“
//   s4  Titelkarte mit dem Namen der Domain
//   s5  Die Domain-Welt entfaltet sich, Kamerafahrt
//   s6  Finisher – je nach Domain eigene Animation
//   s7  Siegerpose

(function () {
  // ───────── Figuren ─────────
  const SKIN = '#f3d6c4';
  const CHARS = {
    gojo:     { name: 'Satoru Gojo', hair: 'spiky', hairC: '#f1f5f9', coat: '#111827', trim: '#1e3a8a', eyes: '#38bdf8', aura: '#60a5fa', sign: 'cross' },
    sukuna:   { name: 'Ryomen Sukuna', hair: 'short', hairC: '#f9a8d4', coat: '#f5f5f4', trim: '#7f1d1d', eyes: '#ef4444', aura: '#ef4444', accent: 'marks', sign: 'enma' },
    megumi:   { name: 'Megumi Fushiguro', hair: 'messy', hairC: '#0f172a', coat: '#0f172a', trim: '#334155', eyes: '#94a3b8', aura: '#475569', sign: 'dog' },
    mahito:   { name: 'Mahito', hair: 'long', hairC: '#93c5fd', coat: '#334155', trim: '#0f766e', eyes: '#5eead4', aura: '#2dd4bf', accent: 'stitches', sign: 'hands' },
    jogo:     { name: 'Jogo', hair: 'volcano', hairC: '#78350f', coat: '#fafaf9', trim: '#b45309', eyes: '#f97316', aura: '#f97316', sign: 'fist' },
    higuruma: { name: 'Hiromi Higuruma', hair: 'slick', hairC: '#1c1917', coat: '#1c1917', trim: '#ca8a04', eyes: '#facc15', aura: '#eab308', accent: 'badge', sign: 'point' },
    hakari:   { name: 'Kinji Hakari', hair: 'short', hairC: '#3f3f46', coat: '#1f2937', trim: '#db2777', eyes: '#f472b6', aura: '#ec4899', accent: 'fur', sign: 'fist' },
    yuta:     { name: 'Yuta Okkotsu', hair: 'messy', hairC: '#1e1b4b', coat: '#f8fafc', trim: '#be185d', eyes: '#f472b6', aura: '#f472b6', accent: 'ring', sign: 'cross' },
    dagon:    { name: 'Dagon', hair: 'octo', hairC: '#dc2626', coat: '#7f1d1d', trim: '#fca5a5', eyes: '#fde68a', aura: '#22d3ee', sign: 'hands' },
    naoya:    { name: 'Naoya Zenin', hair: 'short', hairC: '#facc15', coat: '#1e1b4b', trim: '#a5b4fc', eyes: '#c7d2fe', aura: '#a5b4fc', sign: 'point' },
  };
  // Domain → Besitzer (Skin) + Welt-Thema + Finisher + Kanji/Untertitel
  const DOMAINS = {
    'unendliche-leere':    { char: 'gojo', world: 'void', finish: 'void', kanji: '無量空処', line: 'Unendlich viel Information – du kannst dich nicht mehr bewegen.' },
    'boeser-schrein':      { char: 'sukuna', world: 'shrine', finish: 'shrine', kanji: '伏魔御廚子', line: 'Dismantle. Cleave. Alles im Umkreis wird zerschnitten.' },
    'chimaera-garten':     { char: 'megumi', world: 'shadow', finish: 'shadow', kanji: '嵌合暗翳庭', line: 'Die Schatten verschlucken alles.' },
    'selbstverkoerperung': { char: 'mahito', world: 'hands', finish: 'hands', kanji: '自閉円頓裹', line: 'Ich berühre deine Seele.' },
    'sarg-eisenberg':      { char: 'jogo', world: 'volcano', finish: 'volcano', kanji: '蓋棺鉄囲山', line: 'Verbrenne im Inneren des Vulkans.' },
    'todesurteil':         { char: 'higuruma', world: 'court', finish: 'court', kanji: '誅伏賜死', line: 'Das Urteil lautet: Todesstrafe.' },
    'idle-death-gamble':   { char: 'hakari', world: 'gamble', finish: 'gamble', kanji: '坐殺博徒', line: 'JACKPOT! Das Glück ist auf meiner Seite.' },
    'authentische-liebe':  { char: 'yuta', world: 'swords', finish: 'swords', kanji: '真贋相愛', line: 'Jedes Schwert trägt eine Technik.' },
    'skandha':             { char: 'dagon', world: 'beach', finish: 'beach', kanji: '蕩蘊平線', line: 'Der Ozean hat keinen Boden.' },
    'zeitzellen-palast':   { char: 'naoya', world: 'frames', finish: 'frames', kanji: '時胞月宮殿', line: 'Wer sich nicht an meine Regeln hält, zerbricht.' },
  };

  function hairSVG(c) {
    const C = c.hairC;
    switch (c.hair) {
      case 'spiky': return `<path d="M36 40 L28 12 L44 24 L44 2 L56 18 L62 -4 L68 18 L80 2 L78 24 L94 12 L84 40 Q60 26 36 40Z" fill="${C}"/>`;
      case 'short': return `<path d="M40 36 L36 18 L46 24 L50 12 L58 20 L64 10 L70 20 L76 14 L76 26 L84 22 L80 38 Q60 24 40 36Z" fill="${C}"/>`;
      case 'messy': return `<path d="M38 44 L32 22 L42 26 L40 10 L54 20 L60 6 L66 20 L80 10 L78 26 L90 22 L82 46 Q74 30 60 30 Q46 30 38 44Z" fill="${C}"/>`;
      case 'long': return `<path d="M38 50 Q34 20 60 16 Q86 20 82 50 L88 96 L76 70 L74 46 Q60 34 46 46 L44 70 L32 96Z" fill="${C}"/>`;
      case 'slick': return `<path d="M40 36 Q42 18 62 18 Q80 20 80 36 Q70 26 58 28 Q48 28 40 36Z" fill="${C}"/>`;
      case 'volcano': return `<path d="M38 60 L48 12 L72 12 L82 60Z" fill="#a8a29e"/><ellipse cx="60" cy="12" rx="12" ry="4" fill="#ea580c"/>
        <circle class="smoke" cx="56" cy="2" r="6" fill="#d6d3d1" opacity=".7"/><circle class="smoke s2" cx="66" cy="-6" r="5" fill="#d6d3d1" opacity=".6"/>`;
      case 'octo': return `<ellipse cx="60" cy="32" rx="26" ry="24" fill="${C}"/>
        ${[0, 1, 2, 3, 4].map((i) => `<path d="M${40 + i * 10} 50 q${i % 2 ? 6 : -6} 14 0 22" stroke="${C}" stroke-width="5" fill="none" stroke-linecap="round"/>`).join('')}`;
      default: return '';
    }
  }

  function figureSVG(key, opts) {
    opts = opts || {};
    const c = CHARS[key] || CHARS.gojo;
    const noFace = c.hair === 'volcano' || c.hair === 'octo';
    const eyeY = c.hair === 'volcano' ? 40 : 40;
    const face = noFace
      ? (c.hair === 'volcano' ? `<circle cx="60" cy="40" r="5" fill="${c.eyes}"/><circle cx="60" cy="40" r="2" fill="#000"/>`
        : `<circle cx="52" cy="34" r="3" fill="${c.eyes}"/><circle cx="68" cy="34" r="3" fill="${c.eyes}"/>`)
      : `<circle cx="60" cy="40" r="17" fill="${SKIN}"/>
         <path d="M51 ${eyeY} l6 0 M63 ${eyeY} l6 0" stroke="${c.eyes}" stroke-width="3" stroke-linecap="round" class="eyes"/>
         ${c.accent === 'marks' ? `<path d="M48 44 l6 1 M66 45 l6 -1 M50 30 l20 0" stroke="#111" stroke-width="1.6"/><circle cx="50" cy="34" r="1.6" fill="${c.eyes}"/><circle cx="70" cy="34" r="1.6" fill="${c.eyes}"/>` : ''}
         ${c.accent === 'stitches' ? `<path d="M46 32 L74 50" stroke="#334155" stroke-width="1.5"/>${[0, 1, 2, 3].map((i) => `<path d="M${50 + i * 6} ${33 + i * 4} l3 -4" stroke="#334155" stroke-width="1.2"/>`).join('')}` : ''}`;
    const accent = c.accent === 'badge' ? '<circle cx="48" cy="84" r="4" fill="#facc15"/>'
      : c.accent === 'fur' ? '<path d="M38 62 q8 -8 16 0 q6 -8 12 0 q8 -8 16 0 l0 8 l-44 0Z" fill="#e7e5e4"/>'
      : c.accent === 'ring' ? '<circle cx="28" cy="132" r="3" fill="none" stroke="#fde68a" stroke-width="2"/>' : '';
    return `<svg class="figure" viewBox="0 -10 120 250" xmlns="http://www.w3.org/2000/svg">
      <g class="legs"><path d="M46 140 L42 228 L54 228 L60 158 L66 228 L78 228 L74 140Z" fill="${c.coat}"/>
        <path d="M40 228 h16 v6 h-16z M64 228 h16 v6 h-16z" fill="#000"/></g>
      <g class="torso"><path d="M38 64 Q60 52 82 64 L86 142 L34 142Z" fill="${c.coat}"/>
        <path d="M60 60 L60 142" stroke="${c.trim}" stroke-width="3"/>
        <path d="M48 60 Q60 72 72 60 L72 54 L48 54Z" fill="${c.coat}" stroke="${c.trim}" stroke-width="2"/>${accent}</g>
      <g class="arm-l"><path d="M40 66 L28 128 L36 130 L48 74Z" fill="${c.coat}"/><circle cx="31" cy="132" r="6" fill="${SKIN}"/></g>
      <g class="arm-r"><path d="M80 66 L92 128 L84 130 L72 74Z" fill="${c.coat}"/><circle cx="89" cy="132" r="6" fill="${SKIN}"/></g>
      <g class="head">${face}${hairSVG(c)}</g>
    </svg>`;
  }

  // Fingerzeichen für das Cut-in
  function signSVG(kind, color) {
    const S = SKIN;
    const base = `<rect x="70" y="120" width="60" height="70" rx="22" fill="${S}"/>`;
    const fingers = {
      // Zeige- und Mittelfinger überkreuzt (Gojos Zeichen)
      cross: `<rect x="84" y="38" width="16" height="92" rx="8" fill="${S}" transform="rotate(14 92 128)"/>
              <rect x="102" y="34" width="16" height="96" rx="8" fill="${S}" transform="rotate(-16 110 128)" stroke="#d6b5a3" stroke-width="2.5"/>
              <rect x="122" y="100" width="12" height="30" rx="6" fill="${S}"/><rect x="66" y="104" width="12" height="28" rx="6" fill="${S}"/>`,
      enma: `<rect x="74" y="60" width="16" height="70" rx="8" fill="${S}"/><rect x="110" y="60" width="16" height="70" rx="8" fill="${S}"/>
             <rect x="90" y="84" width="20" height="44" rx="8" fill="${S}"/><path d="M80 60 L100 30 L120 60" stroke="${S}" stroke-width="12" fill="none" stroke-linecap="round"/>`,
      dog: `<rect x="76" y="56" width="16" height="74" rx="8" fill="${S}" transform="rotate(-12 84 120)"/><rect x="108" y="56" width="16" height="74" rx="8" fill="${S}" transform="rotate(12 116 120)"/>
            <rect x="92" y="96" width="18" height="34" rx="8" fill="${S}"/>`,
      hands: `<rect x="74" y="40" width="52" height="96" rx="24" fill="${S}"/><path d="M100 40 L100 136" stroke="#d6b5a3" stroke-width="3"/>`,
      fist: `<rect x="72" y="84" width="58" height="48" rx="16" fill="${S}"/><path d="M86 84 v20 M100 84 v20 M114 84 v20" stroke="#d6b5a3" stroke-width="3"/>`,
      point: `<rect x="92" y="30" width="16" height="100" rx="8" fill="${S}"/>`,
    };
    return `<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
      <circle cx="100" cy="100" r="96" fill="${color}" opacity=".25"/>
      ${Array.from({ length: 18 }, (_, i) => `<line x1="100" y1="100" x2="${100 + Math.cos(i / 18 * 6.283) * 140}" y2="${100 + Math.sin(i / 18 * 6.283) * 140}" stroke="${color}" stroke-width="2" opacity=".5"/>`).join('')}
      ${base}${fingers[kind] || fingers.point}
    </svg>`;
  }

  // ───────── Domain-Welten ─────────
  function rnd(a, b) { return a + Math.random() * (b - a); }
  function many(n, fn) { return Array.from({ length: n }, (_, i) => fn(i)).join(''); }

  function worldHTML(w) {
    switch (w) {
      case 'void': return `<div class="w w-void"><div class="galaxy"></div><div class="galaxy g2"></div>
        ${many(70, () => `<i class="star" style="left:${rnd(0, 100)}%;top:${rnd(0, 100)}%;animation-delay:-${rnd(0, 3).toFixed(2)}s"></i>`)}
        <div class="void-ring"></div></div>`;
      case 'shrine': return `<div class="w w-shrine"><div class="blood-moon"></div>
        <svg class="shrine" viewBox="0 0 400 260"><path d="M60 110 Q200 40 340 110 L326 120 Q200 62 74 120Z" fill="#1a0505"/>
          <rect x="90" y="120" width="220" height="14" fill="#1a0505"/><rect x="104" y="134" width="16" height="110" fill="#1a0505"/><rect x="280" y="134" width="16" height="110" fill="#1a0505"/>
          <rect x="150" y="150" width="100" height="94" fill="#1a0505"/>
          <path d="M170 170 q30 26 60 0 v10 q-30 26 -60 0Z" fill="#7f1d1d"/>${many(8, (i) => `<path d="M${176 + i * 6} 172 l3 8 l3 -8" fill="#fff"/>`)}
          ${many(6, (i) => `<g transform="translate(${30 + i * 64} 236)"><ellipse cx="0" cy="0" rx="16" ry="12" fill="#e7e5e4"/><path d="M-14 -6 q-10 -16 -2 -20 M14 -6 q10 -16 2 -20" stroke="#e7e5e4" stroke-width="4" fill="none"/><circle cx="-5" cy="0" r="3" fill="#000"/><circle cx="5" cy="0" r="3" fill="#000"/></g>`)}
        </svg><div class="red-mist"></div></div>`;
      case 'volcano': return `<div class="w w-volcano"><svg class="volc" viewBox="0 0 400 260"><path d="M40 260 L170 70 L230 70 L360 260Z" fill="#1c0a02"/>
          <path d="M170 70 Q200 90 230 70 L215 110 L200 92 L186 118Z" fill="#f97316"/></svg>
        ${many(40, () => `<i class="ember" style="left:${rnd(0, 100)}%;animation-delay:-${rnd(0, 3).toFixed(2)}s"></i>`)}<div class="lava"></div></div>`;
      case 'shadow': return `<div class="w w-shadow"><div class="shadow-sea"></div>
        ${many(16, () => `<i class="tendril" style="left:${rnd(0, 100)}%;animation-delay:-${rnd(0, 2.6).toFixed(2)}s"></i>`)}</div>`;
      case 'hands': return `<div class="w w-hands"><div class="hand-ring">${many(12, (i) => `<i class="bighand" style="transform:rotate(${i * 30}deg) translateY(-150px)"></i>`)}</div></div>`;
      case 'court': return `<div class="w w-court">${many(6, (i) => `<i class="pillar" style="left:${8 + i * 17}%"></i>`)}
        <svg class="scales" viewBox="0 0 100 100"><line x1="50" y1="10" x2="50" y2="90" stroke="#facc15" stroke-width="3"/><line x1="18" y1="24" x2="82" y2="24" stroke="#facc15" stroke-width="3"/>
          <path d="M18 24 L8 50 L28 50Z M82 24 L72 50 L92 50Z" fill="none" stroke="#facc15" stroke-width="2"/></svg></div>`;
      case 'gamble': return `<div class="w w-gamble">${many(30, () => `<i class="bulb" style="left:${rnd(0, 100)}%;top:${rnd(0, 100)}%;animation-delay:-${rnd(0, 1).toFixed(2)}s"></i>`)}
        <div class="neon">IDLE DEATH GAMBLE</div></div>`;
      case 'swords': return `<div class="w w-swords"><div class="pink-sky"></div>${many(40, () => `<i class="sword" style="left:${rnd(0, 100)}%;height:${rnd(30, 80)}px;transform:rotate(${rnd(-14, 14)}deg)"></i>`)}</div>`;
      case 'beach': return `<div class="w w-beach"><div class="sun"></div><div class="sea"></div>${many(12, () => `<i class="fish" style="left:${rnd(0, 100)}%;top:${rnd(55, 90)}%;animation-delay:-${rnd(0, 3).toFixed(2)}s"></i>`)}</div>`;
      case 'frames': return `<div class="w w-frames">${many(5, (i) => `<div class="strip" style="top:${10 + i * 18}%;animation-delay:-${i * 0.4}s">${many(10, () => '<i></i>')}</div>`)}</div>`;
      default: return '<div class="w w-void"></div>';
    }
  }

  // ───────── Finisher ─────────
  function finishHTML(f) {
    switch (f) {
      case 'void': return `<div class="fx fx-void">${many(26, (i) => `<span class="info" style="--a:${rnd(0, 360)}deg;animation-delay:${(i * 0.05).toFixed(2)}s">${['∞', '01', 'Ω', '∑', 'π', '∂'][i % 6]}</span>`)}
        <i class="void-point"></i></div><div class="fx-word">無量空処</div>`;
      case 'shrine': return `<div class="fx fx-shrine">${many(34, (i) => `<i class="cut" style="--r:${rnd(-80, 80)}deg;top:${rnd(10, 90)}%;animation-delay:${(i * 0.045).toFixed(2)}s"></i>`)}</div><div class="fx-word">解 · 捌</div>`;
      case 'volcano': return `<div class="fx fx-volcano">${many(7, (i) => `<i class="eruption" style="left:${20 + i * 10}%;animation-delay:${(i * 0.08).toFixed(2)}s"></i>`)}</div><div class="fx-word">極ノ番「隕」</div>`;
      case 'shadow': return `<div class="fx fx-shadow">${many(10, (i) => `<i class="grab" style="left:${10 + i * 8}%;animation-delay:${(i * 0.06).toFixed(2)}s"></i>`)}</div><div class="fx-word">影</div>`;
      case 'hands': return `<div class="fx fx-hands">${many(8, (i) => `<i class="touch" style="--r:${i * 45}deg;animation-delay:${(i * 0.06).toFixed(2)}s"></i>`)}</div><div class="fx-word">無為転変</div>`;
      case 'court': return `<div class="fx fx-court"><i class="gavel"></i><div class="verdict">死刑</div><i class="exec"></i></div><div class="fx-word">DEATH PENALTY</div>`;
      case 'gamble': return `<div class="fx fx-gamble"><div class="jp">7 7 7</div></div><div class="fx-word">JACKPOT!</div>`;
      case 'swords': return `<div class="fx fx-swords">${many(22, (i) => `<i class="rain" style="left:${rnd(5, 95)}%;animation-delay:${(i * 0.05).toFixed(2)}s"></i>`)}</div><div class="fx-word">リカ</div>`;
      case 'beach': return `<div class="fx fx-beach"><i class="wave"></i>${many(14, (i) => `<i class="swarm" style="top:${rnd(30, 80)}%;animation-delay:${(i * 0.05).toFixed(2)}s"></i>`)}</div><div class="fx-word">死累累湧軍</div>`;
      case 'frames': return `<div class="fx fx-frames"><i class="frame"></i>${many(10, (i) => `<i class="shard" style="--x:${rnd(-120, 120)}px;--y:${rnd(-120, 120)}px;--r:${rnd(-180, 180)}deg"></i>`)}</div><div class="fx-word">24 FPS</div>`;
      default: return '<div class="fx"></div>';
    }
  }

  // ───────── Abspielen ─────────
  const SHOTS = [['s1', 0], ['s2', 1900], ['s3', 2900], ['s4', 4200], ['s5', 5400], ['s6', 7000], ['s7', 10200], ['end', 12600]];

  function play(container, o, onDone) {
    const D = DOMAINS[o.winnerDomain] || DOMAINS['unendliche-leere'];
    const L = DOMAINS[o.loserDomain] || DOMAINS['boeser-schrein'];
    const W = CHARS[D.char], LC = CHARS[L.char];
    container.innerHTML = `<div class="cine s0 fin-${D.finish}" style="--wa:${W.aura};--la:${LC.aura}">
      <div class="cam"><div class="world">
        <div class="env env-clash"><div class="half hl"></div><div class="half hr"></div><div class="clash-core"></div></div>
        <div class="env env-domain">${worldHTML(D.world)}</div>
        <div class="fig fig-w"><div class="aura"></div>${figureSVG(D.char)}<div class="tag">${o.winnerName}</div></div>
        <div class="fig fig-l"><div class="aura"></div>${figureSVG(L.char)}<div class="tag">${o.loserName}</div>${finishHTML(D.finish)}</div>
        <div class="speedlines"></div>
      </div></div>
      <div class="cutin"><div class="cutin-eye"><div class="eye-shape" style="--e:${W.eyes}"></div></div><div class="cutin-hand">${signSVG(W.sign, W.aura)}</div></div>
      <div class="ryoiki"><b>領域展開</b><span>DOMAIN EXPANSION</span></div>
      <div class="dtitle"><b>${D.kanji}</b><span>${o.domainName}</span><small>${D.line}</small></div>
      <div class="victory"><b>${o.meWon ? 'SIEG!' : 'NIEDERLAGE'}</b><span>${o.winnerName} gewinnt den Domain Clash</span></div>
      <div class="bars"><i></i><i></i></div>
      <div class="flashwhite"></div>
      <button class="cine-skip" type="button">Überspringen ⏭</button>
    </div>`;
    const cine = container.querySelector('.cine');
    const timers = [];
    let finished = false;
    const finish = () => { if (finished) return; finished = true; timers.forEach(clearTimeout); onDone && onDone(); };
    SHOTS.forEach(([cls, t]) => timers.push(setTimeout(() => {
      if (cls === 'end') return finish();
      cine.className = cine.className.replace(/\bs\d\b/g, '').trim() + ' ' + cls;
      cine.classList.remove('cut'); void cine.offsetWidth; cine.classList.add('cut');
    }, t + 60)));
    cine.querySelector('.cine-skip').onclick = finish;
    return { stop: finish };
  }

  window.Cinematic = { play, DOMAINS, CHARS, figureSVG };
})();
