// Regel-Simulation: viele zufällige Partien ohne Oberfläche durchspielen und prüfen, dass nichts hängen bleibt.
//   node tools/simulate.js [anzahl]
// Prüft außerdem gezielt die Waage von Deadly Sentencing und den Bonus durch Reverse Cursed Technique.
global.window = global;
require('../js/packs/jjk.js');
const Game = require('../js/game.js');
const pack = window.PACKS.jjk;
const N = Number(process.argv[2] || 400);
const assert = (c, m) => { if (!c) { console.error('FEHLER:', m); process.exitCode = 1; } };

function playRandom(mode, energy) {
  const s = Game.newGame(pack, ['A', 'B'], { mode, energy });
  Game.startAuction(s);
  let guard = 0;
  while (s.phase !== 'result' && guard++ < 5000) {
    if (s.phase === 'intermission') { Game.startStage(s); continue; }
    if (s.phase === 'auction') {
      const c = s.current;
      const p = c.turn;
      const pl = s.players[p];
      if (c.highBidder !== null && Math.random() < 0.45) Game.act(s, p, { type: 'pass' });
      else if (Game.canOverbid(s, p) || c.highBidder === null) {
        const amt = Math.min(pl.budget, c.highBid + 1 + Math.floor(Math.random() * 3));
        if (Game.act(s, p, { type: 'bid', amount: amt })) Game.act(s, p, { type: 'pass' });
      } else Game.act(s, p, { type: 'pass' });
      continue;
    }
    if (s.phase === 'final') {
      [0, 1].forEach((p) => {
        const pl = s.players[p];
        if (pl.ready) return;
        const allowed = Game.equipAllowed(s, p);
        Game.act(s, p, { type: 'final', sacrifice: null, target: null, equipUse: pl.equip.slice(0, allowed) });
      });
      continue;
    }
    if (s.phase === 'seal') {
      const sl = s.seal;
      if (!sl.options) Game.act(s, sl.target, { type: 'sealOptions', ids: Game.liveAbilities(s, sl.target).slice(0, 2) });
      else Game.act(s, sl.by, { type: 'seal', id: sl.options[0] });
      continue;
    }
    if (s.phase === 'ritual') {
      const R = s.ritual;
      if (!R.decided) Game.act(s, R.player, { type: 'ritual', summon: Math.random() < 0.6 });
      else Game.act(s, R.player, { type: 'ritualDone' });
      continue;
    }
    if (s.phase === 'gamble') {
      const G = s.gamble;
      if (G.done) Game.act(s, G.player, { type: 'gambleDone' });
      else Game.act(s, G.player, { type: Math.random() < 0.75 ? 'spin' : 'stopSpin' });
      continue;
    }
    if (s.phase === 'feast') {
      const Fe = s.feast;
      if (!Fe.fingers) Game.act(s, Fe.player, { type: 'feastSpin' });
      else Game.act(s, 1 - Fe.player, { type: 'feastDone' });
      continue;
    }
    if (s.phase === 'resonance') { Game.act(s, 0, { type: 'resonanceDone' }); continue; }
    if (s.phase === 'verdict') {
      const V = s.verdict;
      if (V.needSeal && !V.sealed) Game.act(s, V.judge, { type: 'verdictSeal', id: V.options[0] });
      else Game.act(s, V.accused, { type: 'verdictDone' });
      continue;
    }
    if (s.phase === 'clash') {
      const c = s.clash;
      if (c.done) { Game.act(s, 0, { type: 'clashDone' }); continue; }
      [0, 1].forEach((p) => { if (c.hits[p].length < c.rounds) Game.act(s, p, { type: 'clashHit', round: c.hits[p].length, offset: Math.random() * 0.3 }); });
      continue;
    }
    throw new Error('Unbekannte Phase ' + s.phase);
  }
  assert(s.phase === 'result', 'Partie hängt in Phase ' + s.phase);
  assert(s.result.scores.every((r) => Number.isFinite(r.total)), 'Punkte sind keine Zahl');
  return s;
}

// 1) Zufallspartien in allen Modi
const stats = { verdict: 0, levels: {}, jackpot: 0, spins: 0 };
for (let i = 0; i < N; i++) {
  const s = playRandom(['classic', 'equipment'][i % 2], i % 3 === 0);
  if (s.verdict) { stats.verdict++; stats.levels[s.verdict.level] = (stats.levels[s.verdict.level] || 0) + 1; }
  if (s.gamble) { stats.spins += s.gamble.spins.length; stats.jackpot += s.gamble.spins.filter((x) => x === 'jackpot').length; }
}
console.log(`${N} Partien ok. Urteile: ${stats.verdict}`, JSON.stringify(stats.levels),
  `Jackpot-Quote: ${stats.spins ? (100 * stats.jackpot / stats.spins).toFixed(1) : '-'} % von ${stats.spins} Spins`);

// 2) Gezielte Prüfung der Waage: Richter (Higuruma) gegen ein sehr böses und ein sehr gutes Team
function rig(judgeIds, accusedIds, opts = {}) {
  const s = Game.newGame(pack, ['Richter', 'Angeklagter'], { mode: opts.equip ? 'equipment' : 'classic' });
  s.players[0].slots = judgeIds;
  s.players[1].slots = accusedIds;
  s.players[0].equip = opts.equip || [];
  s.players[0].choice = { sacrifice: null, target: null, equipUse: opts.equip || [] };
  s.players[1].choice = { sacrifice: null, target: null, equipUse: [] };
  s.players.forEach((pl) => { pl.ready = true; });
  // direkt zur Waage springen (Prison Realm, Ritual, Automat gibt es hier nicht)
  s.phase = 'gamble';
  s.gamble = { player: 0, spinsLeft: 0, total: 0, spins: [], last: null, done: true, outcome: null };
  Game.act(s, 0, { type: 'gambleDone' });
  s.gamble = null;
  return s;
}
const evil = ['boeser-schrein', 'zerlegen-spalten', 'feuerpfeil', 'verwandlung', 'fluchmanipulation'];   // Karma 23
const good = ['schwarzer-blitz', 'divergente-faust', 'ratio', 'fluchsprache', 'authentische-liebe'];    // Karma -15
const judge = ['todesurteil', 'schwarzer-blitz', 'ratio', 'gojo-nahkampf', 'panda'];

let s = rig(judge, evil, { equip: ['henkersschwert'] });
assert(s.verdict && s.verdict.level === 3 && s.verdict.sword, 'Todesurteil mit Schwert erwartet');
Game.act(s, 1, { type: 'verdictDone' });
assert(s.phase === 'result', 'Mit Schwert: Clash muss übersprungen werden');
assert(s.clash && s.clash.winner === 0 && s.clash.execution, 'Richter gewinnt den Clash ohne Kampf');
const half = s.result.scores[1].lines.find((l) => l.label.includes('halbiert'));
assert(half && half.points < 0, 'Gesamtpunkte des Angeklagten halbiert');
console.log('Todesurteil mit Schwert: Angeklagter', s.result.scores[1].total, 'Richter', s.result.scores[0].total);

s = rig(judge, evil);
assert(s.verdict.level === 3 && !s.verdict.sword && s.verdict.needSeal, 'Todesurteil ohne Schwert → versiegeln');
assert(!s.verdict.options.includes('boeser-schrein'), 'Domains dürfen nicht versiegelt werden');
assert(Game.act(s, 1, { type: 'verdictDone' }), 'Weiter erst nach dem Versiegeln');
Game.act(s, 0, { type: 'verdictSeal', id: 'zerlegen-spalten' });
Game.act(s, 1, { type: 'verdictDone' });
assert(s.phase === 'clash', 'Beide haben eine Domain → Clash');
assert(s.clash.flashPts[0] > s.clash.flashPts[1] || s.clash.flashPts[0] === 34, 'Richter hat stärkeren Black Flash');
assert(!Game.countingAbilities(s, 1).includes('zerlegen-spalten'), 'Versiegelte Karte zählt nicht mehr');
console.log('Todesurteil ohne Schwert: Black Flash', s.clash.flashPts, 'versiegelt:', s.verdict.sealed);

s = rig(judge, good);
assert(s.verdict.level <= -3, 'Sehr gutes Team → Waage maximal für den Angeklagten (Stufe ' + s.verdict.level + ')');
Game.act(s, 1, { type: 'verdictDone' });
[0, 1].forEach((p) => { for (let r = 0; r < 5; r++) Game.act(s, p, { type: 'clashHit', round: r, offset: p === 0 ? 0 : 0.9 }); });
Game.act(s, 0, { type: 'clashDone' });
const sc1 = s.result.scores[1];
const dl = sc1.lines.find((l) => l.label.includes('doppelt so viel'));
assert(dl, 'Guter Angeklagter: Domain zählt doppelt so viel wie die des Richters');
console.log('Reines Gewissen: Angeklagter', sc1.total, 'Richter', s.result.scores[0].total, '(Clash vom Richter gewonnen)');

// 3) Reverse Cursed Technique: Reversal Red ohne Schwäche und verstärkt
const withR = Game.score(pack, { abilities: ['rot', 'umgekehrte-technik'], equip: [] }, { abilities: [], equip: [] });
const without = Game.score(pack, { abilities: ['rot', 'blau'], equip: [] }, { abilities: [], equip: [] });
assert(withR.lines.some((l) => l.label.includes('verstärkt Reversal Red')), 'RCT verstärkt Red');
console.log('RCT: Red mit RCT', withR.base, 'Punkte Grundwert (Red+RCT), ohne RCT (Red+Blue)', without.base);
// 4) Sukunas Finger: Glücksrad 1–3, Sukuna-Techniken stärker
function rig2(a, b, equipA, equipB) {
  const s = Game.newGame(pack, ['A', 'B'], { mode: 'equipment' });
  s.players[0].slots = a; s.players[1].slots = b;
  s.players[0].equip = equipA; s.players[1].equip = equipB;
  s.players[0].choice = { sacrifice: null, target: null, equipUse: equipA };
  s.players[1].choice = { sacrifice: null, target: null, equipUse: equipB };
  s.players.forEach((pl) => { pl.ready = true; });
  s.phase = 'gamble';
  s.gamble = { player: 0, spinsLeft: 0, total: 0, spins: [], last: null, done: true, outcome: null };
  Game.act(s, 0, { type: 'gambleDone' });
  s.gamble = null;
  return s;
}
const suk = ['boeser-schrein', 'zerlegen-spalten', 'feuerpfeil', 'panda', 'ratio'];
const counts = { 1: 0, 2: 0, 3: 0 };
let gain = 0;
for (let i = 0; i < 300; i++) {
  const t = rig2(suk, ['schwarzer-blitz', 'panda', 'blau', 'kopie', 'batto'], ['sukuna-finger', 'kette'], ['kette', 'revolver']);
  assert(t.phase === 'feast', 'Finger-Mahl erwartet, Phase ' + t.phase);
  assert(Game.act(t, 0, { type: 'feastDone' }), 'Weiter erst nach dem Drehen');
  Game.act(t, 0, { type: 'feastSpin' });
  counts[t.feast.fingers]++;
  Game.act(t, 1, { type: 'feastDone' });
  assert(t.phase === 'result', 'Danach Auswertung (keine Waage, kein Clash) – ist ' + t.phase);
  gain += t.result.scores[0].lines.filter((l) => l.label.includes('Sukuna isst')).length;
}
assert(gain === 300, 'Finger-Zeile in jeder Auswertung');
console.log('Glücksrad (300×):', JSON.stringify(counts));
// 5) Nobaras Resonanz halbiert die Sukuna-Techniken des Gegners
let r = rig2(['strohpuppe', 'panda', 'ratio', 'batto', 'blau'], suk, ['hammer-naegel', 'sukuna-finger'], ['kette', 'revolver']);
assert(r.phase === 'resonance', 'Resonanz erwartet, Phase ' + r.phase);
Game.act(r, 1, { type: 'resonanceDone' });
const vic = r.result.scores[1];
assert(vic.lines.some((l) => l.label.includes('Resonanz')), 'Resonanz-Zeile beim Opfer');
const noRes = Game.score(pack, { abilities: suk, equip: ['kette', 'revolver'] }, { abilities: [], equip: [] });
console.log('Resonanz: Sukuna-Team', vic.base, 'statt', noRes.base, '(Grundwert)');
// 6) Fluchkraft-Modus: alle haben am Ende Fluchkraft
let missing = 0;
for (let i = 0; i < 100; i++) { const t = playRandom('classic', true); missing += t.players.filter((pl) => !pl.energy.length).length; }
assert(missing === 0, missing + ' Spieler ohne Fluchkraft');
console.log('Fluchkraft: jeder Spieler hat am Ende welche (100 Partien).');
console.log(process.exitCode ? 'TESTS FEHLGESCHLAGEN' : 'Alle Tests bestanden.');
