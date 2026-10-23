// Spielregeln – reine Logik ohne Anzeige.
// Der Host (Raum-Ersteller) rechnet den Spielstand, der Gast bekommt ihn geschickt.
//
// Ablauf: coin → auction (Fähigkeiten) → [intermission → auction (Ausrüstung)] → [final] → result
//   final = Bindungsschwur einsetzen und/oder 2 von 3 Ausrüstungen wählen

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

  function newGame(pack, names, settings, rnd) {
    rnd = rnd || Math.random;
    const mode = settings && settings.mode === 'equipment' ? 'equipment' : 'classic';
    const kinds = {}, names_ = {}, users = {};
    pack.abilities.forEach((a) => { kinds[a.id] = 'ability'; });
    (pack.vows || []).forEach((v) => { kinds[v.id] = 'vow'; });
    (pack.equipment || []).forEach((e) => { kinds[e.id] = e.type === 'storage' ? 'storage' : 'equip'; });
    [...pack.abilities, ...(pack.vows || []), ...(pack.equipment || [])].forEach((x) => { names_[x.id] = x.name; users[x.id] = x.user; });
    return {
      phase: 'coin',
      packId: pack.id,
      mode,
      stage: 'abilities',
      limits: { abilities: SLOTS, equipment: pack.equipSlots || 3 },
      equipUse: pack.equipUse || 2,
      players: names.map((name) => ({
        name, budget: BUDGET, slots: [], paid: {}, filled: [],
        vow: null, storage: null, equip: [], equipFilled: [], leftover: null,
        tokens: freshTokens(), choice: null, ready: false,
      })),
      deck: shuffle(pack.abilities.map((a) => a.id).concat((pack.vows || []).map((v) => v.id)), rnd),
      graveyard: [],
      kinds,
      names: names_,
      users,
      lockedNext: null, // beim Spicken festgelegte nächste Karte
      coin: rnd() < 0.5 ? 0 : 1,
      nextStarter: null,
      round: 0,
      current: null,
      peek: null,       // { id, seen:[bool,bool], votes:[bool,bool], accepted }
      skipNext: null,   // per Spicken beschlossen: diese Karte wird beim Ziehen übersprungen
      events: [],       // für Meldungen in der Anzeige
      evSeq: 0,
      log: [],
      result: null,
    };
  }

  const other = (p) => 1 - p;

  function stageSlots(s, p) {
    return s.stage === 'abilities' ? s.players[p].slots : s.players[p].equip;
  }
  function limit(s) { return s.limits[s.stage]; }

  // Kann der Spieler in dieser Runde (Fähigkeiten / Ausrüstung) noch etwas kaufen?
  function isActive(s, p) {
    return stageSlots(s, p).length < limit(s) && s.players[p].budget >= 1;
  }
  // Kann er auf die aktuelle Karte bieten? (Bindungsschwur braucht keinen normalen Slot)
  function canBid(s, p, id) {
    id = id || (s.current && s.current.id);
    if (s.kinds[id] === 'vow') return s.players[p].budget >= 1 && !s.players[p].vow;
    if (s.kinds[id] === 'storage') return s.players[p].budget >= 1 && !s.players[p].storage;
    return isActive(s, p);
  }
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
  // Einer kann nicht mehr kaufen, der andere schon → Schluss-Skip erlaubt
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

  // Nach der Pause: Ausrüstungs-Runde starten
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
      if (isSpecial(s, id) && !canBid(s, 0, id) && !canBid(s, 1, id)) { s.graveyard.push(id); continue; }
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

  // Leere Slots der aktuellen Runde zufällig füllen
  function fillRandom(s, rnd) {
    rnd = rnd || Math.random;
    const want = s.stage === 'abilities' ? 'ability' : 'equip';
    const pool = shuffle(s.deck, rnd).concat(shuffle(s.graveyard, rnd)).filter((id) => s.kinds[id] === want);
    s.players.forEach((pl, p) => {
      const slots = stageSlots(s, p);
      const filled = s.stage === 'abilities' ? pl.filled : pl.equipFilled;
      while (slots.length < limit(s) && pool.length) {
        const id = pool.shift();
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
    if (s.stage === 'abilities' && s.mode === 'equipment') {
      log(s, 'Fähigkeiten-Runde vorbei – jetzt kommt die Ausrüstung!');
      s.stage = 'equipment';
      s.phase = 'intermission';
      s.players.forEach((pl) => {
        pl.leftover = pl.budget;
        pl.budget = pl.budget * 2;
        pl.tokens = freshTokens();
      });
      s.deck = shuffle((getPack(s).equipment || []).map((e) => e.id), Math.random);
      s.graveyard = [];
      return;
    }
    log(s, 'Versteigerung vorbei – leere Slots wurden zufällig gefüllt.');
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
    if (s.players.every((pl) => pl.ready)) return finishResult(s);
    s.phase = 'final';
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
      if (s.players.every((x) => x.ready)) finishResult(s);
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
  // me / foe: { abilities: [ids], sacrifice, target, equip: [benutzte ids] }
  function score(pack, me, foe) {
    const byId = Object.fromEntries(pack.abilities.map((a) => [a.id, a]));
    const eqById = Object.fromEntries((pack.equipment || []).map((e) => [e.id, e]));
    const effIds = me.abilities.filter((id) => id !== me.sacrifice);
    const list = effIds.map((id) => byId[id]);
    const enemy = foe.abilities.filter((id) => id !== foe.sacrifice).map((id) => byId[id]);
    const lines = [];
    const weakened = [];

    // Grundwerte (+ Abhängigkeiten, + Bindungsschwur)
    let base = 0;
    for (const a of list) {
      let v = a.value;
      if (a.needs && !a.needs.ids.some((id) => effIds.includes(id))) { v = a.needs.weak; weakened.push(a.id); }
      if (a.id === me.target) {
        const boosted = Math.round(v * (pack.vowMultiplier || 1.75));
        lines.push({ kind: 'vow', label: `Binding Vow: ${a.name} verstärkt`, points: boosted - v });
        v = boosted;
      }
      base += v;
    }

    // Klassen
    const tagCount = {};
    list.forEach((a) => a.tags.forEach((t) => (tagCount[t] = (tagCount[t] || 0) + 1)));
    for (const [t, n] of Object.entries(tagCount)) {
      const b = pack.tagBonus[Math.min(n, pack.tagBonus.length - 1)];
      if (b) lines.push({ kind: 'tag', label: `Klasse ${pack.tags[t].name} ×${n}`, points: b });
    }

    // Gleicher Charakter
    const userCount = {};
    list.forEach((a) => (userCount[a.user] = (userCount[a.user] || 0) + 1));
    for (const [u, n] of Object.entries(userCount)) {
      const b = pack.userBonus[Math.min(n, pack.userBonus.length - 1)];
      if (b) lines.push({ kind: 'user', label: `Gleicher Charakter: ${u} ×${n}`, points: b });
    }

    // Feste Kombos
    for (const c of pack.combos) {
      if (c.needs.every((id) => effIds.includes(id))) lines.push({ kind: 'combo', label: `Kombo: ${c.name}`, points: c.bonus, desc: c.desc });
    }

    // Allrounder
    const types = new Set(list.map((a) => a.type));
    if (types.has('domain') && types.has('technik') && types.has('kampf'))
      lines.push({ kind: 'all', label: 'Allrounder (alle 3 Arten)', points: pack.allrounderBonus });

    // Konter
    const countIn = (k) => enemy.filter((a) => (k.vsType && a.type === k.vsType) || (k.vsIds && k.vsIds.includes(a.id))
      || (k.vsUser && a.user === k.vsUser) || (k.vsTag && a.tags.includes(k.vsTag))).length;
    for (const k of pack.counters) {
      if (!effIds.includes(k.id)) continue;
      const n = countIn(k);
      if (n) lines.push({ kind: 'counter', label: `Konter: ${byId[k.id].name} ×${n}`, points: k.bonus * n, desc: k.desc });
    }

    // Ausrüstung
    for (const id of me.equip || []) {
      const e = eqById[id];
      if (!e) continue;
      base += e.value;
      if (list.some((a) => a.user === e.user))
        lines.push({ kind: 'equip', label: `${e.name}: gehört zu ${e.user}`, points: pack.equipUserBonus });
      const fit = (e.fits || []).map((x) => byId[x]).find((a) => a && effIds.includes(a.id));
      if (fit) lines.push({ kind: 'equip', label: `${e.name} passt zu ${fit.name}`, points: pack.equipFitBonus });
      for (const k of e.counters || []) {
        const n = countIn(k);
        if (n) lines.push({ kind: 'counter', label: `Konter: ${e.name} ×${n}`, points: k.bonus * n, desc: k.desc });
      }
    }

    const bonus = lines.reduce((sum, l) => sum + l.points, 0);
    return { base, lines, bonus, weakened, total: base + bonus };
  }

  function sideOf(pl) {
    const ch = pl.choice || {};
    return { abilities: pl.slots, sacrifice: ch.sacrifice || null, target: ch.target || null, equip: ch.equipUse || [] };
  }

  function computeResult(s, pack) {
    const a = sideOf(s.players[0]);
    const b = sideOf(s.players[1]);
    const r = [score(pack, a, b), score(pack, b, a)];
    const winner = r[0].total === r[1].total ? -1 : r[0].total > r[1].total ? 0 : 1;
    s.result = { scores: r, winner };
    return s.result;
  }

  const api = { SLOTS, BUDGET, SKIP_MAX_BID, skipBlocked, setBoosts, equipAllowed, newGame, startAuction, startStage, act, isActive, canBid, canOverbid, soloPhase, stageSlots, score, computeResult };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Game = api;
})(typeof window !== 'undefined' ? window : globalThis);
