// Spielregeln – reine Logik ohne Anzeige.
// Der Host (Raum-Ersteller) rechnet den Spielstand, der Gast bekommt ihn geschickt.
//
// Ablauf: coin → auction (Fähigkeiten)
//         → [intermission → auction (Ausrüstung)]      Modus „Mit Ausrüstung“
//         → [intermission → auction (Fluchkraft)]      Zusatzmodus „Fluchkraft-Runde“
//         → [final]  Binding Vow / Ausrüstung wählen
//         → [seal]   Prison Realm: Gegner schlägt 2 Fähigkeiten vor, Besitzer versiegelt eine
//         → [ritual] Mahoraga ohne Ten Shadows: beschwören (Kampf) oder nicht (halbe Punkte)
//         → [gamble] Idle Death Gamble: der Besitzer dreht bis zu 3× (+2 mit Rough Energy) am Automaten
//         → [clash]  Domain Clash: haben beide eine Domain, entscheidet ein Timing-Duell (5 Runden)
//         → result

(function (root) {
  const BUDGET = 20;
  const SLOTS = 5;
  const getPack = (s) => (root.PACKS || {})[s.packId];

  function shuffle(arr, rnd) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  const freshTokens = () => ({ skip: 1, peek: 1, endskip: 1 });
  const KIND_OF_STAGE = { abilities: 'ability', equipment: 'equip', energy: 'energy' };

  function newGame(pack, names, settings, rnd) {
    rnd = rnd || Math.random;
    settings = settings || {};
    const mode = settings.mode === 'equipment' ? 'equipment' : 'classic';
    const energyMode = !!settings.energy && (pack.energy || []).length > 0;
    const kinds = {}, names_ = {}, users = {};
    pack.abilities.forEach((a) => { kinds[a.id] = 'ability'; });
    (pack.vows || []).forEach((v) => { kinds[v.id] = 'vow'; });
    (pack.equipment || []).forEach((e) => { kinds[e.id] = e.type === 'storage' ? 'storage' : 'equip'; });
    (pack.energy || []).forEach((e) => { kinds[e.id] = 'energy'; });
    [...pack.abilities, ...(pack.vows || []), ...(pack.equipment || []), ...(pack.energy || [])]
      .forEach((x) => { names_[x.id] = x.name; users[x.id] = x.user; });
    const stages = ['abilities'].concat(mode === 'equipment' ? ['equipment'] : []).concat(energyMode ? ['energy'] : []);
    return {
      phase: 'coin',
      packId: pack.id,
      mode,
      energyMode,
      stages,
      stageIdx: 0,
      stage: 'abilities',
      limits: { abilities: SLOTS, equipment: pack.equipSlots || 3, energy: pack.energySlots || 1 },
      equipUse: pack.equipUse || 2,
      players: names.map((name) => ({
        name, budget: BUDGET, slots: [], paid: {}, filled: [],
        vow: null, storage: null, equip: [], equipFilled: [], energy: [], leftover: null,
        tokens: freshTokens(), choice: null, ready: false,
      })),
      deck: shuffle(pack.abilities.map((a) => a.id).concat((pack.vows || []).map((v) => v.id)), rnd),
      graveyard: [],
      kinds,
      names: names_,
      users,
      domainIds: pack.abilities.filter((a) => a.type === 'domain').map((a) => a.id),
      lockedNext: null, // beim Spicken festgelegte nächste Karte
      coin: rnd() < 0.5 ? 0 : 1,
      nextStarter: null,
      round: 0,
      current: null,
      peek: null,       // { id, seen:[bool,bool], votes:[bool,bool], accepted }
      skipNext: null,   // per Sneak Peek beschlossen: diese Karte wird beim Ziehen übersprungen
      seal: null,       // { by, target, options:[id,id]|null, sealed:id|null }
      gamble: null,     // { player, spinsLeft, total, spins:[...], last, done, outcome }
      ritual: null,     // Mahoraga-Beschwörung: { player, chance, decided, summon, success, done }
      clash: null,      // Domain Clash: { domains, zone, perfect, flashPts, hitMult, hits:[[],[]], points, done, winner }
      events: [],       // für Meldungen in der Anzeige
      evSeq: 0,
      log: [],
      result: null,
    };
  }

  const other = (p) => 1 - p;

  function stageSlots(s, p) {
    const pl = s.players[p];
    return s.stage === 'abilities' ? pl.slots : s.stage === 'equipment' ? pl.equip : pl.energy;
  }
  function limit(s) { return s.limits[s.stage]; }

  // Kann der Spieler in dieser Runde noch etwas kaufen?
  function isActive(s, p) {
    return stageSlots(s, p).length < limit(s) && s.players[p].budget >= 1;
  }
  // Kann er auf die aktuelle Karte bieten? (Spezialkarten haben eigene Slots)
  function canBid(s, p, id) {
    id = id || (s.current && s.current.id);
    if (s.kinds[id] === 'vow') return s.players[p].budget >= 1 && !s.players[p].vow;
    if (s.kinds[id] === 'storage') return s.players[p].budget >= 1 && !s.players[p].storage;
    if (isDomain(s, id) && hasDomain(s, p)) return false;
    return isActive(s, p);
  }
  const isDomain = (s, id) => (s.domainIds || []).includes(id);
  const hasDomain = (s, p) => s.players[p].slots.some((id) => isDomain(s, id));
  const isSpecial = (s, id) => s.kinds[id] === 'vow' || s.kinds[id] === 'storage';

  // ───────── Set-Chancen ─────────
  // Pro Spieler wird genau EIN Set (= Charakter) bevorzugt: von den Charakteren, von denen er
  // Karten besitzt, das mit den meisten noch nicht aufgetauchten Karten im Stapel.
  // Je mehr Karten er davon hat, desto öfter kommen weitere – besitzen beide dasselbe Set, addiert es sich.
  const SET_BOOST = 0.45; // +45 % Chance pro besessener Karte des Sets

  function setBoosts(s) {
    return s.players.map((pl) => {
      const owned = {};
      pl.slots.concat(pl.equip).forEach((id) => { const u = s.users[id]; owned[u] = (owned[u] || 0) + 1; });
      let best = null;
      for (const [u, n] of Object.entries(owned)) {
        const left = s.deck.filter((id) => s.users[id] === u && !isSpecial(s, id)).length;
        if (!left) continue;
        if (!best || left > best.left || (left === best.left && n > best.owned)) best = { user: u, owned: n, left };
      }
      return best;
    });
  }

  function drawWeighted(s) {
    const boosts = setBoosts(s);
    const weights = s.deck.map((id) => {
      let w = 1;
      boosts.forEach((b) => { if (b && s.users[id] === b.user && !isSpecial(s, id)) w += SET_BOOST * b.owned; });
      return w;
    });
    let r = Math.random() * weights.reduce((a, b) => a + b, 0);
    for (let i = 0; i < s.deck.length; i++) { r -= weights[i]; if (r <= 0) return s.deck[i]; }
    return s.deck[s.deck.length - 1];
  }

  // Nächste Karte bestimmen (beim Spicken wird sie vorab festgelegt)
  function peekNext(s) {
    if (!s.lockedNext || !s.deck.includes(s.lockedNext)) s.lockedNext = s.deck.length ? drawWeighted(s) : null;
    return s.lockedNext;
  }
  function canOverbid(s, p) {
    return canBid(s, p) && s.players[p].budget > s.current.highBid;
  }
  // Einer kann nicht mehr kaufen, der andere schon → Final Skip erlaubt
  function soloPhase(s) {
    return isActive(s, 0) !== isActive(s, 1);
  }

  // Normaler Skip: nur wenn man dran ist, und nur solange das Gebot höchstens SKIP_MAX_BID € beträgt
  const SKIP_MAX_BID = 5;
  function skipBlocked(s, p) {
    const c = s.current;
    if (!c || c.turn !== p) return 'Skippen geht nur, wenn du dran bist.';
    if (c.highBidder !== null && c.highBid > SKIP_MAX_BID) return `Das Gebot liegt über ${SKIP_MAX_BID} € – jetzt kann nicht mehr geskippt werden.`;
    return null;
  }

  function log(s, text) {
    s.log.push(text);
    if (s.log.length > 40) s.log.shift();
  }
  function event(s, e) {
    e.n = ++s.evSeq;
    s.events.push(e);
    if (s.events.length > 8) s.events.shift();
  }

  function startAuction(s) {
    s.phase = 'auction';
    s.nextStarter = s.coin;
    log(s, `Münzwurf: ${s.players[s.coin].name} beginnt.`);
    nextItem(s);
  }

  // Nach der Pause: nächste Runde (Ausrüstung / Fluchkraft) starten
  function startStage(s) {
    s.phase = 'auction';
    nextItem(s);
  }

  function nextItem(s) {
    s.current = null;
    s.peek = null;
    for (;;) {
      if ((!isActive(s, 0) && !isActive(s, 1)) || s.deck.length === 0) return endStage(s);
      const id = peekNext(s);
      s.lockedNext = null;
      s.deck.splice(s.deck.indexOf(id), 1);
      if (s.skipNext === id) {
        s.skipNext = null;
        s.graveyard.push(id);
        log(s, `„${s.names[id]}“ wurde nach dem Sneak Peek übersprungen.`);
        event(s, { kind: 'peekskip', id });
        continue;
      }
      // Spezialkarte, die keiner kaufen kann → weg damit
      if (!canBid(s, 0, id) && !canBid(s, 1, id)) {
        s.graveyard.push(id);
        if (isDomain(s, id)) log(s, `„${s.names[id]}“ fällt weg – beide haben schon eine Domain.`);
        continue;
      }
      s.skipNext = null;
      let starter = s.nextStarter;
      s.nextStarter = other(starter);
      if (!canBid(s, starter, id)) starter = other(starter);
      s.round++;
      s.current = { id, starter, turn: starter, highBid: 0, highBidder: null, bids: [] };
      return;
    }
  }

  function award(s, p) {
    const c = s.current;
    const pl = s.players[p];
    pl.budget -= c.highBid;
    pl.paid[c.id] = c.highBid;
    if (s.kinds[c.id] === 'vow') pl.vow = c.id;
    else if (s.kinds[c.id] === 'storage') pl.storage = c.id;
    else stageSlots(s, p).push(c.id);
    event(s, { kind: 'won', player: p, id: c.id, price: c.highBid });
    log(s, `${pl.name} bekommt „${s.names[c.id]}“ für ${c.highBid} €.`);
    nextItem(s);
  }

  function discard(s, p, how) {
    const c = s.current;
    s.graveyard.push(c.id);
    event(s, { kind: how, player: p, id: c.id });
    log(s, `${s.players[p].name} überspringt „${s.names[c.id]}“${how === 'endskip' ? ' (Final Skip)' : ''}.`);
    nextItem(s);
  }

  function advanceTurn(s) {
    const c = s.current;
    if (c.highBidder !== null && c.turn !== c.highBidder && !canOverbid(s, c.turn)) award(s, c.highBidder);
  }

  // Leere Slots der aktuellen Runde zufällig füllen (Fluchkraft wird NICHT verschenkt – nur wer kauft, hat welche)
  function fillRandom(s, rnd) {
    if (s.stage === 'energy') return;
    rnd = rnd || Math.random;
    const want = KIND_OF_STAGE[s.stage];
    const pool = shuffle(s.deck, rnd).concat(shuffle(s.graveyard, rnd)).filter((id) => s.kinds[id] === want);
    s.players.forEach((pl, p) => {
      const slots = stageSlots(s, p);
      const filled = s.stage === 'abilities' ? pl.filled : pl.equipFilled;
      while (slots.length < limit(s) && pool.length) {
        const idx = pool.findIndex((id) => !(isDomain(s, id) && hasDomain(s, p)));
        if (idx < 0) break;
        const id = pool.splice(idx, 1)[0];
        slots.push(id);
        filled.push(id);
      }
    });
  }

  function endStage(s) {
    s.current = null;
    s.peek = null;
    s.skipNext = null;
    s.lockedNext = null;
    fillRandom(s);
    const next = s.stages[s.stageIdx + 1];
    if (next) {
      const pack = getPack(s);
      s.stageIdx++;
      s.stage = next;
      s.phase = 'intermission';
      log(s, next === 'equipment' ? 'Fähigkeiten-Runde vorbei – jetzt kommt die Ausrüstung!' : 'Jetzt wird um Fluchkraft geboten!');
      s.players.forEach((pl) => {
        pl.leftover = pl.budget;
        if (next === 'equipment') pl.budget = pl.budget * 2; // Restgeld verdoppelt – Fluchkraft wird mit dem Rest bezahlt
        pl.tokens = freshTokens();
      });
      const cards = next === 'equipment' ? pack.equipment : pack.energy;
      s.deck = shuffle((cards || []).map((e) => e.id), Math.random);
      s.graveyard = [];
      return;
    }
    log(s, 'Versteigerung vorbei.');
    toFinal(s);
  }

  // Wie viele Ausrüstungen darf der Spieler benutzen? (Inventory Curse = alle)
  function equipAllowed(s, p) {
    const pl = s.players[p];
    return pl.storage ? pl.equip.length : Math.min(s.equipUse, pl.equip.length);
  }

  function needsChoice(s, p) {
    return !!s.players[p].vow || (s.mode === 'equipment' && s.players[p].equip.length > equipAllowed(s, p));
  }

  function toFinal(s) {
    s.players.forEach((pl, p) => {
      pl.ready = !needsChoice(s, p);
      if (pl.ready) pl.choice = { sacrifice: null, target: null, equipUse: pl.equip.slice(0, equipAllowed(s, p)) };
    });
    if (s.players.every((pl) => pl.ready)) return afterChoices(s);
    s.phase = 'final';
  }

  // Fähigkeiten, die noch im Spiel sind (nicht geopfert)
  function liveAbilities(s, p) {
    const ch = s.players[p].choice || {};
    return s.players[p].slots.filter((id) => id !== ch.sacrifice);
  }

  // Nach der Auswahl: Prison Realm versiegelt eine gegnerische Fähigkeit
  function afterChoices(s) {
    const pack = getPack(s);
    const sealers = (pack.equipment || []).filter((e) => e.seal).map((e) => e.id);
    const by = [0, 1].find((p) => ((s.players[p].choice || {}).equipUse || []).some((id) => sealers.includes(id)));
    if (by !== undefined) {
      const target = other(by);
      const cand = liveAbilities(s, target);
      if (cand.length >= 2) {
        s.seal = { by, target, options: null, sealed: null };
        s.phase = 'seal';
        log(s, `${s.players[by].name} benutzt Prison Realm!`);
        event(s, { kind: 'sealstart', player: by });
        return;
      }
      if (cand.length === 1) s.seal = { by, target, options: cand, sealed: cand[0] };
    }
    afterSeal(s);
  }

  // Fähigkeiten, die wirklich zählen (nicht geopfert, nicht versiegelt)
  function countingAbilities(s, p) {
    const sealed = s.seal && s.seal.target === p ? s.seal.sealed : null;
    return liveAbilities(s, p).filter((id) => id !== sealed);
  }

  // ───────── Mahoraga-Ritual ─────────
  const RITUAL = { id: 'mahoraga', without: 'zehn-schatten', loseNerf: 0.15 };

  function ritualChance(s, p) {
    // Nur die Grundwerte der eigenen anderen Fähigkeiten zählen – keine Effekte, keine Nerfs
    const pack = getPack(s);
    const sum = countingAbilities(s, p).filter((id) => id !== RITUAL.id)
      .reduce((t, id) => t + pack.abilities.find((a) => a.id === id).value, 0);
    return Math.round(Math.max(0.1, Math.min(0.9, (sum - 120) / 240)) * 100) / 100;
  }

  function afterSeal(s) {
    const owner = [0, 1].find((p) => countingAbilities(s, p).includes(RITUAL.id) && !countingAbilities(s, p).includes(RITUAL.without));
    if (owner !== undefined) {
      s.ritual = { player: owner, chance: ritualChance(s, owner), decided: false, summon: null, success: null, done: false };
      s.phase = 'ritual';
      log(s, `${s.players[owner].name} steht vor der Wahl: Mahoraga beschwören?`);
      event(s, { kind: 'ritualstart', player: owner });
      return;
    }
    startGamble(s);
  }

  // Wer „Idle Death Gamble“ hat, darf am Automaten drehen
  function startGamble(s) {
    const g = (getPack(s).effects || []).find((e) => e.type === 'gamble');
    const owner = g ? [0, 1].find((p) => countingAbilities(s, p).includes(g.id)) : undefined;
    if (owner === undefined) return afterGamble(s);
    const extra = countingAbilities(s, owner).includes(g.extraSpinsFrom) ? g.extraSpins : 0;
    s.gamble = { player: owner, spinsLeft: g.spins + extra, total: g.spins + extra, spins: [], last: null, done: false, outcome: null };
    s.phase = 'gamble';
    log(s, `${s.players[owner].name} tritt an den Automaten von Idle Death Gamble!`);
    event(s, { kind: 'gamblestart', player: owner });
  }

  // ───────── Domain Clash ─────────
  const CLASH_ROUNDS = 5;

  function clashSetup(s, p) {
    const pack = getPack(s);
    const byId = Object.fromEntries(pack.abilities.map((a) => [a.id, a]));
    const ids = countingAbilities(s, p);
    const energy = s.players[p].energy[0] ? (pack.energy || []).find((e) => e.id === s.players[p].energy[0]) : null;
    const doms = ids.map((id) => byId[id]).filter((a) => a.type === 'domain');
    if (!doms.length) return null;
    const dom = doms.reduce((b, a) => (baseValue(pack, a, ids, energy).v > baseValue(pack, b, ids, energy).v ? a : b));
    // Wie gut passt das Team zur Domain? Gleicher Charakter oder gemeinsame Klasse
    const fit = ids.filter((id) => id !== dom.id).map((id) => byId[id])
      .filter((a) => a.user === dom.user || a.tags.some((t) => dom.tags.includes(t))).length;
    const power = baseValue(pack, dom, ids, energy).v + fit * 8;
    const zone = Math.max(0.12, Math.min(0.34, 0.08 + power / 100 * 0.2));
    const hasBF = ids.includes('schwarzer-blitz');
    return { domain: dom.id, zone, perfect: zone * (hasBF ? 0.32 : 0.22), flashPts: hasBF ? 34 : 26, blackFlash: hasBF, fit };
  }

  function afterGamble(s) {
    const setups = [clashSetup(s, 0), clashSetup(s, 1)];
    if (!setups[0] || !setups[1]) return finishResult(s);
    const counterIds = ['einfacher-bereich', 'weidenkorb'];
    // Hat der Gegner Simple Domain / Hollow Wicker Basket, zählen meine Treffer weniger
    const guarded = [0, 1].map((p) => countingAbilities(s, p).some((id) => counterIds.includes(id)));
    s.clash = {
      rounds: CLASH_ROUNDS,
      domains: setups.map((x) => x.domain),
      zone: setups.map((x) => x.zone),
      perfect: setups.map((x) => x.perfect),
      flashPts: setups.map((x) => x.flashPts),
      blackFlash: setups.map((x) => x.blackFlash),
      fit: setups.map((x) => x.fit),
      guarded,
      hitMult: [guarded[1] ? 0.75 : 1, guarded[0] ? 0.75 : 1],
      hits: [[], []],
      points: [0, 0],
      done: false,
      winner: null,
    };
    s.phase = 'clash';
    log(s, `DOMAIN CLASH: „${s.names[setups[0].domain]}“ gegen „${s.names[setups[1].domain]}“!`);
    event(s, { kind: 'clashstart' });
  }

  function clashHit(s, p, offset) {
    const c = s.clash;
    const half = c.zone[p] / 2;
    let kind, pts;
    if (offset <= c.perfect[p] / 2) { kind = 'flash'; pts = c.flashPts[p]; }
    else if (offset <= half) { kind = 'hit'; pts = 16 - 6 * (offset / half); }
    else { kind = 'miss'; pts = 0; }
    pts = Math.round(pts * c.hitMult[p]);
    c.hits[p].push({ kind, pts });
    c.points[p] += pts;
    if (c.hits[0].length >= c.rounds && c.hits[1].length >= c.rounds) {
      c.done = true;
      if (c.points[0] !== c.points[1]) c.winner = c.points[0] > c.points[1] ? 0 : 1;
      else c.winner = c.zone[0] >= c.zone[1] ? 0 : 1; // Gleichstand: stärkere Domain gewinnt
      log(s, `${s.players[c.winner].name} gewinnt den Domain Clash!`);
      event(s, { kind: 'clashwin', player: c.winner });
    }
  }

  function spinOnce(s, g) {
    const ch = g.chances;
    const boost = g.energyBoost && s.players[s.gamble.player].energy[0] === g.energyBoost.id ? g.energyBoost.jackpot : 0;
    const r = Math.random();
    if (r < ch.jackpot + boost) return 'jackpot';
    if (r < ch.jackpot + boost + ch.reach) return 'reach';
    if (r < ch.jackpot + boost + ch.reach + ch.fever) return 'fever';
    return 'miss';
  }

  function finishResult(s) {
    s.phase = 'result';
    log(s, 'Auswertung!');
    computeResult(s, getPack(s));
  }

  // Aktionen:
  //  { type: 'bid', amount } | { type: 'pass' }
  //  { type: 'skip' } | { type: 'endskip' } | { type: 'peek' } | { type: 'peekvote' }
  //  { type: 'final', sacrifice, target, equipUse: [ids] }
  //  { type: 'sealOptions', ids: [id, id] }  (Gegner des Prison-Realm-Besitzers)
  //  { type: 'seal', id }                    (Prison-Realm-Besitzer)
  // Rückgabe: Fehlertext oder null
  function act(s, p, a) {
    const pl = s.players[p];

    if (a.type === 'final') {
      if (s.phase !== 'final') return 'Gerade gibt es nichts auszuwählen.';
      if (pl.ready) return 'Du hast schon gewählt.';
      let sacrifice = null, target = null;
      if (pl.vow && a.sacrifice) {
        if (!pl.slots.includes(a.sacrifice) || !pl.slots.includes(a.target) || a.sacrifice === a.target)
          return 'Wähle eine Fähigkeit zum Opfern und eine andere zum Verstärken.';
        sacrifice = a.sacrifice; target = a.target;
      }
      const allowed = equipAllowed(s, p);
      let equipUse = pl.equip.slice(0, allowed);
      if (s.mode === 'equipment' && pl.equip.length > allowed) {
        const pick = Array.isArray(a.equipUse) ? [...new Set(a.equipUse)] : [];
        if (pick.length !== allowed || !pick.every((id) => pl.equip.includes(id)))
          return `Wähle genau ${allowed} Ausrüstungen aus.`;
        equipUse = pick;
      }
      pl.choice = { sacrifice, target, equipUse };
      pl.ready = true;
      log(s, `${pl.name} ist bereit.`);
      if (s.players.every((x) => x.ready)) afterChoices(s);
      return null;
    }

    if (a.type === 'sealOptions') {
      if (s.phase !== 'seal' || !s.seal || s.seal.options) return 'Gerade gibt es nichts vorzuschlagen.';
      if (p !== s.seal.target) return 'Dein Gegner muss die Fähigkeiten vorschlagen.';
      const ids = Array.isArray(a.ids) ? [...new Set(a.ids)] : [];
      const cand = liveAbilities(s, p);
      if (ids.length !== 2 || !ids.every((id) => cand.includes(id))) return 'Wähle genau 2 deiner Fähigkeiten.';
      s.seal.options = ids;
      log(s, `${pl.name} schlägt 2 Fähigkeiten zum Versiegeln vor.`);
      return null;
    }

    if (a.type === 'seal') {
      if (s.phase !== 'seal' || !s.seal || !s.seal.options) return 'Noch gibt es keine Vorschläge.';
      if (p !== s.seal.by) return 'Nur der Besitzer von Prison Realm darf versiegeln.';
      if (!s.seal.options.includes(a.id)) return 'Wähle eine der beiden vorgeschlagenen Fähigkeiten.';
      s.seal.sealed = a.id;
      log(s, `„${s.names[a.id]}“ wurde im Prison Realm versiegelt!`);
      event(s, { kind: 'sealed', player: p, id: a.id });
      afterSeal(s);
      return null;
    }

    if (a.type === 'ritual' || a.type === 'ritualDone') {
      const R = s.ritual;
      if (s.phase !== 'ritual' || !R) return 'Gerade gibt es keine Beschwörung.';
      if (a.type === 'ritualDone') { if (!R.decided) return 'Erst entscheiden.'; R.done = true; startGamble(s); return null; }
      if (p !== R.player) return 'Nur der Besitzer von Mahoraga entscheidet.';
      if (R.decided) return 'Schon entschieden.';
      R.decided = true;
      R.summon = !!a.summon;
      if (!R.summon) {
        log(s, `${pl.name} beschwört Mahoraga nicht – er zählt nur halb.`);
        R.done = true;
        startGamble(s);
        return null;
      }
      R.success = Math.random() < R.chance;
      log(s, R.success ? `${pl.name} bezwingt Mahoraga!` : `Mahoraga schlägt ${pl.name} weg!`);
      event(s, { kind: R.success ? 'ritualwin' : 'rituallose', player: p });
      return null;
    }

    if (a.type === 'clashHit' || a.type === 'clashDone') {
      const c = s.clash;
      if (s.phase !== 'clash' || !c) return 'Gerade läuft kein Domain Clash.';
      if (a.type === 'clashDone') { if (!c.done) return 'Der Clash läuft noch.'; finishResult(s); return null; }
      if (c.hits[p].length >= c.rounds) return 'Du bist schon fertig.';
      if (a.round !== c.hits[p].length) return null; // doppelte Nachricht ignorieren
      const off = Math.max(0, Math.min(1, Number(a.offset)));
      clashHit(s, p, Number.isFinite(off) ? off : 1);
      return null;
    }

    if (a.type === 'spin' || a.type === 'stopSpin' || a.type === 'gambleDone') {
      const G = s.gamble;
      if (s.phase !== 'gamble' || !G) return 'Gerade gibt es keinen Automaten.';
      if (p !== G.player) return 'Nur der Besitzer von Idle Death Gamble darf drehen.';
      if (a.type === 'gambleDone') { if (!G.done) return 'Erst fertig spielen.'; afterGamble(s); return null; }
      if (G.done) return 'Der Automat ist schon fertig.';
      if (a.type === 'stopSpin') {
        G.done = true;
        G.outcome = G.last === 'reach' || G.last === 'fever' ? G.last : 'none';
        log(s, `${pl.name} hört am Automaten auf.`);
        return null;
      }
      if (G.spinsLeft < 1) return 'Keine Spins mehr.';
      const g = (getPack(s).effects || []).find((e) => e.type === 'gamble');
      const res = spinOnce(s, g);
      G.spinsLeft--;
      G.spins.push(res);
      G.last = res;
      if (res === 'jackpot') { G.done = true; G.outcome = 'jackpot'; log(s, `🎰 JACKPOT für ${pl.name}!`); }
      else if (G.spinsLeft === 0) { G.done = true; G.outcome = res; }
      return null;
    }

    if (s.phase !== 'auction' || !s.current) return 'Gerade läuft keine Versteigerung.';
    const c = s.current;

    if (a.type === 'skip') {
      if (pl.tokens.skip < 1) return 'Du hast deinen Skip schon benutzt.';
      const why = skipBlocked(s, p);
      if (why) return why;
      pl.tokens.skip--;
      return discard(s, p, 'skipped'), null;
    }

    if (a.type === 'endskip') {
      if (!(soloPhase(s) && isActive(s, p))) return 'Final Skip geht erst, wenn dein Gegner nichts mehr kaufen kann.';
      if (pl.tokens.endskip < 1) return 'Du hast deinen Final Skip schon benutzt.';
      pl.tokens.endskip--;
      return discard(s, p, 'endskip'), null;
    }

    if (a.type === 'peek') {
      if (pl.tokens.peek < 1) return 'Du hast Sneak Peek schon benutzt.';
      if (!isActive(s, p)) return 'Du kannst nichts mehr kaufen – Sneak Peek geht nicht mehr.';
      if (s.deck.length === 0) return 'Es kommt keine Karte mehr.';
      if (s.peek && s.peek.seen[p]) return 'Du hast Sneak Peek schon benutzt.';
      pl.tokens.peek--;
      if (!s.peek) s.peek = { id: peekNext(s), seen: [false, false], votes: [false, false], accepted: false };
      s.peek.seen[p] = true;
      log(s, `${pl.name} nutzt Sneak Peek.`);
      event(s, { kind: 'peek', player: p });
      return null;
    }

    if (a.type === 'peekvote') {
      if (!s.peek) return 'Noch hat niemand Sneak Peek benutzt.';
      if (s.peek.accepted) return 'Ist schon beschlossen.';
      const o = other(p);
      // Vorschlagen darf nur, wer gespickt hat – der andere kann danach zustimmen (blind oder selbst gespickt)
      if (!s.peek.votes[p] && !s.peek.seen[p] && !s.peek.votes[o]) return 'Erst muss jemand, der gespickt hat, das Überspringen vorschlagen.';
      if (s.peek.seen[p] && !isActive(s, o)) {
        s.peek.accepted = true;
        s.peek.votes[p] = true;
        s.skipNext = s.peek.id;
        log(s, `${pl.name} überspringt die nächste Karte sofort (Sneak Peek).`);
        return null;
      }
      s.peek.votes[p] = !s.peek.votes[p];
      // Zieht der Vorschlagende zurück, ist auch eine blinde Zustimmung hinfällig
      if (!s.peek.votes[p] && s.peek.votes[o] && !s.peek.seen[o]) s.peek.votes[o] = false;
      if (s.peek.votes[0] && s.peek.votes[1]) {
        s.peek.accepted = true;
        s.skipNext = s.peek.id;
        log(s, 'Beide sind einverstanden: Die nächste Karte wird übersprungen.');
      }
      return null;
    }

    if (c.turn !== p) return 'Du bist nicht dran.';

    if (a.type === 'bid') {
      const amount = Math.floor(Number(a.amount));
      if (!canBid(s, p)) return 'Du kannst hier nicht bieten.';
      if (!Number.isFinite(amount) || amount < 1) return 'Gebot muss mindestens 1 € sein.';
      if (amount <= c.highBid) return `Du musst mehr als ${c.highBid} € bieten.`;
      if (amount > pl.budget) return `Du hast nur noch ${pl.budget} €.`;
      c.highBid = amount;
      c.highBidder = p;
      c.bids.push({ p, amount });
      c.turn = other(p);
      advanceTurn(s);
      return null;
    }

    if (a.type === 'pass') {
      if (c.highBidder === null) return 'Du fängst an – du musst mindestens 1 € bieten. Ablehnen geht erst nach einem Gebot.';
      return award(s, c.highBidder), null;
    }
    return 'Unbekannte Aktion.';
  }

  // ───────── Punkte ─────────
  // side: { abilities, sacrifice, target, sealed:[ids], equip:[benutzte ids], energy:id|null, jackpot:bool }

  // Wert einer Fähigkeit nach Abhängigkeit + Fluchkraft-Ausgleich (ohne Gegner-Effekte)
  function baseValue(pack, a, ids, energy) {
    if (!a.needs || a.needs.ids.some((id) => ids.includes(id))) return { v: a.value, weak: false, healed: 0 };
    const ctrl = energy ? energy.control : 0;
    const healed = Math.round((a.value - a.needs.weak) * ctrl);
    return { v: a.needs.weak + healed, weak: true, healed };
  }

  function effIdsOf(side) {
    return side.abilities.filter((id) => id !== side.sacrifice && !(side.sealed || []).includes(id));
  }

  function score(pack, me, foe) {
    const byId = Object.fromEntries(pack.abilities.map((a) => [a.id, a]));
    const eqById = Object.fromEntries((pack.equipment || []).map((e) => [e.id, e]));
    const enById = Object.fromEntries((pack.energy || []).map((e) => [e.id, e]));
    const effects = pack.effects || [];
    const effIds = effIdsOf(me);
    const foeIds = effIdsOf(foe);
    const list = effIds.map((id) => byId[id]);
    const enemy = foeIds.map((id) => byId[id]);
    const energy = me.energy ? enById[me.energy] : null;
    const foeEnergy = foe.energy ? enById[foe.energy] : null;
    const has = (ids, id) => ids.includes(id);
    const lines = [];
    const weakened = [];
    const val = {};

    // 1) Grundwerte: Abhängigkeiten + Ausgleich durch Fluchkraft-Kontrolle
    for (const a of list) {
      const b = baseValue(pack, a, effIds, energy);
      val[a.id] = b.v;
      if (b.weak) {
        weakened.push(a.id);
        if (b.healed > 0) lines.push({ kind: 'energy', label: `${energy.name} gleicht die Schwäche von ${a.name} aus`, points: 0 });
      }
    }

    // 1b) Mahoraga-Ritual
    if (me.ritual && val.mahoraga !== undefined) {
      const full = byId.mahoraga.value;
      const wi = weakened.indexOf('mahoraga');
      if (wi >= 0) weakened.splice(wi, 1);
      if (me.ritual === 'win') {
        val.mahoraga = full;
        lines.push({ kind: 'combo', label: 'Mahoraga bezwungen – er kämpft für dich', points: 0 });
      } else if (me.ritual === 'skip') {
        val.mahoraga = Math.round(full / 2);
        lines.push({ kind: 'nojackpot', label: 'Mahoraga nicht beschworen – zählt nur halb', points: 0 });
      } else if (me.ritual === 'lose') {
        val.mahoraga = 0;
        list.forEach((a) => { if (a.id !== 'mahoraga') val[a.id] = Math.round(val[a.id] * (1 - 0.15)); });
        lines.push({ kind: 'debuff', label: 'Mahoraga hat dich weggeschlagen – alle Fähigkeiten geschwächt', points: 0 });
      }
    }

    // 2) Charakter-Synergie (z. B. Gojo): jede Karte wird stärker, je mehr man von ihm hat
    const userCount = {};
    list.forEach((a) => (userCount[a.user] = (userCount[a.user] || 0) + 1));
    for (const [u, f] of Object.entries(pack.userSynergy || {})) {
      const n = userCount[u] || 0;
      if (n < 2) continue;
      let plus = 0;
      list.filter((a) => a.user === u).forEach((a) => { const nv = Math.round(val[a.id] * (1 + f * (n - 1))); plus += nv - val[a.id]; val[a.id] = nv; });
      lines.push({ kind: 'user', label: `${u}-Synergie: ${n} Techniken verstärken sich`, points: 0, hiddenPoints: plus });
    }

    // 3) Binding Vow
    if (me.target && val[me.target] !== undefined) {
      const a = byId[me.target];
      const boosted = Math.round(val[a.id] * (pack.vowMultiplier || 1.75));
      lines.push({ kind: 'vow', label: `Binding Vow: ${a.name} verstärkt`, points: 0 });
      val[a.id] = boosted;
    }

    // 4) Effekte des Gegners gegen mich (Beschlagnahmen, Stoppen) – Heilung mildert sie
    const heal = effects.find((e) => e.type === 'heal' && has(effIds, e.id));
    for (const e of effects.filter((x) => x.type === 'debuff' && has(foeIds, x.id))) {
      const targets = list.filter((a) => a.type === e.vsType);
      if (!targets.length) continue;
      const t = targets.reduce((best, a) => (val[a.id] > val[best.id] ? a : best));
      const factor = heal ? 1 - (1 - e.factor) * heal.factor : e.factor;
      val[t.id] = Math.round(val[t.id] * factor);
      lines.push({ kind: 'debuff', label: `${e.label}: ${t.name}${heal ? ' (durch Heilung gemildert)' : ''}`, points: 0 });
    }

    // 4b) Automat von Idle Death Gamble
    const gm = effects.find((e) => e.type === 'gamble');
    if (gm && me.gamble === 'jackpot') {
      list.forEach((a) => { val[a.id] = Math.round(val[a.id] * (1 + gm.jackpotAbilityBoost)); });
      if (!me.energyMode) list.filter((a) => a.type === 'domain').forEach((a) => { val[a.id] = Math.round(val[a.id] * gm.jackpotDomainMult); });
      lines.push({ kind: 'jackpot', label: `🎰 JACKPOT! Alle Fähigkeiten stärker${me.energyMode ? ', Fluchkraft verdoppelt' : ', Domains zählen doppelt'}`, points: 0 });
    } else if (gm && me.gamble === 'reach') {
      list.forEach((a) => { val[a.id] = Math.round(val[a.id] * (1 + gm.reachBoost)); });
      lines.push({ kind: 'jackpot', label: 'Trostpreis „Reach“: alle Fähigkeiten etwas stärker', points: 0 });
    } else if (gm && me.gamble === 'fever' && val[gm.id] !== undefined) {
      val[gm.id] = Math.round(val[gm.id] * (1 + gm.feverBoost));
      lines.push({ kind: 'jackpot', label: 'Trostpreis „Fever“: Idle Death Gamble stärker', points: 0 });
    } else if (gm && me.gamble === 'none') {
      lines.push({ kind: 'nojackpot', label: 'Automat: rechtzeitig aufgehört – kein Gewinn, keine Strafe', points: 0 });
    }
    if (gm && foe.gamble === 'jackpot' && energy) lines.push({ kind: 'debuff', label: 'Gegnerischer Jackpot schwächt deine Fluchkraft', points: 0 });

    // 4c) Domain Clash
    if (me.clash === 'win') {
      const h = me.clashHalved ? 0.5 : 1;
      list.forEach((a) => { val[a.id] = Math.round(val[a.id] * (1 + 0.08 * h)); });
      if (val[me.clashDomain] !== undefined) val[me.clashDomain] = Math.round(val[me.clashDomain] * (1 + 0.2 * h));
      lines.push({ kind: 'duel', label: `Domain Clash gewonnen: ${byId[me.clashDomain].name}${me.clashHalved ? ' (Simple Domain des Gegners bremst)' : ''}`, points: 0 });
    } else if (me.clash === 'lose') {
      lines.push({ kind: 'nojackpot', label: `Domain Clash verloren: ${byId[me.clashDomain].name}`, points: 0 });
    }

    let base = list.reduce((sum, a) => sum + val[a.id], 0);

    // 5) Klassen
    const tagCount = {};
    list.forEach((a) => a.tags.forEach((t) => (tagCount[t] = (tagCount[t] || 0) + 1)));
    for (const [t, n] of Object.entries(tagCount)) {
      const b = pack.tagBonus[Math.min(n, pack.tagBonus.length - 1)];
      if (b) lines.push({ kind: 'tag', label: `Klasse ${pack.tags[t].name} ×${n}`, points: b });
    }

    // 6) Gleicher Charakter
    for (const [u, n] of Object.entries(userCount)) {
      const b = pack.userBonus[Math.min(n, pack.userBonus.length - 1)];
      if (b) lines.push({ kind: 'user', label: `Gleicher Charakter: ${u} ×${n}`, points: b });
    }

    // 7) Kombos + Allrounder
    for (const c of pack.combos) {
      if (c.needs.every((id) => has(effIds, id))) lines.push({ kind: 'combo', label: `Kombo: ${c.name}`, points: c.bonus, desc: c.desc });
    }
    const types = new Set(list.map((a) => a.type));
    if (types.has('domain') && types.has('technik') && types.has('kampf'))
      lines.push({ kind: 'all', label: 'Allrounder (alle 3 Arten)', points: pack.allrounderBonus });

    // 8) Konter (Fähigkeiten + Ausrüstung) – Boogie Woogie des Gegners schwächt den stärksten ab
    const counterLines = [];
    const countIn = (k) => enemy.filter((a) => (k.vsType && a.type === k.vsType) || (k.vsIds && k.vsIds.includes(a.id))
      || (k.vsUser && a.user === k.vsUser) || (k.vsTag && a.tags.includes(k.vsTag))).length;
    for (const k of pack.counters) {
      if (!has(effIds, k.id)) continue;
      const n = countIn(k);
      if (n) counterLines.push({ kind: 'counter', label: `Konter: ${byId[k.id].name} ×${n}`, points: k.bonus * n, desc: k.desc });
    }

    // 9) Ausrüstung
    for (const id of me.equip || []) {
      const e = eqById[id];
      if (!e) continue;
      base += e.value;
      if (list.some((a) => a.user === e.user))
        lines.push({ kind: 'equip', label: `${e.name}: gehört zu ${e.user}`, points: pack.equipUserBonus });
      const fit = (e.fits || []).map((x) => byId[x]).find((a) => a && has(effIds, a.id));
      if (fit) lines.push({ kind: 'equip', label: `${e.name} passt zu ${fit.name}`, points: pack.equipFitBonus });
      for (const k of e.counters || []) {
        const n = countIn(k);
        if (n) counterLines.push({ kind: 'counter', label: `Konter: ${e.name} ×${n}`, points: k.bonus * n, desc: k.desc });
      }
    }
    const shield = effects.find((e) => e.type === 'shield' && has(foeIds, e.id));
    if (shield && counterLines.length) {
      const top = counterLines.reduce((b, l) => (l.points > b.points ? l : b));
      top.points = Math.round(top.points * shield.factor);
      top.label += ` (${shield.label})`;
    }
    lines.push(...counterLines);

    // 10) Copy: kopiert einen Teil der stärksten gegnerischen Technik
    for (const e of effects.filter((x) => x.type === 'copy' && has(effIds, x.id))) {
      const t = enemy.filter((a) => a.type === e.vsType);
      if (!t.length) continue;
      const best = t.reduce((b, a) => (baseValue(pack, a, foeIds, foeEnergy).v > baseValue(pack, b, foeIds, foeEnergy).v ? a : b));
      lines.push({ kind: 'copy', label: `${e.label}: ${best.name}`, points: Math.round(baseValue(pack, best, foeIds, foeEnergy).v * e.share) });
    }

    // 11) Domain-Duell: die stärkere Domain gewinnt
    const myDom = list.filter((a) => a.type === 'domain').map((a) => val[a.id]);
    const foeDom = enemy.filter((a) => a.type === 'domain').map((a) => baseValue(pack, a, foeIds, foeEnergy).v);
    if (!me.clash && myDom.length && foeDom.length && Math.max(...myDom) > Math.max(...foeDom) && pack.domainDuelBonus) {
      const best = list.filter((a) => a.type === 'domain').reduce((b, a) => (val[a.id] > val[b.id] ? a : b));
      lines.push({ kind: 'duel', label: `Domain-Duell gewonnen: ${best.name}`, points: pack.domainDuelBonus });
    }

    // 13) Fluchkraft
    if (energy) {
      let ePts = energy.amount * (pack.energyPointFactor || 0.5);
      if (gm && me.gamble === 'jackpot') ePts *= gm.jackpotEnergyMult;
      if (gm && foe.gamble === 'jackpot') ePts *= gm.jackpotFoeEnergyMult;
      base += Math.round(ePts);
      lines.push({ kind: 'energy', label: `Fluchkraft: ${energy.name}`, points: 0 });
      const hungry = list.filter((a) => a.hungry);
      if (hungry.length && energy.amount > 0)
        lines.push({ kind: 'energy', label: `Genug Fluchkraft für ${hungry.length} energiehungrige Fähigkeit${hungry.length > 1 ? 'en' : ''}`,
          points: hungry.length * Math.round(energy.amount * (pack.energyHungryFactor || 0.12)) });
      if (list.some((a) => a.user === energy.user))
        lines.push({ kind: 'energy', label: `Eigene Fluchkraft von ${energy.user}`, points: pack.energyOwnBonus || 0 });
      if (energy.special && energy.special.ifAny.some((id) => has(effIds, id)))
        lines.push({ kind: 'energy', label: energy.special.label, points: energy.special.bonus });
    }

    let bonus = lines.reduce((sum, l) => sum + l.points, 0);
    if (gm && me.gamble === 'miss') {
      const minus = Math.round((base + bonus) * gm.missPenalty);
      lines.push({ kind: 'debuff', label: 'Automat: alle Spins verloren – alles etwas schwächer', points: -minus });
      bonus -= minus;
    }
    return { base, lines, bonus, weakened, total: base + bonus };
  }

  function sideOf(s, p) {
    const pl = s.players[p];
    const ch = pl.choice || {};
    return {
      abilities: pl.slots, sacrifice: ch.sacrifice || null, target: ch.target || null,
      sealed: s.seal && s.seal.target === p && s.seal.sealed ? [s.seal.sealed] : [],
      equip: ch.equipUse || [], energy: pl.energy[0] || null, energyMode: !!s.energyMode,
      gamble: s.gamble && s.gamble.player === p ? s.gamble.outcome : null,
      ritual: s.ritual && s.ritual.player === p ? (!s.ritual.summon ? 'skip' : s.ritual.success ? 'win' : 'lose') : null,
      clash: s.clash && s.clash.done ? (s.clash.winner === p ? 'win' : 'lose') : null,
      clashDomain: s.clash ? s.clash.domains[p] : null,
      clashHalved: !!(s.clash && s.clash.guarded[1 - p]),
    };
  }

  function computeResult(s, pack, rnd) {
    rnd = rnd || Math.random;
    const sides = [sideOf(s, 0), sideOf(s, 1)];
    const r = [score(pack, sides[0], sides[1]), score(pack, sides[1], sides[0])];
    const winner = r[0].total === r[1].total ? -1 : r[0].total > r[1].total ? 0 : 1;
    s.result = { scores: r, winner, gamble: sides.map((x) => x.gamble) };
    return s.result;
  }

  const api = {
    SLOTS, BUDGET, SKIP_MAX_BID, CLASH_ROUNDS, skipBlocked, setBoosts, equipAllowed, liveAbilities, countingAbilities, newGame, startAuction, startStage,
    act, isActive, canBid, hasDomain, isDomain, canOverbid, soloPhase, stageSlots, score, computeResult,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Game = api;
})(typeof window !== 'undefined' ? window : globalThis);
