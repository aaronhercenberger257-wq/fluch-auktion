/**
 * synth.mjs -- Soundeffekte per Synthese, reines Node (keine Abhängigkeit).
 *
 * Warum selbst bauen: Im Plugin-Katalog gibt es nichts für Spiel-SFX ohne
 * Fremdkonto. Synthese liefert eigene, rechtefreie Sounds (Roblox verlangt
 * Rechte am Audio) in beliebig vielen Varianten.
 *
 * Aufruf:  node tools/sfx/synth.mjs [nur,diese,rezepte]
 * Ausgabe: tools/sfx/out/<rezept>_<n>.wav  (44,1 kHz, mono, 16 bit)
 *          tools/sfx/out/_report.txt       (Länge, Spitze, Lautheit, Klangfarbe)
 *          tools/sfx/out/_wave.png         (Wellenform + Spektrogramm je Sound)
 *
 * Roblox-Import: .wav erlaubt, < 7 min, < 20 MB, <= 48 kHz, mono ok.
 * Rezepte bestehen aus Schichten nach dem Profi-Prinzip:
 *   Transient (Knack, 0-30 ms) + Körper (Wumms/Ton) + Schwanz (Hall/Rauschen).
 */

import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath } from "node:url";

const OUT = path.join(path.dirname(fileURLToPath(import.meta.url)), "out");
export const SR = 44100;

// --- Zufall -------------------------------------------------------------------

function rng(seed = 1) {
  let s = seed >>> 0 || 1;
  return () => {
    s ^= s << 13;
    s >>>= 0;
    s ^= s >>> 17;
    s ^= s << 5;
    s >>>= 0;
    return s / 4294967296;
  };
}

// --- Grundbausteine (alle liefern Float32Array) --------------------------------

export const buf = (sec) => new Float32Array(Math.max(1, Math.round(sec * SR)));

/** Hüllkurve: Werte zur Zeit t (s) per Funktion. */
export function env(len, fn) {
  const out = buf(len);
  for (let i = 0; i < out.length; i++) out[i] = fn(i / SR);
  return out;
}
/** Schneller Anstieg, exponentielles Abklingen. */
export const decay = (len, attack, tau) =>
  env(len, (t) => (t < attack ? t / attack : Math.exp(-(t - attack) / tau)));

/** Oszillator mit Frequenz-Verlauf freqFn(t). */
export function osc(len, freqFn, shape = "sine") {
  const out = buf(len);
  let phase = 0;
  for (let i = 0; i < out.length; i++) {
    phase += freqFn(i / SR) / SR;
    const p = phase % 1;
    out[i] =
      shape === "sine"
        ? Math.sin(2 * Math.PI * p)
        : shape === "tri"
          ? 1 - 4 * Math.abs(p - 0.5)
          : shape === "saw"
            ? 2 * p - 1
            : p < 0.5
              ? 1
              : -1;
  }
  return out;
}

/** Rauschen: white, pink oder brown. */
export function noise(len, color = "white", seed = 1) {
  const r = rng(seed);
  const out = buf(len);
  let b0 = 0,
    b1 = 0,
    b2 = 0,
    last = 0;
  for (let i = 0; i < out.length; i++) {
    const w = r() * 2 - 1;
    if (color === "pink") {
      b0 = 0.99765 * b0 + w * 0.099046;
      b1 = 0.963 * b1 + w * 0.2965164;
      b2 = 0.57 * b2 + w * 1.0526913;
      out[i] = (b0 + b1 + b2 + w * 0.1848) * 0.18;
    } else if (color === "brown") {
      last = (last + 0.02 * w) / 1.02;
      out[i] = last * 3.5;
    } else out[i] = w;
  }
  return out;
}

/**
 * Biquad-Filter mit zeitlich veränderlicher Grenzfrequenz cutFn(t).
 * type: lowpass | highpass | bandpass, q = Resonanz.
 */
export function filter(input, type, cutFn, q = 0.707) {
  const out = new Float32Array(input.length);
  let x1 = 0,
    x2 = 0,
    y1 = 0,
    y2 = 0;
  const fn = typeof cutFn === "function" ? cutFn : () => cutFn;
  for (let i = 0; i < input.length; i++) {
    const f0 = Math.min(SR * 0.45, Math.max(20, fn(i / SR)));
    const w0 = (2 * Math.PI * f0) / SR;
    const alpha = Math.sin(w0) / (2 * q);
    const cos = Math.cos(w0);
    let b0, b1, b2;
    if (type === "lowpass") {
      b0 = (1 - cos) / 2;
      b1 = 1 - cos;
      b2 = (1 - cos) / 2;
    } else if (type === "highpass") {
      b0 = (1 + cos) / 2;
      b1 = -(1 + cos);
      b2 = (1 + cos) / 2;
    } else {
      b0 = alpha;
      b1 = 0;
      b2 = -alpha;
    }
    const a0 = 1 + alpha;
    const a1 = -2 * cos;
    const a2 = 1 - alpha;
    const x = input[i];
    const y = (b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2) / a0;
    x2 = x1;
    x1 = x;
    y2 = y1;
    y1 = y;
    out[i] = y;
  }
  return out;
}

export function mul(a, b) {
  const out = new Float32Array(a.length);
  for (let i = 0; i < a.length; i++) out[i] = a[i] * (b[i] ?? 0);
  return out;
}
export function gain(a, g) {
  return a.map((v) => v * g);
}
/** Sättigung (tanh) -- macht Treffer dicker. */
export function drive(a, amount = 2) {
  const n = Math.tanh(amount);
  return a.map((v) => Math.tanh(v * amount) / n);
}

/** Schichten mischen: [[signal, startSek, lautstärke], ...]. */
export function mix(len, layers) {
  const out = buf(len);
  for (const [sig, start = 0, vol = 1] of layers) {
    const off = Math.round(start * SR);
    for (let i = 0; i < sig.length && i + off < out.length; i++) out[i + off] += sig[i] * vol;
  }
  return out;
}

/** Einfacher Hall (Schroeder: 4 Kammfilter + 2 Allpässe). */
export function reverb(input, { size = 1, mixAmt = 0.3, damp = 0.4, tail = 1.2 } = {}) {
  const len = input.length + Math.round(tail * SR);
  const dry = new Float32Array(len);
  dry.set(input);
  const combs = [1116, 1188, 1277, 1356].map((d) => Math.round(d * size));
  const wet = new Float32Array(len);
  for (const d of combs) {
    const line = new Float32Array(d);
    let idx = 0;
    let lp = 0;
    for (let i = 0; i < len; i++) {
      const outv = line[idx];
      lp = outv * (1 - damp) + lp * damp;
      line[idx] = dry[i] + lp * 0.84;
      wet[i] += outv;
      idx = (idx + 1) % d;
    }
  }
  let sig = wet;
  for (const d of [556, 441].map((x) => Math.round(x * size))) {
    const line = new Float32Array(d);
    let idx = 0;
    const out = new Float32Array(len);
    for (let i = 0; i < len; i++) {
      const bufv = line[idx];
      const v = -sig[i] * 0.5 + bufv;
      line[idx] = sig[i] + bufv * 0.5;
      out[i] = v;
      idx = (idx + 1) % d;
    }
    sig = out;
  }
  const out = new Float32Array(len);
  for (let i = 0; i < len; i++) out[i] = dry[i] * (1 - mixAmt) + sig[i] * mixAmt * 0.25;
  return out;
}

/** Endbearbeitung: Gleichanteil weg, normalisieren (-1 dBFS), Ausblenden, Stille kürzen. */
export function master(sig, { peakDb = -1, fadeMs = 30 } = {}) {
  let mean = 0;
  for (const v of sig) mean += v;
  mean /= sig.length;
  let s = filter(sig.map((v) => v - mean), "highpass", 40, 0.7);
  s = s.map((v) => Math.tanh(v * 1.1)); // weicher Begrenzer
  let peak = 0;
  for (const v of s) peak = Math.max(peak, Math.abs(v));
  const target = 10 ** (peakDb / 20);
  s = s.map((v) => (v / (peak || 1)) * target);
  // Stille am Ende abschneiden (unter -60 dB).
  let end = s.length;
  while (end > SR * 0.05 && Math.abs(s[end - 1]) < 0.001) end--;
  s = s.slice(0, end);
  const fade = Math.min(s.length, Math.round((fadeMs / 1000) * SR));
  for (let i = 0; i < fade; i++) s[s.length - 1 - i] *= i / fade;
  return s;
}

// --- WAV ----------------------------------------------------------------------

export function wav(sig) {
  const data = Buffer.alloc(sig.length * 2);
  for (let i = 0; i < sig.length; i++) data.writeInt16LE(Math.round(Math.max(-1, Math.min(1, sig[i])) * 32767), i * 2);
  const h = Buffer.alloc(44);
  h.write("RIFF", 0);
  h.writeUInt32LE(36 + data.length, 4);
  h.write("WAVE", 8);
  h.write("fmt ", 12);
  h.writeUInt32LE(16, 16);
  h.writeUInt16LE(1, 20);
  h.writeUInt16LE(1, 22);
  h.writeUInt32LE(SR, 24);
  h.writeUInt32LE(SR * 2, 28);
  h.writeUInt16LE(2, 32);
  h.writeUInt16LE(16, 34);
  h.write("data", 36);
  h.writeUInt32LE(data.length, 40);
  return Buffer.concat([h, data]);
}

// --- Analyse (damit Claude Sounds "sehen" kann) ---------------------------------

/** FFT (radix 2, in place). */
function fft(re, im) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      [re[i], re[j]] = [re[j], re[i]];
      [im[i], im[j]] = [im[j], im[i]];
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len;
    for (let i = 0; i < n; i += len) {
      for (let k = 0; k < len / 2; k++) {
        const wr = Math.cos(ang * k);
        const wi = Math.sin(ang * k);
        const ur = re[i + k];
        const ui = im[i + k];
        const vr = re[i + k + len / 2] * wr - im[i + k + len / 2] * wi;
        const vi = re[i + k + len / 2] * wi + im[i + k + len / 2] * wr;
        re[i + k] = ur + vr;
        im[i + k] = ui + vi;
        re[i + k + len / 2] = ur - vr;
        im[i + k + len / 2] = ui - vi;
      }
    }
  }
}

export function analyze(sig) {
  let peak = 0;
  let sum = 0;
  for (const v of sig) {
    peak = Math.max(peak, Math.abs(v));
    sum += v * v;
  }
  const rms = Math.sqrt(sum / sig.length);
  // Spektrum per FFT (Hann-Fenster 2048, bis 60 Fenster gemittelt).
  const N = 2048;
  const spec = new Float64Array(N / 2);
  const frames = Math.max(1, Math.min(60, Math.floor(sig.length / N)));
  for (let fi = 0; fi < frames; fi++) {
    const off = sig.length > N ? Math.floor((fi * (sig.length - N)) / Math.max(1, frames - 1)) : 0;
    const re = new Float64Array(N);
    const im = new Float64Array(N);
    for (let n = 0; n < N; n++) re[n] = (sig[off + n] || 0) * (0.5 - 0.5 * Math.cos((2 * Math.PI * n) / N));
    fft(re, im);
    for (let k = 0; k < N / 2; k++) spec[k] += Math.hypot(re[k], im[k]);
  }
  let num = 0;
  let den = 0;
  const bands = { sub: 0, low: 0, mid: 0, high: 0, air: 0 };
  for (let k = 1; k < N / 2; k++) {
    const hz = (k * SR) / N;
    const e = spec[k] * spec[k];
    num += spec[k] * hz;
    den += spec[k];
    if (hz < 80) bands.sub += e;
    else if (hz < 400) bands.low += e;
    else if (hz < 2500) bands.mid += e;
    else if (hz < 8000) bands.high += e;
    else bands.air += e;
  }
  const total = Object.values(bands).reduce((x, y) => x + y, 0) || 1;
  const mixPct = Object.fromEntries(Object.entries(bands).map(([k, v]) => [k, Math.round((v / total) * 100)]));
  // Anschlag: Zeit bis 90 % der Spitze.
  let attack = 0;
  for (let i = 0; i < sig.length; i++) {
    if (Math.abs(sig[i]) >= peak * 0.9) {
      attack = i / SR;
      break;
    }
  }
  const head = sig.length > SR * 0.3 ? analyzeBands(sig.slice(0, Math.round(SR * 0.25))) : null;
  return {
    headBandsPct: head,
    seconds: +(sig.length / SR).toFixed(3),
    peakDb: +(20 * Math.log10(peak || 1e-9)).toFixed(1),
    rmsDb: +(20 * Math.log10(rms || 1e-9)).toFixed(1),
    attackMs: Math.round(attack * 1000),
    brightnessHz: Math.round(num / (den || 1)),
    bandsPct: mixPct,
  };
}

/** Nur die Bänder (für den Anschlag). */
function analyzeBands(sig) {
  const r = analyze(sig);
  return r.bandsPct;
}

/** Wellenform-Bild (Hüllkurve) mehrerer Sounds untereinander, als PNG. */
export function wavePng(entries) {
  const W = 900;
  const rowH = 70;
  const H = rowH * entries.length;
  const px = Buffer.alloc(W * H * 4);
  const set = (x, y, r, g, b) => {
    if (x < 0 || y < 0 || x >= W || y >= H) return;
    const i = (y * W + x) * 4;
    px[i] = r;
    px[i + 1] = g;
    px[i + 2] = b;
    px[i + 3] = 255;
  };
  const maxLen = Math.max(...entries.map((e) => e.sig.length));
  entries.forEach((e, row) => {
    const y0 = row * rowH;
    for (let x = 0; x < W; x++) for (let y = y0; y < y0 + rowH; y++) set(x, y, row % 2 ? 22 : 30, 26, 34);
    const per = maxLen / W;
    for (let x = 0; x < W; x++) {
      const a = Math.floor(x * per);
      if (a >= e.sig.length) break;
      let m = 0;
      for (let i = a; i < Math.min(e.sig.length, a + per); i++) m = Math.max(m, Math.abs(e.sig[i]));
      const h = Math.round(m * (rowH / 2 - 4));
      const mid = y0 + rowH / 2;
      for (let y = mid - h; y <= mid + h; y++) set(x, y, 90, 200, 255);
    }
    for (let x = 0; x < W; x += Math.round(SR / per / 10)) set(x, y0 + rowH - 2, 120, 120, 120); // 0,1-s-Raster
  });
  const raw = Buffer.alloc((W * 4 + 1) * H);
  for (let y = 0; y < H; y++) px.copy(raw, y * (W * 4 + 1) + 1, y * W * 4, (y + 1) * W * 4);
  const crcT = new Int32Array(256).map((_, n) => {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c;
  });
  const crc = (b) => {
    let c = 0xffffffff;
    for (const x of b) c = crcT[(c ^ x) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  };
  const chunk = (t, d) => {
    const l = Buffer.alloc(4);
    l.writeUInt32BE(d.length);
    const td = Buffer.concat([Buffer.from(t), d]);
    const c = Buffer.alloc(4);
    c.writeUInt32BE(crc(td));
    return Buffer.concat([l, td, c]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(W, 0);
  ihdr.writeUInt32BE(H, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk("IHDR", ihdr),
    chunk("IDAT", zlib.deflateSync(raw)),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

// --- Rezepte -------------------------------------------------------------------
// Jedes Rezept: (seed) -> Float32Array. Zufall nur über seed -> Varianten.

/** Präsenz-Schicht 1-3 kHz: macht Treffer auf Handy-Lautsprechern hörbar. */
const presence = (len, seed, center = 1800, tau = 0.04) =>
  mul(filter(noise(len, "white", seed + 77), "bandpass", center, 0.9), decay(len, 0.0008, tau));

const jitter = (seed, amount) => 1 + (rng(seed * 31)() * 2 - 1) * amount;

export const RECIPES = {
  /** Leichter Schlag (M1): Knack + kurzer Wumms. */
  punch_light(seed) {
    const p = jitter(seed, 0.08);
    const click = mul(filter(noise(0.03, "white", seed), "highpass", 2500), decay(0.03, 0.001, 0.006));
    const body = mul(osc(0.18, (t) => (180 * Math.exp(-t * 30) + 70) * p), decay(0.18, 0.002, 0.045));
    const dust = mul(filter(noise(0.2, "pink", seed + 1), "lowpass", 1800), decay(0.2, 0.003, 0.05));
    return master(drive(mix(0.25, [[click, 0, 1.2], [presence(0.1, seed, 1500, 0.025), 0, 0.9], [body, 0, 1], [dust, 0, 0.35]]), 2.6));
  },

  /** Schwerer Schlag: tiefer Druck, Knochen-Knack, kurzer Raum. */
  punch_heavy(seed) {
    const p = jitter(seed, 0.07);
    const click = mul(filter(noise(0.04, "white", seed), "highpass", 1800), decay(0.04, 0.001, 0.01));
    const thump = mul(osc(0.45, (t) => (160 * Math.exp(-t * 18) + 60) * p), decay(0.45, 0.002, 0.1));
    const crunch = mul(filter(noise(0.25, "white", seed + 2), "bandpass", (t) => 1200 - t * 3000, 1.2), decay(0.25, 0.002, 0.05));
    const air = mul(filter(noise(0.5, "brown", seed + 3), "lowpass", 400), decay(0.5, 0.005, 0.15));
    const dry = drive(mix(0.6, [[click, 0, 1], [presence(0.15, seed, 1300, 0.04), 0, 1], [thump, 0, 1.2], [crunch, 0.004, 0.7], [air, 0, 0.5]]), 3.2);
    return master(reverb(dry, { size: 0.7, mixAmt: 0.18, tail: 0.5 }));
  },

  /** Schwung durch die Luft (Schwert/Arm): Rauschen, Filter fegt hoch und runter. */
  whoosh(seed) {
    const len = 0.42 * jitter(seed, 0.15);
    const peak = len * 0.45;
    const n = noise(len, "pink", seed);
    const band = filter(n, "bandpass", (t) => 500 + 2600 * Math.exp(-(((t - peak) / (len * 0.28)) ** 2)), 2.2);
    const amp = env(len, (t) => Math.exp(-(((t - peak) / (len * 0.3)) ** 2)));
    return master(mul(band, amp), { fadeMs: 60 });
  },

  /** Schnitt-Treffer: Whoosh + scharfer metallischer Biss + Zisch. */
  slash_hit(seed) {
    const sw = RECIPES.whoosh(seed);
    const bite = mul(filter(noise(0.12, "white", seed + 5), "highpass", 4000), decay(0.12, 0.0008, 0.025));
    const ring = mul(
      mix(0.5, [
        [osc(0.5, () => 2350 * jitter(seed, 0.05)), 0, 0.5],
        [osc(0.5, () => 3710 * jitter(seed, 0.05)), 0, 0.35],
        [osc(0.5, () => 5230 * jitter(seed, 0.05)), 0, 0.25],
      ]),
      decay(0.5, 0.001, 0.09),
    );
    return master(mix(0.8, [[sw, 0, 0.6], [bite, 0.17, 1], [ring, 0.17, 0.35]]));
  },

  /** Klingen prallen aufeinander: unharmonische Teiltöne + Knall. */
  sword_clash(seed) {
    const partials = [1, 2.76, 5.4, 8.93, 13.3].map((m) => m * 620 * jitter(seed, 0.04));
    const ring = mix(
      1.4,
      partials.map((f, i) => [mul(osc(1.4, () => f), decay(1.4, 0.001, 0.5 / (i + 1))), 0, 0.6 / (i + 1)]),
    );
    const hit = mul(filter(noise(0.06, "white", seed), "highpass", 2000), decay(0.06, 0.0005, 0.01));
    return master(reverb(mix(1.5, [[ring, 0, 1], [hit, 0, 1.2]]), { size: 0.9, mixAmt: 0.25, tail: 0.8 }));
  },

  /** Große Explosion: Knall + Wumms (fällt) + Grollen + Trümmer. */
  explosion(seed) {
    const crack = mul(filter(noise(0.08, "white", seed), "highpass", 1500), decay(0.08, 0.001, 0.015));
    const boom = mul(osc(1.4, (t) => 110 * Math.exp(-t * 4) + 48), decay(1.4, 0.004, 0.4));
    const rumble = mul(filter(noise(2.2, "brown", seed + 1), "lowpass", (t) => 900 * Math.exp(-t * 1.6) + 120), decay(2.2, 0.01, 0.8));
    const r = rng(seed + 9);
    const debrisLayers = [];
    for (let i = 0; i < 18; i++) {
      const d = mul(filter(noise(0.05, "white", seed + 20 + i), "bandpass", 1500 + r() * 3000, 3), decay(0.05, 0.001, 0.012));
      debrisLayers.push([d, 0.15 + r() * 1.2, 0.15 * (1 - i / 20)]);
    }
    const dry = drive(mix(2.4, [[crack, 0, 1.8], [presence(0.4, seed, 1100, 0.12), 0, 1.4], [boom, 0, 1.1], [rumble, 0, 0.8], ...debrisLayers.map(([d, t, v]) => [d, t, v * 2])]), 3);
    return master(reverb(dry, { size: 1.2, mixAmt: 0.3, tail: 1.5 }));
  },

  /** Aufladen: steigender Ton + wachsendes Rauschen (für gehaltene Fähigkeiten). */
  charge_up(seed) {
    const len = 1.6;
    const tone = mul(osc(len, (t) => 120 * 2 ** (t * 2.2), "saw"), env(len, (t) => (t / len) ** 1.5));
    const toneF = filter(tone, "lowpass", (t) => 400 + t * 3000);
    const air = mul(filter(noise(len, "pink", seed), "bandpass", (t) => 300 + t * 2500, 1.5), env(len, (t) => (t / len) ** 2));
    const shimmer = mul(osc(len, (t) => 1800 + t * 900 + 40 * Math.sin(t * 60)), env(len, (t) => 0.3 * (t / len) ** 3));
    return master(mix(len, [[toneF, 0, 0.6], [air, 0, 0.7], [shimmer, 0, 0.4]]), { fadeMs: 10 });
  },

  /** Energie-Entladung (Strahl feuern): Knall + sinkender Laser + Rauschen. */
  energy_release(seed) {
    const zap = mul(osc(0.9, (t) => 1400 * Math.exp(-t * 3) + 160, "square"), decay(0.9, 0.002, 0.3));
    const zapF = filter(zap, "lowpass", (t) => 6000 * Math.exp(-t * 2) + 400);
    const blast = mul(filter(noise(0.9, "white", seed), "lowpass", (t) => 8000 * Math.exp(-t * 3) + 300), decay(0.9, 0.002, 0.25));
    const sub = mul(osc(0.9, (t) => 70 * Math.exp(-t * 2) + 35), decay(0.9, 0.003, 0.35));
    return master(reverb(drive(mix(1, [[zapF, 0, 0.6], [blast, 0, 0.7], [sub, 0, 1]]), 2), { mixAmt: 0.22, tail: 0.9 }));
  },

  /** Teleport/Blinzeln: schneller Sog rückwärts + Pling. */
  teleport(seed) {
    const len = 0.5;
    const suck = mul(filter(noise(len, "white", seed), "bandpass", (t) => 6000 * Math.exp(-t * 7) + 300, 4), env(len, (t) => Math.sin((t / len) * Math.PI)));
    const ping = mul(osc(len, (t) => 2200 + 900 * Math.exp(-t * 20)), decay(len, 0.001, 0.08));
    return master(mix(len, [[suck, 0, 1], [ping, 0.3, 0.35]]));
  },

  /** Ketten rasseln: viele kleine metallische Klicks in Gruppen. */
  chain_rattle(seed) {
    const r = rng(seed);
    const len = 0.9;
    const layers = [];
    for (let i = 0; i < 26; i++) {
      const f = 2500 + r() * 3500;
      const click = mul(
        mix(0.08, [
          [osc(0.08, () => f), 0, 0.6],
          [osc(0.08, () => f * 1.47), 0, 0.4],
        ]),
        decay(0.08, 0.0005, 0.012 + r() * 0.01),
      );
      layers.push([click, (i / 26) * 0.7 + r() * 0.05, 0.3 + r() * 0.4]);
    }
    return master(reverb(mix(len, layers), { size: 0.6, mixAmt: 0.15, tail: 0.3 }));
  },

  /** Heiliger Glanz (Kausal/Licht): Akkord aus Glocken + Schimmern. */
  holy_shimmer(seed) {
    const len = 2.2;
    const notes = [880, 1108.7, 1318.5, 1760].map((f) => f * jitter(seed, 0.01));
    const bells = mix(
      len,
      notes.map((f, i) => [
        mul(mix(len, [[osc(len, () => f), 0, 1], [osc(len, () => f * 2.01), 0, 0.3], [osc(len, () => f * 3.02), 0, 0.12]]), decay(len, 0.004, 0.9)),
        i * 0.06,
        0.4,
      ]),
    );
    const air = mul(filter(noise(len, "white", seed), "highpass", 7000), env(len, (t) => 0.25 * Math.exp(-t * 1.5)));
    return master(reverb(mix(len, [[bells, 0, 1], [air, 0, 1]]), { size: 1.3, mixAmt: 0.4, tail: 1.6 }));
  },

  /** Dunkler Puls (Void): tiefer Wumms mit Schwebung + Sog. */
  void_pulse(seed) {
    const len = 1.4;
    const lo = mul(mix(len, [[osc(len, () => 73), 0, 1], [osc(len, () => 75.5), 0, 1]]), decay(len, 0.01, 0.45));
    const growl = mul(filter(osc(len, (t) => 82 - t * 20, "saw"), "lowpass", 500), decay(len, 0.02, 0.4));
    const suck = mul(filter(noise(len, "pink", seed), "lowpass", (t) => 300 + t * 2000), env(len, (t) => (t / len) ** 2 * 0.6));
    return master(reverb(drive(mix(len, [[lo, 0, 0.8], [growl, 0, 1.2], [presence(0.3, seed, 700, 0.1), 0, 0.8], [suck, 0, 0.8]]), 3.5), { size: 1.1, mixAmt: 0.25 }));
  },

  /** Impact-Frame-Schlag: Stille-Gefühl, dann tiefer Riesenwumms + Klingen. */
  impact_frame(seed) {
    const len = 2.5;
    const boom = mul(osc(len, (t) => 95 * Math.exp(-t * 2.5) + 50), decay(len, 0.003, 0.6));
    const crack = mul(filter(noise(0.1, "white", seed), "highpass", 1200), decay(0.1, 0.0008, 0.02));
    const ring = mul(osc(len, () => 3136 * jitter(seed, 0.02)), env(len, (t) => 0.25 * Math.exp(-t * 1.2)));
    const press = mul(filter(noise(len, "brown", seed + 1), "lowpass", 250), decay(len, 0.01, 0.9));
    return master(reverb(drive(mix(len, [[boom, 0, 1.1], [crack, 0, 1.6], [presence(0.5, seed, 1000, 0.15), 0, 1.3], [ring, 0.05, 1.4], [press, 0, 0.6]]), 3.2), { size: 1.4, mixAmt: 0.3, tail: 1.8 }));
  },

  /** UI-Klick (System-Fenster): kurzer, sauberer Blip. */
  ui_click(seed) {
    const t1 = mul(osc(0.06, () => 1600 * jitter(seed, 0.03)), decay(0.06, 0.0008, 0.012));
    const t2 = mul(osc(0.06, () => 2400), decay(0.06, 0.0008, 0.008));
    return master(mix(0.07, [[t1, 0, 1], [t2, 0, 0.4]]), { peakDb: -6, fadeMs: 5 });
  },

  /** System-Fenster öffnen: Sci-Fi-Aufschwung + zwei Töne. */
  ui_open(seed) {
    const len = 0.55;
    const sweep = mul(filter(noise(len, "white", seed), "bandpass", (t) => 800 + t * 7000, 3), env(len, (t) => Math.sin((t / len) * Math.PI) * 0.6));
    const a = mul(osc(0.2, () => 988), decay(0.2, 0.002, 0.06));
    const b = mul(osc(0.3, () => 1480), decay(0.3, 0.002, 0.09));
    return master(mix(len, [[sweep, 0, 0.6], [a, 0.18, 0.6], [b, 0.27, 0.6]]), { peakDb: -4 });
  },

  /** Level up: aufsteigendes Arpeggio mit Glanz. */
  level_up(seed) {
    const notes = [523.25, 659.25, 783.99, 1046.5];
    const layers = notes.map((f, i) => [
      mul(mix(0.6, [[osc(0.6, () => f, "tri"), 0, 1], [osc(0.6, () => f * 2), 0, 0.25]]), decay(0.6, 0.003, 0.18)),
      i * 0.09,
      0.6,
    ]);
    return master(reverb(mix(1.1, layers), { size: 1, mixAmt: 0.3, tail: 0.8 }), { peakDb: -3 });
  },

  /** Münze: zwei schnelle helle Töne. */
  coin(seed) {
    const a = mul(osc(0.1, () => 1975.5), decay(0.1, 0.001, 0.03));
    const b = mul(osc(0.35, () => 2637), decay(0.35, 0.001, 0.1));
    return master(mix(0.45, [[a, 0, 0.7], [b, 0.07, 0.7]]), { peakDb: -4 });
  },
};

// --- Ausgabe -------------------------------------------------------------------

if (process.argv[1] && process.argv[1].endsWith("synth.mjs")) {
  const only = process.argv[2] ? process.argv[2].split(",") : null;
  const variants = Number(process.env.VARIANTS || 2);
  fs.mkdirSync(OUT, { recursive: true });
  const report = [];
  const pics = [];
  for (const [name, make] of Object.entries(RECIPES)) {
    if (only && !only.includes(name)) continue;
    for (let v = 1; v <= variants; v++) {
      const sig = make(v * 101);
      fs.writeFileSync(path.join(OUT, `${name}_${v}.wav`), wav(sig));
      const a = analyze(sig);
      report.push(`${name}_${v}: ${JSON.stringify(a)}`);
      if (v === 1) pics.push({ name, sig });
    }
    console.log("ok", name);
  }
  fs.writeFileSync(path.join(OUT, "_report.txt"), report.join("\n") + "\n");
  fs.writeFileSync(path.join(OUT, "_wave.png"), wavePng(pics));
  console.log(report.join("\n"));
}
