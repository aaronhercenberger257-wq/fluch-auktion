// Eigene Bilder für die Fähigkeiten: Farbverlauf + Symbol + Kanji-Stempel.
// Alles als SVG gezeichnet – keine fremden Bilder, keine Urheberrechtsprobleme.

(function () {
  // Symbole im 100×100-Raster. "C" wird durch die Akzentfarbe ersetzt.
  const G = {
    void: `<circle cx="50" cy="50" r="30" fill="none" stroke="C" stroke-width="2" opacity=".5"/>
           <circle cx="50" cy="50" r="20" fill="none" stroke="C" stroke-width="3" opacity=".8"/>
           <circle cx="50" cy="50" r="10" fill="#000"/><circle cx="50" cy="50" r="10" fill="none" stroke="#fff" stroke-width="1.5"/>
           <g stroke="C" stroke-width="1.2" opacity=".7">${Array.from({ length: 12 }, (_, i) => {
             const a = (i / 12) * Math.PI * 2; return `<line x1="${50 + Math.cos(a) * 34}" y1="${50 + Math.sin(a) * 34}" x2="${50 + Math.cos(a) * 46}" y2="${50 + Math.sin(a) * 46}"/>`; }).join('')}</g>`,
    shrine: `<path d="M18 40 Q50 26 82 40 L78 44 Q50 33 22 44Z" fill="C"/><rect x="26" y="44" width="48" height="5" fill="C"/>
             <rect x="30" y="49" width="5" height="34" fill="C"/><rect x="65" y="49" width="5" height="34" fill="C"/>
             <rect x="45" y="55" width="10" height="28" fill="C" opacity=".7"/><path d="M35 30 Q50 18 65 30" stroke="C" stroke-width="3" fill="none"/>
             <path d="M20 88 L80 88" stroke="C" stroke-width="3"/>`,
    shadow: `<ellipse cx="50" cy="72" rx="36" ry="10" fill="#000" opacity=".7"/>
             <path d="M22 72 Q30 40 40 60 Q46 30 54 58 Q62 34 70 62 Q76 48 80 72Z" fill="C" opacity=".85"/>
             <circle cx="44" cy="52" r="2.5" fill="#fff"/><circle cx="60" cy="54" r="2.5" fill="#fff"/>`,
    hands: `${[0, 72, 144, 216, 288].map((r) => `<g transform="rotate(${r} 50 50)"><path d="M46 18 Q50 10 54 18 L55 36 L45 36Z" fill="C"/><rect x="47" y="12" width="2" height="8" rx="1" fill="C"/><rect x="51" y="11" width="2" height="9" rx="1" fill="C"/></g>`).join('')}
            <circle cx="50" cy="50" r="12" fill="none" stroke="C" stroke-width="3"/><path d="M42 50 L58 50 M50 42 L50 58" stroke="C" stroke-width="1.5" stroke-dasharray="2 2"/>`,
    volcano: `<path d="M12 86 L38 38 L62 38 L88 86Z" fill="#1c0a02" stroke="C" stroke-width="2"/>
              <path d="M38 38 Q50 46 62 38 L56 52 L50 46 L44 56Z" fill="C"/>
              <circle cx="50" cy="22" r="8" fill="C" opacity=".8"/><circle cx="38" cy="16" r="5" fill="C" opacity=".6"/><circle cx="62" cy="14" r="4" fill="C" opacity=".6"/>`,
    scale: `<line x1="50" y1="18" x2="50" y2="82" stroke="C" stroke-width="3"/><line x1="22" y1="30" x2="78" y2="30" stroke="C" stroke-width="3"/>
            <path d="M22 30 L12 54 L32 54Z" fill="none" stroke="C" stroke-width="2"/><path d="M78 30 L68 54 L88 54Z" fill="none" stroke="C" stroke-width="2"/>
            <path d="M10 54 Q22 64 34 54Z M66 54 Q78 64 90 54Z" fill="C"/><rect x="36" y="80" width="28" height="5" fill="C"/>`,
    dice: `<rect x="20" y="30" width="36" height="36" rx="6" fill="C" transform="rotate(-12 38 48)"/>
           <rect x="48" y="38" width="32" height="32" rx="6" fill="#fff" opacity=".9" transform="rotate(14 64 54)"/>
           <g fill="#111"><circle cx="30" cy="42" r="3"/><circle cx="44" cy="56" r="3"/><circle cx="37" cy="49" r="3"/>
           <circle cx="58" cy="48" r="2.6"/><circle cx="70" cy="60" r="2.6"/></g>
           <text x="50" y="22" text-anchor="middle" font-size="12" font-weight="900" fill="C" font-family="sans-serif">777</text>`,
    infinity: `<path d="M50 50 C40 32 18 32 18 50 C18 68 40 68 50 50 C60 32 82 32 82 50 C82 68 60 68 50 50Z" fill="none" stroke="C" stroke-width="6"/>
               <circle cx="50" cy="50" r="40" fill="none" stroke="C" stroke-width="1" opacity=".4" stroke-dasharray="3 4"/>`,
    orb: `<circle cx="34" cy="50" r="13" fill="#3b82f6" opacity=".8"/><circle cx="66" cy="50" r="13" fill="#ef4444" opacity=".8"/>
          <circle cx="50" cy="50" r="18" fill="C" opacity=".9"/><circle cx="50" cy="50" r="9" fill="#fff" opacity=".85"/>
          <circle cx="50" cy="50" r="30" fill="none" stroke="C" stroke-width="1.5" opacity=".5"/>`,
    eye: `<path d="M12 50 Q50 18 88 50 Q50 82 12 50Z" fill="#fff" opacity=".95"/>
          <circle cx="50" cy="50" r="16" fill="C"/><circle cx="50" cy="50" r="7" fill="#021526"/>
          <circle cx="45" cy="45" r="3" fill="#fff"/><path d="M12 50 Q50 18 88 50" fill="none" stroke="C" stroke-width="2"/>`,
    slash: `<path d="M16 80 L80 14" stroke="C" stroke-width="5" stroke-linecap="round"/><path d="M26 86 L86 30" stroke="C" stroke-width="2.5" stroke-linecap="round" opacity=".7"/>
            <path d="M14 26 L62 86" stroke="#fff" stroke-width="3" stroke-linecap="round" opacity=".8"/><path d="M30 14 L88 70" stroke="C" stroke-width="1.5" opacity=".5"/>`,
    arrow: `<path d="M22 20 Q8 50 22 80" fill="none" stroke="C" stroke-width="4"/><line x1="22" y1="20" x2="22" y2="80" stroke="C" stroke-width="1"/>
            <line x1="22" y1="50" x2="84" y2="50" stroke="#fff" stroke-width="3"/><path d="M84 50 L72 42 L76 50 L72 58Z" fill="#fff"/>
            <path d="M30 50 Q50 30 70 50 Q50 70 30 50Z" fill="C" opacity=".75"/><path d="M40 50 Q55 38 74 50 Q55 62 40 50Z" fill="#fde68a" opacity=".8"/>`,
    dog: `<path d="M24 74 L30 44 L22 24 L38 36 L50 32 L62 36 L78 24 L70 44 L76 74 Q50 86 24 74Z" fill="C"/>
          <path d="M36 52 L44 56 M64 52 L56 56" stroke="#fff" stroke-width="3" stroke-linecap="round"/><path d="M46 66 L50 70 L54 66" fill="none" stroke="#000" stroke-width="2"/>`,
    wheel: `<circle cx="50" cy="50" r="12" fill="none" stroke="C" stroke-width="4"/>
            ${Array.from({ length: 8 }, (_, i) => `<g transform="rotate(${i * 45} 50 50)"><line x1="50" y1="38" x2="50" y2="18" stroke="C" stroke-width="3"/><circle cx="50" cy="16" r="4" fill="C"/></g>`).join('')}
            <circle cx="50" cy="50" r="34" fill="none" stroke="C" stroke-width="1.5" opacity=".5"/>`,
    stitch: `<circle cx="50" cy="50" r="28" fill="C" opacity=".35"/><path d="M26 34 Q50 56 74 70" fill="none" stroke="C" stroke-width="3"/>
             ${[0, 1, 2, 3, 4, 5].map((i) => { const x = 30 + i * 8, y = 37 + i * 6; return `<line x1="${x - 4}" y1="${y + 5}" x2="${x + 4}" y2="${y - 5}" stroke="#fff" stroke-width="2"/>`; }).join('')}
             <circle cx="40" cy="44" r="3" fill="#fff"/><circle cx="62" cy="42" r="3" fill="#fff"/>`,
    swirl: `<path d="M50 50 m0 0 a4 4 0 0 1 8 0 a8 8 0 0 1 -16 0 a12 12 0 0 1 24 0 a16 16 0 0 1 -32 0 a20 20 0 0 1 40 0 a24 24 0 0 1 -48 0" fill="none" stroke="C" stroke-width="3.5"/>
            <circle cx="50" cy="50" r="5" fill="#000"/>`,
    nail: `<rect x="44" y="18" width="12" height="40" fill="C" transform="rotate(25 50 50)"/><path d="M44 58 L56 58 L50 72Z" fill="C" transform="rotate(25 50 50)"/>
           <rect x="36" y="12" width="28" height="7" rx="2" fill="#fff" transform="rotate(25 50 50)"/>
           <circle cx="34" cy="74" r="10" fill="none" stroke="C" stroke-width="2" opacity=".7"/><circle cx="34" cy="74" r="16" fill="none" stroke="C" stroke-width="1" opacity=".4"/>`,
    ratio: `<rect x="22" y="16" width="56" height="68" fill="none" stroke="C" stroke-width="2.5"/>
            <line x1="22" y1="63.6" x2="78" y2="63.6" stroke="#ef4444" stroke-width="3"/>
            <text x="50" y="44" text-anchor="middle" font-size="18" font-weight="900" fill="C" font-family="sans-serif">7:3</text>
            <circle cx="50" cy="63.6" r="6" fill="none" stroke="#fff" stroke-width="2"/>`,
    drop: `<path d="M50 14 Q74 50 74 62 A24 24 0 0 1 26 62 Q26 50 50 14Z" fill="C"/>
           <path d="M40 58 Q42 48 48 42" stroke="#fff" stroke-width="3" fill="none" opacity=".7" stroke-linecap="round"/>
           <line x1="12" y1="88" x2="88" y2="88" stroke="C" stroke-width="2"/>`,
    mouth: `<path d="M20 50 Q50 30 80 50 Q50 70 20 50Z" fill="#000" stroke="C" stroke-width="3"/>
            <path d="M24 50 Q50 40 76 50" stroke="C" stroke-width="2" fill="none"/>
            <circle cx="30" cy="62" r="2" fill="C"/><circle cx="70" cy="62" r="2" fill="C"/>
            <path d="M84 34 L94 28 M86 50 L96 50 M84 66 L94 72 M16 34 L6 28 M14 50 L4 50 M16 66 L6 72" stroke="C" stroke-width="2.5"/>`,
    clap: `<path d="M30 76 L30 40 Q30 32 36 32 L44 32 L46 24 Q50 18 54 24 L56 32 L64 32 Q70 32 70 40 L70 76Z" fill="C" opacity=".9"/>
           <line x1="50" y1="26" x2="50" y2="76" stroke="#000" stroke-width="2"/>
           <path d="M18 30 L10 22 M82 30 L90 22 M50 12 L50 4 M16 50 L6 50 M84 50 L94 50" stroke="#fff" stroke-width="3" stroke-linecap="round"/>`,
    flame: `<path d="M50 12 Q70 34 66 52 Q78 46 76 36 Q90 58 78 76 Q66 90 50 90 Q30 90 22 74 Q14 56 30 40 Q30 52 38 54 Q30 30 50 12Z" fill="C"/>
            <path d="M50 46 Q62 60 58 72 Q54 82 50 82 Q40 82 40 70 Q40 60 50 46Z" fill="#fef3c7"/>`,
    bullet: `<rect x="30" y="44" width="40" height="14" rx="2" fill="C"/><path d="M70 44 Q86 51 70 58Z" fill="#fff"/>
             <rect x="26" y="44" width="5" height="14" fill="#555"/>
             <path d="M14 46 L24 46 M10 51 L24 51 M14 56 L24 56" stroke="C" stroke-width="2" opacity=".6"/>`,
    cross: `<rect x="40" y="18" width="20" height="64" rx="4" fill="C"/><rect x="18" y="40" width="64" height="20" rx="4" fill="C"/>
            <circle cx="50" cy="50" r="38" fill="none" stroke="C" stroke-width="1.5" opacity=".5"/><circle cx="50" cy="50" r="6" fill="#fff"/>`,
    flash: `<path d="M56 8 L28 54 L46 54 L36 92 L74 40 L54 40 L66 8Z" fill="#000" stroke="C" stroke-width="3"/>
            <path d="M20 28 L36 38 M80 64 L64 58 M18 70 L32 64" stroke="C" stroke-width="2.5"/>`,
    fist: `<rect x="28" y="38" width="44" height="34" rx="9" fill="C"/>
           <path d="M38 38 L38 52 M50 38 L50 52 M62 38 L62 52" stroke="#000" stroke-width="2.5"/>
           <rect x="34" y="70" width="32" height="18" fill="C" opacity=".8"/>
           <rect x="24" y="30" width="52" height="42" rx="12" fill="none" stroke="C" stroke-width="1.5" opacity=".6" transform="translate(6 -6)"/>`,
    chain: `${[0, 1, 2, 3].map((i) => `<ellipse cx="${24 + i * 17}" cy="${70 - i * 14}" rx="12" ry="7" fill="none" stroke="C" stroke-width="4" transform="rotate(-40 ${24 + i * 17} ${70 - i * 14})"/>`).join('')}
            <path d="M80 18 L90 10 L86 24Z" fill="C"/>`,
    kick: `<circle cx="38" cy="26" r="8" fill="C"/><path d="M38 34 L42 58 L28 82 M42 58 L80 46 M40 42 L22 52 M40 42 L60 34" stroke="C" stroke-width="6" stroke-linecap="round" fill="none"/>
           <path d="M84 36 L94 30 M86 48 L96 48 M84 58 L92 64" stroke="#fff" stroke-width="2.5"/>`,
    circle: `<circle cx="50" cy="56" r="32" fill="none" stroke="C" stroke-width="3"/>
             <circle cx="50" cy="56" r="26" fill="C" opacity=".15"/><circle cx="50" cy="40" r="7" fill="#fff"/>
             <path d="M50 47 L50 66 M50 66 L42 78 M50 66 L58 78 M40 54 L60 54" stroke="#fff" stroke-width="3" stroke-linecap="round"/>`,
    sword: `<path d="M20 82 L74 20" stroke="#fff" stroke-width="4" stroke-linecap="round"/><path d="M16 74 L28 86" stroke="C" stroke-width="5"/>
            <path d="M12 88 L22 78" stroke="C" stroke-width="6" stroke-linecap="round"/>
            <circle cx="50" cy="50" r="36" fill="none" stroke="C" stroke-width="1.5" stroke-dasharray="4 3" opacity=".7"/>`,
    // ───── neue Symbole ─────
    heart: `<path d="M50 80 C20 60 14 42 24 30 C34 18 46 24 50 34 C54 24 66 18 76 30 C86 42 80 60 50 80Z" fill="C"/>
            ${[18, 34, 66, 82].map((x, i) => `<path d="M${x} ${88 - (i % 2) * 6} L${x} ${64 - (i % 2) * 6}" stroke="#fff" stroke-width="2" opacity=".7"/>`).join('')}`,
    wave: `<path d="M8 56 Q20 44 32 56 T56 56 T80 56 T104 56" fill="none" stroke="C" stroke-width="5"/>
           <path d="M8 70 Q20 58 32 70 T56 70 T80 70 T104 70" fill="none" stroke="C" stroke-width="3" opacity=".6"/>
           <path d="M40 40 Q50 30 60 40 L54 40 L50 46 L46 40Z" fill="#fff" opacity=".8"/><circle cx="74" cy="28" r="9" fill="#fde68a" opacity=".8"/>`,
    clock: `<circle cx="50" cy="50" r="32" fill="#000" stroke="C" stroke-width="3"/>
            <path d="M50 50 L50 28 M50 50 L66 58" stroke="C" stroke-width="4" stroke-linecap="round"/>
            ${Array.from({ length: 12 }, (_, i) => `<line x1="50" y1="21" x2="50" y2="26" stroke="C" stroke-width="2" transform="rotate(${i * 30} 50 50)"/>`).join('')}
            <path d="M80 26 A40 40 0 0 1 84 64" fill="none" stroke="#fff" stroke-width="2" opacity=".6"/>`,
    sphere: `<circle cx="50" cy="50" r="34" fill="C" opacity=".2"/><circle cx="50" cy="50" r="22" fill="C" opacity=".55"/>
             <circle cx="50" cy="50" r="12" fill="C"/><circle cx="45" cy="45" r="5" fill="#fff" opacity=".85"/>
             <path d="M14 50 A36 12 0 0 0 86 50" fill="none" stroke="C" stroke-width="1.5" opacity=".7"/>`,
    mirror: `<rect x="18" y="22" width="28" height="56" rx="4" fill="none" stroke="C" stroke-width="3"/>
             <rect x="54" y="22" width="28" height="56" rx="4" fill="C" opacity=".5"/>
             <path d="M32 36 L32 64 M68 36 L68 64" stroke="#fff" stroke-width="3"/><line x1="50" y1="14" x2="50" y2="86" stroke="#fff" stroke-dasharray="3 3"/>`,
    leaf: `<path d="M20 80 Q20 26 80 20 Q76 78 20 80Z" fill="C"/><path d="M20 80 Q46 54 72 28" stroke="#052e16" stroke-width="3" fill="none"/>
           <circle cx="76" cy="72" r="8" fill="#f9a8d4"/><circle cx="76" cy="72" r="3" fill="#fde68a"/>`,
    snow: `${[0, 60, 120].map((r) => `<g transform="rotate(${r} 50 50)"><line x1="50" y1="14" x2="50" y2="86" stroke="C" stroke-width="4"/>
           <path d="M42 24 L50 32 L58 24 M42 76 L50 68 L58 76" fill="none" stroke="C" stroke-width="3"/></g>`).join('')}<circle cx="50" cy="50" r="6" fill="#fff"/>`,
    film: `<rect x="14" y="30" width="72" height="40" fill="#000" stroke="C" stroke-width="2"/>
           ${[0, 1, 2, 3].map((i) => `<rect x="${18 + i * 17}" y="38" width="13" height="24" fill="C" opacity="${0.3 + i * 0.2}"/>`).join('')}
           ${Array.from({ length: 9 }, (_, i) => `<rect x="${16 + i * 8}" y="32" width="4" height="3" fill="C"/><rect x="${16 + i * 8}" y="65" width="4" height="3" fill="C"/>`).join('')}`,
    katana: `<path d="M18 84 Q50 54 86 14" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round"/>
             <path d="M24 70 L34 80" stroke="C" stroke-width="5"/><path d="M12 92 L26 76" stroke="C" stroke-width="6" stroke-linecap="round"/>
             <path d="M30 76 Q52 52 80 22" fill="none" stroke="C" stroke-width="1.5" opacity=".7"/>`,
    basket: `<path d="M20 44 L80 44 L72 82 L28 82Z" fill="none" stroke="C" stroke-width="3"/>
             ${[0, 1, 2, 3].map((i) => `<path d="M${24 + i * 2} ${52 + i * 8} L${76 - i * 2} ${52 + i * 8}" stroke="C" stroke-width="2" opacity=".7"/>`).join('')}
             ${[34, 50, 66].map((x) => `<line x1="${x}" y1="44" x2="${x}" y2="82" stroke="C" stroke-width="2" opacity=".6"/>`).join('')}
             <path d="M28 44 Q50 14 72 44" fill="none" stroke="C" stroke-width="3"/>`,
    spear: `<path d="M20 80 L66 34" stroke="#d6d3d1" stroke-width="5" stroke-linecap="round"/>
            <path d="M62 30 L86 14 L70 38Z" fill="C"/><path d="M66 34 L80 26 L74 40" fill="none" stroke="#fff" stroke-width="1.5"/>
            <circle cx="22" cy="78" r="6" fill="none" stroke="C" stroke-width="3"/><path d="M28 72 L60 40" stroke="C" stroke-width="1" opacity=".6" stroke-dasharray="3 3"/>`,
    cloud: `<rect x="14" y="44" width="22" height="10" rx="5" fill="C" transform="rotate(-20 25 49)"/>
            <rect x="40" y="40" width="22" height="10" rx="5" fill="C"/><rect x="66" y="44" width="22" height="10" rx="5" fill="C" transform="rotate(20 77 49)"/>
            <path d="M34 46 Q38 40 42 44 M60 44 Q64 40 68 46" fill="none" stroke="#fff" stroke-width="2"/>
            <path d="M18 70 Q34 62 50 70 T82 70" fill="none" stroke="C" stroke-width="2" opacity=".5"/>`,
    cube: `<path d="M50 16 L82 32 L82 68 L50 84 L18 68 L18 32Z" fill="#000" stroke="C" stroke-width="3"/>
           <path d="M18 32 L50 48 L82 32 M50 48 L50 84" stroke="C" stroke-width="2"/>
           <circle cx="36" cy="58" r="4" fill="C"/><circle cx="64" cy="58" r="4" fill="C"/><circle cx="50" cy="30" r="4" fill="C"/>`,
    hammer: `<rect x="28" y="20" width="44" height="18" rx="3" fill="C"/><rect x="46" y="38" width="8" height="46" rx="2" fill="#a16207"/>
             <path d="M74 60 L86 72 M80 54 L90 64" stroke="#d4d4d8" stroke-width="3" stroke-linecap="round"/>`,
    gun: `<path d="M16 40 L76 40 L80 46 L76 52 L42 52 L36 74 L22 74 L26 52 L16 52Z" fill="C"/>
          <circle cx="46" cy="50" r="6" fill="none" stroke="#000" stroke-width="2"/><path d="M80 46 L94 46" stroke="#fde68a" stroke-width="3"/>`,
    finger: `<path d="M40 86 L40 30 Q40 18 50 18 Q60 18 60 30 L60 86Z" fill="#7f1d1d" stroke="C" stroke-width="2"/>
             <path d="M42 40 L58 40 M42 56 L58 56 M42 70 L58 70" stroke="#000" stroke-width="2"/>
             <rect x="43" y="20" width="14" height="8" rx="3" fill="#000"/>
             <path d="M30 30 L22 22 M70 30 L78 22 M28 50 L18 50 M72 50 L82 50" stroke="C" stroke-width="2"/>`,
    blindfold: `<path d="M8 44 Q50 34 92 44 L92 58 Q50 48 8 58Z" fill="#0a0a0a" stroke="C" stroke-width="2"/>
                <path d="M50 22 Q34 30 30 44 M50 22 Q66 30 70 44" fill="none" stroke="#fff" stroke-width="2" opacity=".8"/>
                <path d="M82 58 Q88 70 80 82 M88 56 Q96 66 92 78" fill="none" stroke="#0a0a0a" stroke-width="5"/>`,
    ring: `<ellipse cx="50" cy="60" rx="24" ry="20" fill="none" stroke="C" stroke-width="7"/>
           <path d="M42 34 L50 22 L58 34 L50 42Z" fill="#fff"/><path d="M50 22 L50 42" stroke="C" stroke-width="1"/>`,
    rope: `<path d="M14 30 Q34 10 50 30 T86 30 Q90 50 70 52 T30 58 Q10 66 26 82 T74 84" fill="none" stroke="C" stroke-width="5"/>
           <path d="M14 30 Q34 10 50 30 T86 30" fill="none" stroke="#000" stroke-width="1.5" stroke-dasharray="3 3"/>`,
    scroll: `<rect x="26" y="20" width="48" height="60" fill="#fef3c7"/><rect x="20" y="16" width="60" height="8" rx="4" fill="C"/>
             <rect x="20" y="76" width="60" height="8" rx="4" fill="C"/>
             <path d="M34 34 L66 34 M34 44 L62 44 M34 54 L66 54 M34 64 L56 64" stroke="#78350f" stroke-width="2"/>
             <circle cx="64" cy="66" r="7" fill="#b91c1c"/>`,
    bolt: `<path d="M60 8 L30 52 L48 52 L38 92 L74 42 L54 42 L68 8Z" fill="C"/>
           <line x1="50" y1="92" x2="50" y2="98" stroke="C"/><path d="M18 30 L28 36 M82 66 L72 60" stroke="#fff" stroke-width="2"/>`,
    worm: `${[0, 1, 2, 3, 4].map((i) => `<circle cx="${22 + i * 13}" cy="${60 - Math.sin(i * 0.9) * 12}" r="${11 - i}" fill="C" opacity="${1 - i * 0.12}"/>`).join('')}
           <circle cx="18" cy="56" r="3" fill="#000"/><circle cx="26" cy="54" r="3" fill="#000"/>
           <path d="M14 66 Q22 72 30 66" stroke="#000" stroke-width="2" fill="none"/>
           <path d="M58 30 L74 14 M66 34 L86 22" stroke="#e5e7eb" stroke-width="3" stroke-linecap="round"/>`,
    blade: `<path d="M24 80 L76 28" stroke="#e5e7eb" stroke-width="7" stroke-linecap="round"/>
            ${[0, 1, 2, 3, 4].map((i) => `<path d="M${36 + i * 8} ${70 - i * 8} l6 -6" stroke="C" stroke-width="4"/>`).join('')}
            <path d="M18 86 L28 76" stroke="C" stroke-width="6" stroke-linecap="round"/>`,
  };

  // Ein Bild für eine Fähigkeit als SVG-Text
  function abilitySVG(ab, opts) {
    opts = opts || {};
    const a = ab.art;
    const uid = 'g' + ab.id.replace(/[^a-z0-9]/gi, '') + (opts.uid || '');
    const glyph = (G[a.glyph] || '').replace(/"C"/g, `"${a.c2}"`);
    return `<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${ab.name}">
      <defs>
        <radialGradient id="${uid}" cx="50%" cy="45%" r="75%">
          <stop offset="0" stop-color="${a.c2}" stop-opacity=".55"/>
          <stop offset=".55" stop-color="${a.c1}"/>
          <stop offset="1" stop-color="#000"/>
        </radialGradient>
      </defs>
      <rect width="100" height="100" fill="url(#${uid})"/>
      <g opacity=".12" stroke="#fff" stroke-width=".5">${[15, 30, 45, 60, 75, 90].map((y) => `<line x1="0" y1="${y}" x2="100" y2="${y - 20}"/>`).join('')}</g>
      <g>${glyph}</g>
      ${opts.noSeal ? '' : `<g transform="translate(72 72)"><rect width="22" height="22" rx="2" fill="#b91c1c" opacity=".92"/>
        <text x="11" y="17" text-anchor="middle" font-size="16" fill="#fff" font-family="'Noto Serif JP', serif" font-weight="700">${a.kanji}</text></g>`}
    </svg>`;
  }

  window.Art = { abilitySVG };
})();
