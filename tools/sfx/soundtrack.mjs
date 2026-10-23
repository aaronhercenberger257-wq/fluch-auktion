// Tonspuren für die Domain-Animationen und die Mahoraga-Clips.
// Alle Klänge werden synthetisch erzeugt (synth.mjs) – keine fremden Aufnahmen, keine Rechte-Probleme.
//
//   node tools/sfx/soundtrack.mjs            → tools/sfx/tracks/<name>.wav
//
// Die Zeitpunkte folgen den Blender-Szenen: gebaut wird mit 288 Bildern (12 s), danach auf 432 Bilder (18 s)
// gestreckt (siehe blender/scenes.py: SEG_OLD → SEG_NEW). Hier wird dieselbe Umrechnung benutzt.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SR, buf, env, decay, osc, noise, filter, mul, gain, drive, mix, reverb, master, wav, analyze, RECIPES } from "./synth.mjs";

const OUT = path.join(path.dirname(fileURLToPath(import.meta.url)), "tracks");
const FPS = 24;

function rng(seed) {
  let s = seed >>> 0 || 1;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}
const piecewise = (oldSeg, newSeg) => (f) => {
  for (let i = 0; i < oldSeg.length - 1; i++) {
    const a = oldSeg[i], b = oldSeg[i + 1];
    if (f < b || i === oldSeg.length - 2) return newSeg[i] + ((f - a) * (newSeg[i + 1] - newSeg[i])) / (b - a);
  }
  return f;
};
const DOMAIN_T = piecewise([1, 43, 63, 111, 139, 181, 247, 289], [1, 61, 85, 151, 191, 281, 381, 433]);
const MAHO_T = piecewise([1, 61, 145], [1, 97, 217]);

// ───────── Spur zusammensetzen ─────────
class Track {
  constructor(sec, T) {
    this.buf = buf(sec);
    this.T = T;
  }
  /** Klang zur Zeit eines (alten) Animationsbilds einfügen */
  at(frame, sig, vol = 1) {
    const start = Math.round(((this.T(frame) - 1) / FPS) * SR);
    for (let i = 0; i < sig.length && start + i < this.buf.length; i++) if (start + i >= 0) this.buf[start + i] += sig[i] * vol;
  }
  /** Klang auf eine Strecke (alte Bilder) gestreckt/geschleift legen, mit Ein-/Ausblenden */
  span(f0, f1, make, vol = 1, fade = 0.4) {
    const s = ((this.T(f0) - 1) / FPS) * SR, e = ((this.T(f1) - 1) / FPS) * SR;
    const len = Math.max(1, Math.round(e - s));
    const sig = make(len / SR);
    const fs_ = Math.min(len / 2, fade * SR);
    for (let i = 0; i < len && s + i < this.buf.length; i++) {
      const g = Math.min(1, i / fs_, (len - i) / fs_);
      this.buf[Math.round(s) + i] += (sig[i % sig.length] || 0) * vol * g;
    }
  }
  render() {
    return master(reverb(this.buf, { size: 1.1, mixAmt: 0.12, tail: 1.0 }), { peakDb: -1, fadeMs: 200 });
  }
}

// ───────── Eigene Bausteine ─────────
const hp = (s, f) => filter(s, "highpass", f);
const lp = (s, f) => filter(s, "lowpass", f);
const bp = (s, f, q = 1) => filter(s, "bandpass", f, q);

const drone = (f, color = "saw", cut = 600) => (sec) =>
  mul(lp(mix(sec, [[osc(sec, () => f, color), 0, 0.6], [osc(sec, () => f * 1.005, color), 0, 0.6], [osc(sec, () => f / 2), 0, 0.8]]), cut),
    env(sec, (t) => 0.5 + 0.15 * Math.sin(t * 1.3)));
const wind = (seed, cut = 900) => (sec) => mul(bp(noise(sec, "pink", seed), (t) => cut * (0.7 + 0.3 * Math.sin(t * 0.7)), 0.8), env(sec, (t) => 0.6 + 0.3 * Math.sin(t * 0.4)));
const crackle = (seed, rate = 40) => (sec) => {
  const r = rng(seed), out = buf(sec);
  for (let k = 0; k < sec * rate; k++) {
    const pos = Math.floor(r() * out.length), len = 60 + Math.floor(r() * 300), amp = 0.2 + r() * 0.8;
    for (let i = 0; i < len && pos + i < out.length; i++) out[pos + i] += (r() * 2 - 1) * amp * Math.exp(-i / (len / 4));
  }
  return mix(sec, [[hp(out, 1200), 0, 0.6], [lp(noise(sec, "brown", seed + 1), 300), 0, 0.5]]);
};
const ocean = (seed) => (sec) => mul(lp(noise(sec, "pink", seed), 1400), env(sec, (t) => 0.35 + 0.35 * (0.5 + 0.5 * Math.sin(t * 0.9)) ** 2));
const shimmerPad = (base) => (sec) => mix(sec, [base, base * 1.5, base * 2, base * 3].map((f, i) => [mul(osc(sec, (t) => f * (1 + 0.003 * Math.sin(t * 3 + i))), env(sec, () => 0.25)), 0, 0.5 / (i + 1)]));
const arcade = (seed) => (sec) => {
  const r = rng(seed), layers = [];
  for (let t = 0; t < sec; t += 0.11 + r() * 0.25) {
    const f = [880, 1175, 1568, 1760, 2093][Math.floor(r() * 5)];
    layers.push([mul(osc(0.09, () => f, "square"), decay(0.09, 0.001, 0.03)), t, 0.25]);
  }
  return mix(sec, layers);
};
const projector = (seed) => (sec) => {
  const clicks = [];
  for (let t = 0; t < sec; t += 1 / 24) clicks.push([mul(hp(noise(0.01, "white", seed + Math.round(t * 99)), 2500), decay(0.01, 0.0005, 0.002)), t, 0.3]);
  return mix(sec, [[mix(sec, clicks), 0, 1], [mul(osc(sec, () => 120, "tri"), env(sec, () => 0.2)), 0, 1]]);
};
const knock = (seed) => master(mix(0.5, [[mul(osc(0.4, (t) => 220 * Math.exp(-t * 8) + 90), decay(0.4, 0.001, 0.07)), 0, 1],
  [mul(bp(noise(0.08, "white", seed), 1800, 2), decay(0.08, 0.0005, 0.012)), 0, 1.2]]));
const bell = (f) => master(mix(3, [1, 2.4, 3.9, 5.4].map((m, i) => [mul(osc(3, () => f * m), decay(3, 0.002, 1.4 / (i + 1))), 0, 0.5 / (i + 1)])));
const clunk = (seed) => master(mix(0.6, [[RECIPES.sword_clash(seed), 0, 0.5], [mul(osc(0.5, (t) => 140 * Math.exp(-t * 10) + 70), decay(0.5, 0.001, 0.1)), 0, 1]]));
const glassBreak = (seed) => {
  const r = rng(seed), layers = [];
  for (let i = 0; i < 30; i++) {
    const f = 2500 + r() * 6000;
    layers.push([mul(osc(0.3, () => f), decay(0.3, 0.0005, 0.03 + r() * 0.05)), r() * 0.25, 0.2 + r() * 0.3]);
  }
  return master(mix(0.8, [[mix(0.6, layers), 0, 1], [mul(hp(noise(0.3, "white", seed), 3000), decay(0.3, 0.0005, 0.06)), 0, 0.8]]));
};
const splash = (seed) => master(mix(0.8, [[mul(bp(noise(0.8, "white", seed), (t) => 2500 - t * 2000, 1), decay(0.8, 0.002, 0.2)), 0, 1],
  [mul(lp(noise(0.5, "brown", seed + 2), 400), decay(0.5, 0.003, 0.12)), 0, 0.8]]));
const thud = (seed) => master(mix(0.8, [[mul(osc(0.7, (t) => 90 * Math.exp(-t * 5) + 45), decay(0.7, 0.002, 0.2)), 0, 1.2],
  [mul(lp(noise(0.5, "brown", seed), 500), decay(0.5, 0.002, 0.12)), 0, 0.8]]));
const growl = (seed) => master(mul(lp(mix(1.0, [[osc(1, (t) => 85 + 10 * Math.sin(t * 30), "saw"), 0, 1], [noise(1, "brown", seed), 0, 0.8]]), 700), env(1, (t) => Math.sin(Math.PI * t))));
const warble = (seed) => (sec) => mul(lp(osc(sec, (t) => 300 + 200 * Math.sin(t * 9) + 120 * Math.sin(t * 2.3), "tri"), 1600), env(sec, () => 0.5));
const chord = (notes) => master(reverb(mix(3, notes.map((f, i) => [mul(mix(3, [[osc(3, () => f, "tri"), 0, 1], [osc(3, () => f * 2), 0, 0.3]]), decay(3, 0.02, 1.4)), i * 0.05, 0.4])), { size: 1.4, mixAmt: 0.4, tail: 2 }));
const R = (name, seed) => RECIPES[name](seed);

// ───────── Gemeinsamer Ablauf aller Domain-Videos ─────────
function common(tr, d) {
  tr.span(1, 43, crackle(d.seed, 60), 0.5);                // Clash: Energie knistert
  tr.span(1, 43, drone(55, "saw", 300), 0.35);
  tr.at(2, R("energy_release", d.seed), 0.7);
  tr.at(30, R("explosion", d.seed + 1), 0.35);
  tr.at(42, R("whoosh", d.seed + 2), 1.0);                  // Reißschwenk
  tr.at(61, R("teleport", d.seed + 3), 0.5);
  tr.span(63, 111, (s) => R("charge_up", d.seed + 4), 0.7);  // Fingerzeichen: Aufladen
  tr.at(63, R("impact_frame", d.seed + 5), 0.7);            // „領域展開“
  tr.at(111, d.eyeSound || R("holy_shimmer", d.seed + 6), 0.8);
  tr.span(139, 151, (s) => R("charge_up", d.seed + 7), 0.8); // Domain schwillt an …
  tr.at(151, R("explosion", d.seed + 8), 1.0);              // … und entfaltet sich
  tr.at(151, R("impact_frame", d.seed + 9), 0.8);
  tr.span(151, 289, d.ambience, d.ambVol ?? 0.55, 1.2);     // Domain-Atmosphäre
  tr.at(247, R("whoosh", d.seed + 10), 0.8);                // Siegerpose
  tr.at(249, chord(d.victory || [261.6, 329.6, 392, 523.3]), 0.7);
  tr.at(249, R("void_pulse", d.seed + 11), 0.4);
}

const DOMAINS = {
  void: { seed: 11, ambience: (s) => mix(s, [[drone(49, "sine", 200)(s), 0, 1], [shimmerPad(392)(s), 0, 0.35]]), victory: [246.9, 311.1, 370, 493.9],
    eyeSound: R("void_pulse", 3),
    finish(tr) {
      tr.span(181, 216, (s) => { const l = []; const r = rng(5); for (let t = 0; t < s; t += 0.03) l.push([mul(osc(0.03, () => 1500 + r() * 4000, "square"), decay(0.03, 0.001, 0.008)), t, 0.15 + 0.4 * (t / s)]); return mix(s, l); }, 0.6);
      tr.at(199, R("void_pulse", 7), 0.9);
      tr.at(218, R("teleport", 8), 1.0);
      tr.at(226, R("impact_frame", 9), 1.0);
      tr.at(227, R("punch_heavy", 10), 1.0);
      tr.at(232, R("whoosh", 11), 0.7);
      tr.at(244, thud(12), 0.7);
    } },
  shrine: { seed: 21, ambience: (s) => mix(s, [[drone(41, "saw", 260)(s), 0, 1], [wind(4, 500)(s), 0, 0.6]]), victory: [220, 261.6, 311.1, 440],
    finish(tr) {
      for (let i = 0; i < 26; i++) tr.at(184 + i * 1.3, R("slash_hit", 30 + i), 0.45 + (i % 3) * 0.1);
      tr.at(216, R("sword_clash", 60), 0.9);
      tr.at(217, R("impact_frame", 61), 1.0);
      tr.at(219, R("explosion", 62), 0.8);
    } },
  shadow: { seed: 31, ambience: (s) => mix(s, [[drone(36, "sine", 180)(s), 0, 1], [crackle(7, 6)(s), 0, 0.3]]), victory: [196, 233.1, 293.7, 392],
    finish(tr) {
      tr.span(186, 214, (s) => R("charge_up", 70), 0.5);
      tr.at(205, growl(71), 0.9);
      tr.at(209, growl(72), 0.8);
      tr.at(214, R("punch_heavy", 73), 0.9);
      tr.at(222, R("punch_light", 74), 0.8);
      tr.span(214, 246, drone(40, "saw", 250), 0.6);
      tr.at(244, R("void_pulse", 75), 1.0);
    } },
  hands: { seed: 41, ambience: (s) => mix(s, [[drone(58, "tri", 400)(s), 0, 0.8], [warble(3)(s), 0, 0.15], [wind(5, 1500)(s), 0, 0.3]]), victory: [233.1, 277.2, 349.2, 466.2],
    finish(tr) {
      tr.at(190, R("whoosh", 80), 0.9);
      tr.at(202, R("teleport", 81), 0.8);
      tr.at(206, R("void_pulse", 82), 1.0);
      tr.span(206, 228, warble(83), 0.8);
      tr.span(228, 245, (s) => R("charge_up", 84).reverse(), 0.8);
      tr.at(244, R("punch_light", 85), 0.7);
    } },
  volcano: { seed: 51, ambience: (s) => mix(s, [[crackle(9, 90)(s), 0, 0.9], [drone(43, "saw", 220)(s), 0, 0.7]]), victory: [174.6, 220, 261.6, 349.2],
    finish(tr) {
      for (let i = 0; i < 7; i++) tr.at(196 + i * 2, R("explosion", 90 + i), 0.4);
      tr.at(210, R("explosion", 99), 1.0);
      tr.at(211, R("impact_frame", 98), 0.8);
      tr.span(214, 240, crackle(97, 160), 0.6);
    } },
  court: { seed: 61, ambience: (s) => mix(s, [[drone(65, "sine", 300)(s), 0, 0.7], [wind(6, 700)(s), 0, 0.2]]), victory: [261.6, 329.6, 392, 523.3],
    finish(tr) {
      tr.at(192, knock(100), 1.0);
      tr.at(194, bell(196), 0.8);
      tr.at(204, R("holy_shimmer", 101), 0.7);
      tr.at(216, R("whoosh", 102), 0.9);
      tr.at(220, R("slash_hit", 103), 1.0);
      tr.at(221, R("impact_frame", 104), 0.9);
      tr.at(236, thud(105), 0.8);
    } },
  gamble: { seed: 71, ambience: (s) => mix(s, [[arcade(8)(s), 0, 0.7], [drone(73, "square", 500)(s), 0, 0.25]]), victory: [523.3, 659.3, 784, 1046.5],
    finish(tr) {
      tr.span(181, 199, (s) => { const l = []; for (let t = 0; t < s; t += 0.05) l.push([R("ui_click", 110 + Math.round(t * 100)), t, 0.5]); return mix(s, l); }, 0.8);
      [199, 204, 209].forEach((f, i) => tr.at(f, clunk(111 + i), 0.9));
      tr.at(211, R("level_up", 114), 1.0);
      for (let i = 0; i < 10; i++) tr.at(212 + i * 1.2, R("coin", 115 + i), 0.5);
      tr.at(216, R("whoosh", 126), 0.9);
      tr.at(222, R("punch_heavy", 127), 1.0);
      tr.at(223, R("impact_frame", 128), 0.9);
    } },
  swords: { seed: 81, ambience: (s) => mix(s, [[wind(9, 1100)(s), 0, 0.8], [shimmerPad(587)(s), 0, 0.15]]), victory: [293.7, 370, 440, 587.3],
    finish(tr) {
      for (let i = 0; i < 12; i++) tr.at(186 + i * 2, R("sword_clash", 130 + i), 0.25);
      tr.span(192, 212, (s) => R("charge_up", 145), 0.5);
      for (let i = 0; i < 14; i++) tr.at(202 + i * 1.5, R("slash_hit", 150 + i), 0.45);
      tr.at(214, R("impact_frame", 170), 1.0);
      tr.at(215, glassBreak(171), 0.6);
    } },
  beach: { seed: 91, ambience: (s) => mix(s, [[ocean(10)(s), 0, 1], [wind(11, 2200)(s), 0, 0.2]]), victory: [349.2, 440, 523.3, 698.5],
    finish(tr) {
      for (let i = 0; i < 10; i++) tr.at(182 + i * 4, R("whoosh", 180 + i), 0.45);
      for (let i = 0; i < 6; i++) tr.at(186 + i * 7, splash(190 + i), 0.5);
      tr.at(226, splash(197), 1.0);
      tr.at(236, R("explosion", 198), 0.5);
    } },
  frames: { seed: 101, ambience: (s) => mix(s, [[projector(12)(s), 0, 0.7], [drone(82, "sine", 400)(s), 0, 0.5]]), victory: [311.1, 392, 466.2, 622.3],
    finish(tr) {
      [184, 190, 196, 202, 208].forEach((f, i) => tr.at(f, R("teleport", 200 + i), 0.7));
      tr.at(200, R("void_pulse", 206), 0.6);
      tr.at(221, R("impact_frame", 207), 1.0);
      tr.at(222, glassBreak(208), 1.0);
    } },
};

// ───────── Mahoraga ─────────
function mahoraga(win) {
  const tr = new Track(9, MAHO_T);
  tr.span(1, 18, drone(46, "saw", 260), 0.6);
  tr.at(4, R("charge_up", 300), 0.6);
  tr.span(18, 56, (s) => mix(s, [[drone(36, "saw", 220)(s), 0, 1], [wind(12, 400)(s), 0, 0.6]]), 0.9);
  tr.at(18, R("void_pulse", 301), 1.0);
  tr.at(54, thud(302), 1.0);
  [59, 67].forEach((f, i) => tr.at(f, clunk(303 + i), 1.0));      // das Rad klickt
  if (!win) {
    tr.at(71, R("charge_up", 310), 0.4);
    tr.at(73, R("whoosh", 311), 1.0);
    tr.at(77, R("impact_frame", 312), 1.0);
    tr.at(77, R("punch_heavy", 313), 1.0);
    tr.at(80, R("whoosh", 314), 0.8);
    tr.at(100, R("explosion", 315), 0.7);
    tr.at(121, clunk(316), 0.9);
    tr.span(101, 145, drone(41, "saw", 240), 0.5);
  } else {
    tr.at(64, R("whoosh", 320), 1.0);
    tr.at(75, R("impact_frame", 321), 1.0);
    tr.at(75, R("energy_release", 322), 0.9);
    tr.at(76, R("punch_heavy", 323), 1.0);
    tr.span(76, 90, crackle(324, 120), 0.7);
    tr.at(96, thud(325), 1.0);
    tr.at(97, R("holy_shimmer", 326), 0.9);
    tr.at(104, chord([261.6, 329.6, 392, 523.3]), 0.7);
  }
  return tr.render();
}

fs.mkdirSync(OUT, { recursive: true });
const report = [];
for (const [name, d] of Object.entries(DOMAINS)) {
  const tr = new Track(18, DOMAIN_T);
  common(tr, d);
  d.finish(tr);
  const sig = tr.render();
  fs.writeFileSync(path.join(OUT, name + ".wav"), wav(sig));
  report.push(name + ": " + JSON.stringify(analyze(sig)));
  console.log("ok", name);
}
for (const [name, w] of [["mahoraga_win", true], ["mahoraga_lose", false]]) {
  const sig = mahoraga(w);
  fs.writeFileSync(path.join(OUT, name + ".wav"), wav(sig));
  report.push(name + ": " + JSON.stringify(analyze(sig)));
  console.log("ok", name);
}
fs.writeFileSync(path.join(OUT, "_report.txt"), report.join("\n") + "\n");
console.log(report.join("\n"));
