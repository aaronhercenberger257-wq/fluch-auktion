// Oberfläche + Ablauf: Startseite → Lobby → Münzwurf → Versteigerung → [Ausrüstung] → [Auswahl] → Ergebnis

(function () {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  let net = null;
  let me = 0;               // 0 = Host, 1 = Gast
  let myName = '';
  let foeName = '';
  let guestConnected = false;
  let settings = { packId: Object.keys(PACKS)[0], mode: 'classic', energy: false };
  let state = null;
  const ui = {
    gameId: null, coinShown: null, lastRound: null, lastHigh: null, slotCounts: [0, 0, 0, 0], lastEv: 0,
    descOpen: false, bid: null, starting: false, stageTimer: null, final: null,
  };

  const pack = () => PACKS[(state && state.packId) || settings.packId];
  const item = (id) => {
    const p = pack();
    return p.abilities.find((a) => a.id === id) || (p.vows || []).find((v) => v.id === id) || (p.equipment || []).find((e) => e.id === id) || (p.energy || []).find((e) => e.id === id);
  };
  const foe = () => 1 - me;
  const MODES = {
    classic: { name: 'Klassisch', desc: '5 Fähigkeiten, 20 € Budget.' },
    equipment: { name: 'Mit Ausrüstung', desc: 'Erst 5 Fähigkeiten, dann 3 Ausrüstungs-Slots mit doppeltem Restgeld. Am Ende zählen 2 davon.' },
  };

  function store(key, val) { try { if (val === undefined) return localStorage.getItem(key); localStorage.setItem(key, val); } catch (e) { return null; } }

  // ───────── Bildschirme ─────────
  function show(name) {
    const el = document.getElementById('screen-' + name);
    if (el.classList.contains('active')) return;
    document.querySelectorAll('.screen').forEach((s) => s.classList.toggle('active', s === el));
    window.scrollTo(0, 0);
  }

  let toastTimer;
  function toast(text, isErr) {
    const t = $('#toast');
    t.textContent = text;
    t.classList.toggle('err', !!isErr);
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('show'), 3000);
  }

  function openModal(html) {
    $('#modal-body').innerHTML = html;
    $('#modal').hidden = false;
  }
  function closeModal() { $('#modal').hidden = true; }

  // ───────── Startseite ─────────
  $('#in-name').value = store('fa-name') || '';
  const urlCode = new URLSearchParams(location.search).get('raum');
  if (urlCode) $('#in-code').value = urlCode.toUpperCase();

  function readName() {
    const n = $('#in-name').value.trim();
    if (!n) { $('#start-error').textContent = 'Gib zuerst deinen Namen ein.'; $('#in-name').focus(); return null; }
    store('fa-name', n);
    return n.slice(0, 16);
  }

  $('#btn-create').onclick = () => {
    const n = readName(); if (!n) return;
    myName = n; me = 0;
    $('#start-error').textContent = '';
    $('#btn-create').disabled = true;
    $('#btn-create').textContent = 'Raum wird erstellt …';
    net = Net.host({
      onOpen(code) {
        $('#btn-create').disabled = false;
        $('#btn-create').textContent = 'Raum erstellen';
        $('#lobby-code').textContent = code;
        show('lobby');
        renderLobby();
      },
      onGuest() {},
      onMessage: hostMessage,
      onClose: lost,
      onError(text) {
        $('#btn-create').disabled = false;
        $('#btn-create').textContent = 'Raum erstellen';
        if (document.querySelector('#screen-start.active')) $('#start-error').textContent = text;
        else if (!guestConnected) $('#lobby-error').textContent = text;
      },
    });
  };

  $('#btn-join').onclick = () => {
    const n = readName(); if (!n) return;
    const code = $('#in-code').value.trim().toUpperCase();
    if (code.length !== 5) { $('#start-error').textContent = 'Der Raum-Code hat 5 Zeichen.'; return; }
    myName = n; me = 1;
    $('#start-error').textContent = '';
    $('#btn-join').disabled = true;
    $('#btn-join').textContent = 'Suche …';
    net = Net.join(code, {
      onOpen() {
        $('#btn-join').disabled = false;
        $('#btn-join').textContent = 'Beitreten';
        net.send({ t: 'hello', name: myName });
        $('#lobby-code').textContent = code;
        show('lobby');
        renderLobby();
      },
      onMessage: guestMessage,
      onClose: lost,
      onError(text) {
        $('#btn-join').disabled = false;
        $('#btn-join').textContent = 'Beitreten';
        $('#start-error').textContent = text;
      },
    });
  };
  $('#in-code').addEventListener('keydown', (e) => { if (e.key === 'Enter') $('#btn-join').click(); });

  $('#btn-rules').onclick = () => openModal(rulesHTML());

  // ───────── Lobby ─────────
  const packSelect = $('#set-pack');
  packSelect.innerHTML = Object.values(PACKS).map((p) => `<option value="${p.id}">${esc(p.name)}</option>`).join('') +
    '<option disabled>Mehr Anime (bald)</option><option disabled>Anime mischen (bald)</option>';
  const modeSelect = $('#set-mode');
  modeSelect.innerHTML = Object.entries(MODES).map(([k, m]) => `<option value="${k}">${m.name}</option>`).join('');

  packSelect.onchange = () => { settings.packId = packSelect.value; sendLobby(); };
  modeSelect.onchange = () => { settings.mode = modeSelect.value; renderLobby(); sendLobby(); };
  $('#set-energy').onchange = (e) => { settings.energy = e.target.checked; sendLobby(); };

  $('#btn-share').onclick = async () => {
    const link = location.origin + location.pathname + '?raum=' + $('#lobby-code').textContent;
    try {
      if (navigator.share && /Mobi|Android|iPhone/i.test(navigator.userAgent)) await navigator.share({ title: 'Fluch-Auktion', text: 'Spiel mit mir die Fluch-Auktion!', url: link });
      else { await navigator.clipboard.writeText(link); toast('Link kopiert – schick ihn deinem Freund!'); }
    } catch (e) {
      toast('Code: ' + $('#lobby-code').textContent);
    }
  };

  $('#btn-start').onclick = () => { if (me === 0 && guestConnected) startGame(); };

  function renderLobby() {
    const host = me === 0 ? myName : foeName;
    const guest = me === 1 ? myName : (guestConnected ? foeName : null);
    $('#lobby-players').innerHTML = `
      <div class="lobby-player"><span class="dot"></span><b>${esc(host || '…')}</b><span class="tag">${me === 0 ? 'Du · ' : ''}Host</span></div>
      ${guest ? `<div class="lobby-player"><span class="dot"></span><b>${esc(guest)}</b><span class="tag">${me === 1 ? 'Du · ' : ''}Gast</span></div>`
              : `<div class="lobby-player waiting"><span class="dot"></span><span class="muted">Warte auf Mitspieler …</span></div>`}`;
    packSelect.value = settings.packId;
    modeSelect.value = settings.mode || 'classic';
    $('#mode-desc').textContent = MODES[settings.mode || 'classic'].desc;
    $('#set-energy').checked = !!settings.energy;
    $('#lobby-settings').classList.toggle('readonly', me !== 0);
    const startBtn = $('#btn-start');
    if (me === 0) {
      startBtn.hidden = false;
      startBtn.disabled = !guestConnected;
      startBtn.textContent = guestConnected ? 'Spiel starten' : 'Warte auf Mitspieler …';
      $('#lobby-wait').textContent = guestConnected ? '' : 'Schick deinem Freund den Code oder den Link.';
    } else {
      startBtn.hidden = true;
      $('#lobby-wait').textContent = foeName ? `Warte, bis ${foeName} das Spiel startet …` : 'Verbinde …';
    }
  }

  function sendLobby() {
    if (me !== 0 || !net) return;
    net.send({ t: 'lobby', host: myName, settings });
  }

  // ───────── Netzwerk-Nachrichten ─────────
  function hostMessage(m) {
    if (!m || typeof m !== 'object') return;
    if (m.t === 'hello') {
      foeName = String(m.name || 'Spieler 2').slice(0, 16);
      guestConnected = true;
      sendLobby();
      if (state) broadcast(); else renderLobby();
    } else if (m.t === 'act' && state) {
      const err = Game.act(state, 1, m.a || {});
      if (err) net.send({ t: 'err', text: err });
      broadcast();
    } else if (m.t === 'rematch' && state && state.phase === 'result') {
      toast(`${foeName} will eine Revanche!`);
      ui.rematchAsked = true;
      render();
    }
  }

  function guestMessage(m) {
    if (!m || typeof m !== 'object') return;
    if (m.t === 'lobby') {
      foeName = m.host;
      settings = m.settings;
      if (!state) renderLobby();
    } else if (m.t === 'state') {
      state = m.state;
      render();
    } else if (m.t === 'err') {
      toast(m.text, true);
    } else if (m.t === 'full') {
      $('#start-error').textContent = 'Der Raum ist schon voll.';
      show('start');
    }
  }

  function broadcast() {
    net.send({ t: 'state', state });
    // Host: nach dem Domain Clash automatisch weiter (falls keiner klickt)
    if (state.phase === 'clash' && state.clash && state.clash.done && !ui.clashTimer) {
      ui.clashTimer = setTimeout(() => {
        ui.clashTimer = null;
        if (state.phase === 'clash') { Game.act(state, 0, { type: 'clashDone' }); broadcast(); }
      }, 9000);
    }
    // Host: nach der Pause die Ausrüstungs-Runde starten
    if (state.phase === 'intermission' && !ui.stageTimer) {
      ui.stageTimer = setTimeout(() => {
        ui.stageTimer = null;
        if (state.phase === 'intermission') { Game.startStage(state); broadcast(); }
      }, 6500);
    }
    render();
  }

  function startGame() {
    if (ui.starting) return;
    ui.starting = true;
    ui.rematchAsked = false;
    state = Game.newGame(PACKS[settings.packId], [myName, foeName], { mode: settings.mode, energy: settings.energy });
    state.gameId = Date.now() + '-' + Math.random().toString(36).slice(2, 6);
    broadcast();
    setTimeout(() => {
      ui.starting = false;
      Game.startAuction(state);
      broadcast();
    }, 3800);
  }

  function doAction(a) {
    if (!state) return;
    if (me === 0) {
      const err = Game.act(state, 0, a);
      if (err) toast(err, true);
      broadcast();
    } else {
      net.send({ t: 'act', a });
    }
  }

  function lost() {
    if (!net) return;
    net = null;
    show('game');
    $('#game').innerHTML = `<div class="overlay-msg panel">
      <h2>Verbindung verloren</h2>
      <p class="muted">${esc(foeName || 'Der andere Spieler')} ist nicht mehr verbunden.</p>
      <button class="btn btn-primary" data-action="home">Zur Startseite</button></div>`;
  }

  // ───────── Spiel anzeigen ─────────
  function render() {
    if (!state || !net) return;
    show('game');
    if (state.gameId !== ui.gameId) {
      ui.gameId = state.gameId;
      ui.lastRound = null; ui.slotCounts = [0, 0, 0, 0]; ui.lastHigh = null;
      ui.lastEv = state.evSeq; ui.final = null; ui.rematchSent = null; ui.sealPick = null; ui.spinSeen = 0; ui.spinning = false;
    }
    announceEvents();
    if (state.phase === 'coin') renderCoin();
    else if (state.phase === 'auction') renderAuction();
    else if (state.phase === 'intermission') renderIntermission();
    else if (state.phase === 'final') renderFinal();
    else if (state.phase === 'seal') renderSeal();
    else if (state.phase === 'gamble') { if (!ui.spinning) renderGamble(); }
    else if (state.phase === 'clash') renderClash();
    else if (state.phase === 'result') renderResult();
  }

  function announceEvents() {
    const fresh = state.events.filter((e) => e.n > ui.lastEv);
    ui.lastEv = state.evSeq;
    const texts = fresh.map((ev) => {
      const nm = ev.id ? `„${item(ev.id).name}“` : '';
      const who = ev.player === me ? 'Du' : state.players[ev.player] && state.players[ev.player].name;
      if (ev.kind === 'won') return `${ev.player === me ? 'Du sicherst dir' : who + ' sichert sich'} ${nm} für ${ev.price} €`;
      if (ev.kind === 'skipped') return `${who} ${ev.player === me ? 'überspringst' : 'überspringt'} ${nm}`;
      if (ev.kind === 'endskip') return `${who} ${ev.player === me ? 'nutzt' : 'nutzt'} Final Skip auf ${nm}`;
      if (ev.kind === 'peekskip') return `${nm} wurde nach dem Sneak Peek übersprungen`;
      if (ev.kind === 'peek' && ev.player !== me) return `${who} hat Sneak Peek benutzt 👀`;
      if (ev.kind === 'sealstart') return ev.player === me ? 'Prison Realm öffnet sich …' : `${who} öffnet Prison Realm! 🧊`;
      if (ev.kind === 'clashstart') return 'DOMAIN CLASH! ⚔';
      if (ev.kind === 'clashwin') return ev.player === me ? 'Du gewinnst den Domain Clash!' : `${who} gewinnt den Domain Clash!`;
      if (ev.kind === 'gamblestart') return ev.player === me ? 'Der Automat von Idle Death Gamble wartet auf dich 🎰' : `${who} tritt an den Automaten 🎰`;
      if (ev.kind === 'sealed') return `${nm} wurde versiegelt 🔒`;
      return null;
    }).filter(Boolean);
    if (texts.length) toast(texts.join(' · '));
  }

  function renderCoin() {
    if (ui.coinShown === state.gameId) return;
    ui.coinShown = state.gameId;
    const [a, b] = state.players;
    $('#game').innerHTML = `<div class="coin-stage">
      <h2>Münzwurf</h2>
      <div class="coin flip-${state.coin}">
        <div class="coin-face a">${esc(a.name)}</div>
        <div class="coin-face b">${esc(b.name)}</div>
      </div>
      <p class="coin-result">${state.coin === me ? 'Du beginnst mit dem Bieten!' : esc(state.players[state.coin].name) + ' beginnt mit dem Bieten!'}</p>
      ${state.mode === 'equipment' ? '<p class="muted">Modus: Mit Ausrüstung</p>' : ''}
    </div>`;
  }

  const art = (it, uid) => Art.abilitySVG(it, { uid });

  function slotRow(p, ids, count, cls, offset) {
    const prev = ui.slotCounts[offset + p] || 0;
    return Array.from({ length: count }, (_, i) => {
      const id = ids[i];
      if (!id) return `<span class="slot ${cls}"></span>`;
      const it = item(id);
      return `<button class="slot filled ${cls} ${i >= prev ? 'pop' : ''}" data-action="detail" data-id="${id}" title="${esc(it.name)}">${art(it, 's' + offset + p + i)}</button>`;
    }).join('');
  }

  function tokenChips(pl) {
    const t = pl.tokens;
    return `<span class="tok ${t.skip ? '' : 'used'}" title="Skip">Skip</span>
      <span class="tok ${t.peek ? '' : 'used'}" title="Sneak Peek">Sneak Peek</span>
      <span class="tok ${t.endskip ? '' : 'used'}" title="Final Skip">Final Skip</span>`;
  }

  function playerBar(p) {
    const pl = state.players[p];
    const c = state.current;
    const isMe = p === me;
    const eqMode = state.mode === 'equipment';
    const vowSlot = pl.vow
      ? `<button class="slot vow filled" data-action="detail" data-id="${pl.vow}" title="Binding Vow">${art(item(pl.vow), 'v' + p)}</button>`
      : '<span class="slot vow" title="Extra-Slot für einen Binding Vow"></span>';
    const storageSlot = !eqMode ? '' : pl.storage
      ? `<button class="slot vow storage filled" data-action="detail" data-id="${pl.storage}" title="Inventory Curse">${art(item(pl.storage), 'st' + p)}</button>`
      : '<span class="slot vow storage" title="Extra-Slot für den Inventory Curse"></span>';
    return `<div class="pbar ${isMe ? 'me' : 'foe'} ${c && c.turn === p ? 'turn' : ''}">
      <div class="pbar-head">
        <span class="pname">${esc(pl.name)}${isMe ? '<small>Du</small>' : ''}</span>
        <span class="budget ${pl.budget === 0 ? 'zero' : ''}">${pl.budget} €</span>
      </div>
      <div class="slots-wrap">
        <div class="slots">${slotRow(p, pl.slots, Game.SLOTS, '', 0)}</div>
        ${vowSlot}
      </div>
      ${eqMode ? `<div class="slots-wrap eqwrap ${state.stage === 'equipment' ? '' : 'dim'}"><div class="slots eq">${slotRow(p, pl.equip, state.limits.equipment, 'equip', 2)}</div>${storageSlot}</div>` : ''}
      ${state.energyMode ? `<div class="energy-row ${state.stage === 'energy' ? '' : 'dim'}">${pl.energy[0]
        ? `<button class="slot energy filled" data-action="detail" data-id="${pl.energy[0]}" title="Fluchkraft">${art(item(pl.energy[0]), 'en' + p)}</button><span>${esc(item(pl.energy[0]).name)}</span>`
        : '<span class="slot energy" title="Fluchkraft"></span><span class="muted">Fluchkraft</span>'}</div>` : ''}
      <div class="pmeta">${tokenChips(pl)}</div>
    </div>`;
  }

  // Fluchkraft: Menge und Kontrolle als Wörter (keine genauen Zahlen)
  function energyChips(it) {
    const amt = it.amount >= 95 ? 'gewaltig' : it.amount >= 75 ? 'groß' : it.amount >= 55 ? 'mittel' : it.amount > 0 ? 'klein' : 'null';
    const ctl = it.control >= 0.8 ? 'meisterhaft' : it.control >= 0.6 ? 'gut' : it.control >= 0.4 ? 'mittel' : it.control > 0 ? 'schwach' : 'keine';
    return `<div class="chips"><span class="chip en">Menge: <b>${amt}</b></span><span class="chip en">Kontrolle: <b>${ctl}</b></span></div>`;
  }

  function cardExtra(it) {
    const p = pack();
    if (it.type === 'equip') {
      const fits = (it.fits || []).map((id) => item(id)).filter(Boolean).map((a) => a.name);
      return fits.length ? `<p class="needs fits">⚔ Passt besonders zu: ${esc(fits.join(', '))}</p>` : '';
    }
    if (it.needs) return `<p class="needs">⚠ ${esc(it.needs.text)}</p>`;
    return '';
  }

  function abilityCard(it, opts) {
    opts = opts || {};
    const p = pack();
    const t = p.types[it.type];
    const tags = (it.tags || []).map((x) => `<span class="chip">${esc(p.tags[x].name)}</span>`).join('');
    return `<article class="card ${opts.enter ? 'enter' : ''} type-${it.type}">
      <div class="card-art">${Art.abilitySVG(it, { uid: opts.uid || 'c', noSeal: true })}
        <span class="card-seal">${it.art.kanji}</span>
        <span class="type-badge" style="--tc:${t.color}">${esc(t.name)}</span>
      </div>
      <div class="card-body">
        <h2 class="card-name">${esc(it.name)}</h2>
        <div class="card-user">${it.type === 'equip' ? 'Gehörte: ' : ''}${esc(it.user)}</div>
        <p class="card-short">${esc(it.short)}</p>
        ${tags || it.hungry ? `<div class="chips">${tags}${it.hungry ? '<span class="chip hungry" title="Profitiert von viel Fluchkraft">🔥 Energiehungrig</span>' : ''}</div>` : ''}
        ${it.type === 'energy' ? energyChips(it) : ''}
        ${it.effect ? `<p class="effect">✦ ${esc(it.effect)}</p>` : ''}
        <details class="desc" ${opts.open ? 'open' : ''}>
          <summary>Beschreibung</summary>
          <p>${esc(it.desc)}</p>
          ${cardExtra(it)}
        </details>
      </div>
    </article>`;
  }

  function miniItem(id, extra) {
    const it = item(id);
    return `<button class="mini" data-action="detail" data-id="${id}">
      <span class="thumb">${art(it, 'm' + id)}</span>
      <span><b>${esc(it.name)}</b><small>${esc(pack().types[it.type].name)}${extra ? ' · ' + extra : ''}</small></span></button>`;
  }

  function renderAuction() {
    const c = state.current;
    const it = item(c.id);
    const my = state.players[me];
    const their = state.players[foe()];
    const newRound = ui.lastRound !== state.round;
    if (newRound) { ui.descOpen = false; ui.bid = null; }

    const isVow = it.type === 'vow';
    const isStorage = it.type === 'storage';
    const myTurn = c.turn === me;
    const iCanBid = myTurn && Game.canBid(state, me);
    const min = c.highBid + 1;
    let bidVal = ui.bid && ui.bid.key === c.id + ':' + c.highBid ? ui.bid.v : min;
    bidVal = Math.max(min, Math.min(my.budget, bidVal));

    let high;
    if (c.highBidder === null) high = `<div class="high-amount none">Kein Gebot</div><div class="high-who muted">Startgebot ab 1 €</div>`;
    else high = `<div class="high-amount ${ui.lastHigh !== c.id + c.highBid ? 'bump' : ''}">${c.highBid} €</div>
      <div class="high-who">Höchstgebot von <span class="${c.highBidder === me ? 'me' : 'foe'}">${c.highBidder === me ? 'dir' : esc(their.name)}</span></div>`;

    let turnHTML;
    if (iCanBid) {
      const canPass = c.highBidder !== null;
      let hint;
      if (canPass) hint = `Ablehnen = ${esc(their.name)} bekommt sie für ${c.highBid} €.`;
      else if (!Game.canBid(state, foe())) hint = 'Du bietest allein – mindestens 1 €. Willst du sie nicht, musst du skippen.';
      else hint = 'Du fängst an und musst mindestens 1 € bieten. Ablehnen geht erst, wenn jemand geboten hat.';
      turnHTML = `<div class="turn-msg mine">Du bist dran!</div>
        <div class="stepper">
          <button class="btn btn-secondary" data-action="step" data-d="-1" aria-label="weniger">−</button>
          <input id="bid-input" type="number" inputmode="numeric" min="${min}" max="${my.budget}" value="${bidVal}" aria-label="Gebot in Euro">
          <button class="btn btn-secondary" data-action="step" data-d="1" aria-label="mehr">+</button>
        </div>
        <div class="quick">
          <button class="btn btn-ghost" data-action="quick" data-v="${min}">${min} €</button>
          <button class="btn btn-ghost" data-action="quick" data-v="${Math.min(my.budget, c.highBid + 3)}">+3</button>
          <button class="btn btn-ghost" data-action="quick" data-v="${Math.min(my.budget, c.highBid + 5)}">+5</button>
          <button class="btn btn-ghost" data-action="quick" data-v="${my.budget}">Alles</button>
        </div>
        <div class="actions ${canPass ? '' : 'single'}">
          ${canPass ? '<button class="btn btn-danger" data-action="pass">Ablehnen</button>' : ''}
          <button class="btn btn-primary" data-action="bid">Bieten</button>
        </div>
        <p class="hint">${hint}</p>`;
    } else if (!Game.canBid(state, me)) {
      let why;
      if (isVow && my.vow) why = 'Du hast schon einen Binding Vow.';
      else if (isStorage && my.storage) why = 'Du hast schon einen Inventory Curse.';
      else if (my.budget < 1) why = 'Du hast kein Geld mehr.';
      else why = state.stage === 'energy' ? 'Du hast schon eine Fluchkraft.' : 'Deine Slots sind voll.';
      turnHTML = `<div class="turn-msg">${why}</div>
        <p class="hint">${esc(their.name)} bietet hier allein.${Game.stageSlots(state, me).length < state.limits[state.stage] && !isVow && !isStorage ? ' Deine leeren Slots werden am Ende zufällig gefüllt.' : ''}</p>`;
    } else {
      turnHTML = `<div class="turn-msg">${esc(their.name)} überlegt<span class="dots"></span></div>
        <p class="hint">Warte auf das Gebot von ${esc(their.name)}.</p>`;
    }

    $('#game').innerHTML = `
      <div class="players">${playerBar(me)}${playerBar(foe())}</div>
      <div class="round-info"><span>${{ abilities: 'Fähigkeiten', equipment: 'Ausrüstung', energy: 'Fluchkraft' }[state.stage]} · Karte #${state.round}</span><span>noch ${state.deck.length} im Stapel</span></div>
      ${setBoostHTML()}
      <div class="auction">
        ${abilityCard(it, { enter: newRound, open: ui.descOpen, uid: 'main' })}
        <div class="panel bidbox">
          <div class="high">${high}</div>
          ${turnHTML}
          ${specialHTML()}
          <details class="log"><summary>Verlauf</summary><ol>${state.log.slice().reverse().map((l) => `<li>${esc(l)}</li>`).join('')}</ol></details>
        </div>
      </div>`;

    ui.lastRound = state.round;
    ui.lastHigh = c.id + c.highBid;
    ui.slotCounts = [0, 1].map((p) => state.players[p].slots.length).concat([0, 1].map((p) => state.players[p].equip.length));

    const d = $('#game details.desc');
    d.addEventListener('toggle', () => (ui.descOpen = d.open));
    const inp = $('#bid-input');
    if (inp) {
      inp.addEventListener('input', () => (ui.bid = { key: c.id + ':' + c.highBid, v: Number(inp.value) }));
      inp.addEventListener('keydown', (e) => { if (e.key === 'Enter') doAction({ type: 'bid', amount: inp.value }); });
    }
  }

  // Welche Sets kommen gerade öfter? (gleiches Set bei beiden = stärker)
  function setBoostHTML() {
    const boosts = Game.setBoosts(state);
    const sets = {};
    boosts.forEach((b, p) => { if (b) (sets[b.user] = sets[b.user] || []).push(p); });
    const chips = Object.entries(sets).map(([u, ps]) => {
      const who = ps.length === 2 ? 'beide' : ps[0] === me ? 'du' : esc(state.players[ps[0]].name);
      return `<span class="setchip ${ps.length === 2 ? 'both' : ps[0] === me ? 'me' : 'foe'}" title="Weil ${who} schon Karten von ${esc(u)} ${ps.length === 2 || ps[0] !== me ? 'hat' : 'hast'}, kommen weitere davon öfter.">🎲 ${esc(u)} öfter</span>`;
    }).join('');
    return chips ? `<div class="setboost">${chips}</div>` : '';
  }

  // Skip, Sneak Peek, Final Skip
  function specialHTML() {
    const my = state.players[me];
    const their = state.players[foe()];
    const t = my.tokens;
    const pk = state.peek;
    const solo = Game.soloPhase(state) && Game.isActive(state, me);
    const what = { abilities: 'Karte', equipment: 'Ausrüstung', energy: 'Fluchkraft' }[state.stage];
    const skipWhy = Game.skipBlocked(state, me);
    const skipHint = !t.skip ? '' : skipWhy
      ? (state.current.turn === me ? `Skip gesperrt: Gebot über ${Game.SKIP_MAX_BID} €. ` : 'Skippen kannst du nur, wenn du dran bist. ')
      : `Du darfst jetzt skippen (bis ${Game.SKIP_MAX_BID} € Gebot). `;

    let peekHTML = '';
    if (pk) {
      const iSaw = pk.seen[me], theySaw = pk.seen[foe()];
      const myVote = pk.votes[me], theirVote = pk.votes[foe()];
      // Keine automatische Anfrage: erst wenn jemand, der gespickt hat, vorschlägt, kann der andere zustimmen
      let status = '', btn = '';
      if (pk.accepted) status = `<p class="peek-ok">✓ Beschlossen: Die nächste ${what} wird übersprungen.</p>`;
      else if (myVote) {
        status = `<p class="hint">${theirVote ? '' : `Du schlägst vor zu überspringen – warte, ob ${esc(their.name)} zustimmt …`}</p>`;
        btn = iSaw ? 'Vorschlag zurückziehen' : 'Zustimmung zurückziehen';
      } else if (theirVote) {
        status = `<p class="vote-badge">${esc(their.name)} hat Sneak Peek benutzt und schlägt vor, die nächste ${what} zu überspringen.</p>
          ${iSaw ? '' : `<p class="hint">Stimm blind zu – oder benutz selbst Sneak Peek${my.tokens.peek ? '' : ' (hast du aber nicht mehr)'}.</p>`}`;
        btn = iSaw ? 'Zustimmen' : 'Blind zustimmen';
      } else if (iSaw) {
        status = '<p class="hint">Willst du vorschlagen, sie zu überspringen? Dein Gegner erfährt nur davon, wenn du es vorschlägst.</p>';
        btn = `Überspringen vorschlagen`;
      } else if (theySaw) {
        status = `<p class="hint">${esc(their.name)} hat Sneak Peek benutzt 👀</p>`;
      }
      peekHTML = (iSaw || status) ? `<div class="peek">
        ${iSaw ? `<p class="eyebrow">Als Nächstes kommt</p>${miniItem(pk.id)}` : ''}
        ${status}
        ${btn ? `<button class="btn btn-secondary ${myVote ? 'voted' : ''}" data-action="peekvote">${btn}</button>` : ''}
      </div>` : '';
    }

    return `<div class="skipbox">
      <p class="eyebrow">Spezial-Aktionen</p>
      <div class="special">
        <button class="btn btn-secondary" data-action="skip" ${t.skip && !skipWhy ? '' : 'disabled'} title="Überspringt diese ${what} sofort – nur wenn du dran bist und das Gebot höchstens ${Game.SKIP_MAX_BID} € ist">⏭ Skip</button>
        <button class="btn btn-secondary" data-action="peek" ${t.peek && state.deck.length && !(pk && pk.seen[me]) ? '' : 'disabled'} title="Sieh heimlich, was als Nächstes kommt">👁 Sneak Peek</button>
        ${solo ? `<button class="btn btn-secondary glow" data-action="endskip" ${t.endskip ? '' : 'disabled'} title="Nur, wenn dein Gegner nichts mehr kaufen kann">⏩ Final Skip</button>` : ''}
      </div>
      <p class="hint">${skipHint}${solo && t.endskip ? `${esc(their.name)} kann nichts mehr kaufen – du hast einen <b>Final Skip</b>. ` : ''}Jede Aktion geht einmal${state.stages.length > 1 ? ' pro Runde' : ''}.</p>
      ${peekHTML}
    </div>`;
  }

  function renderIntermission() {
    const eq = state.stage === 'equipment';
    const rows = state.players.map((pl, p) => `<div class="inter-row ${p === me ? 'me' : 'foe'}">
      <b>${esc(pl.name)}${p === me ? ' (Du)' : ''}</b>
      <span>${eq ? `${pl.leftover} € übrig → <strong>${pl.budget} €</strong>` : `<strong>${pl.budget} €</strong> Restgeld`}</span></div>`).join('');
    $('#game').innerHTML = `<div class="inter panel">
      <p class="eyebrow">Runde ${state.stageIdx + 1}</p>
      <h2>${eq ? 'Ausrüstung' : 'Fluchkraft'}</h2>
      ${eq
        ? `<p>Euer Restgeld wird <b>verdoppelt</b>. Jeder hat jetzt <b>${state.limits.equipment} Ausrüstungs-Slots</b> – am Ende zählen nur <b>${state.equipUse}</b> davon.</p>`
        : `<p>Jetzt geht es um die <b>Fluchkraft</b> eines Charakters. Bezahlt wird mit eurem <b>Restgeld</b> (nicht verdoppelt). Jeder kann nur <b>eine</b> kaufen – wer kein Geld mehr hat, geht leer aus.</p>`}
      <div class="inter-rows">${rows}</div>
      <p class="hint">${eq
        ? 'Waffen bringen Extra-Punkte, wenn sie zu deinen Fähigkeiten oder ihrem ursprünglichen Besitzer passen. Mit dem <b>Inventory Curse</b> darfst du sogar alle 3 benutzen.'
        : 'Viel <b>Menge</b> bringt Punkte und hilft energiehungrigen Fähigkeiten 🔥. Gute <b>Kontrolle</b> gleicht Schwächen aus – z. B. „Infinity“ ohne „Six Eyes“.'}
        Skip, Sneak Peek und Final Skip sind wieder aufgeladen.</p>
      <div class="inter-bar"><span></span></div>
    </div>`;
    ui.slotCounts = [0, 1].map((p) => state.players[p].slots.length).concat([0, 1].map((p) => state.players[p].equip.length));
  }

  // ───────── Domain Clash (Sure-Hit-Timing) ─────────
  const CLASH_THEME = { void: 'stars', shrine: 'slash', shadow: 'shadow', hands: 'hands', volcano: 'ember', scale: 'gavel',
    dice: 'dice', heart: 'swords', wave: 'bubble', clock: 'frames' };
  const themeOf = (id) => CLASH_THEME[item(id).art.glyph] || 'stars';

  function particles(theme, n) {
    return Array.from({ length: n }, (_, i) => {
      const x = Math.round(Math.random() * 100), d = (Math.random() * 3).toFixed(2), sz = 6 + Math.round(Math.random() * 14);
      return `<i class="pt pt-${theme}" style="left:${x}%;top:${Math.round(Math.random() * 100)}%;animation-delay:-${d}s;--sz:${sz}px"></i>`;
    }).join('');
  }

  function clashSide(p, cls) {
    const id = state.clash.domains[p];
    const it = item(id);
    return `<div class="clash-side ${cls} theme-${themeOf(id)}" style="--c2:${it.art.c2};--c1:${it.art.c1}">
      <div class="clash-fx">${particles(themeOf(id), 26)}</div>
      <div class="clash-art">${art(it, 'cl' + p)}</div>
      <div class="clash-label"><b>${esc(it.name)}</b><span>${esc(state.players[p].name)}${p === me ? ' (Du)' : ''}</span></div>
    </div>`;
  }

  function renderClash() {
    const c = state.clash;
    if (!document.getElementById('clash') || ui.clashGame !== state.gameId) {
      ui.clashGame = state.gameId;
      ui.clash = { round: c.hits[me].length, raf: null, locked: true, timer: null };
      $('#game').innerHTML = `<div id="clash" class="clash">
        <div class="clash-scene intro">
          ${clashSide(me, 'left')}${clashSide(foe(), 'right')}
          <div class="clash-flash"></div>
          <h2 class="clash-title">DOMAIN CLASH</h2>
        </div>
        <div class="tug"><span class="tug-me"></span><b class="tug-txt"></b></div>
        <div class="panel clash-play">
          <div class="clash-round"></div>
          <div class="sh-bar"><div class="sh-zone"><div class="sh-perfect"></div></div><div class="sh-needle"></div></div>
          <p class="clash-fb">&nbsp;</p>
          <button class="btn btn-primary btn-big sh-btn" data-action="clash-hit" disabled>TREFFEN!</button>
          <p class="hint">Drück, wenn der Zeiger in deiner <b>Sure-Hit-Zone</b> ist – genau in der Mitte gibt es einen <b>BLACK FLASH</b>${c.blackFlash[me] ? ' (mit deinem „Black Flash“ besonders stark!)' : ''}. Leertaste geht auch.
            ${c.guarded[foe()] ? `<br>⚠ ${esc(state.players[foe()].name)} schützt sich mit Simple Domain – deine Treffer zählen weniger.` : ''}</p>
          <div class="clash-pips"><div><small>Du</small><span id="pips-me"></span></div><div><small>${esc(state.players[foe()].name)}</small><span id="pips-foe"></span></div></div>
        </div>
        <div class="clash-end"></div>
      </div>`;
      const half = c.zone[me] / 2;
      $('.sh-zone').style.width = (c.zone[me] * 100) + '%';
      $('.sh-perfect').style.width = ((c.perfect[me] / c.zone[me]) * 100) + '%';
      ui.clash.half = half;
      setTimeout(() => { const sc = $('.clash-scene'); if (sc) sc.classList.remove('intro'); startClashRound(); }, 2600);
    }
    updateClash();
  }

  function updateClash() {
    const c = state.clash;
    if (!$('#clash')) return;
    const a = c.points[me], b = c.points[foe()];
    const share = a + b ? (a / (a + b)) * 100 : 50;
    $('.tug-me').style.width = share + '%';
    $('.tug-txt').textContent = `${a} : ${b}`;
    const pip = (h) => `<i class="cp ${h.kind}">${h.kind === 'flash' ? '⚡' : h.kind === 'hit' ? '●' : '×'}</i>`;
    const rest = (n) => Array.from({ length: Math.max(0, c.rounds - n) }, () => '<i class="cp"></i>').join('');
    $('#pips-me').innerHTML = c.hits[me].map(pip).join('') + rest(c.hits[me].length);
    $('#pips-foe').innerHTML = c.hits[foe()].map(pip).join('') + rest(c.hits[foe()].length);
    const end = $('.clash-end');
    if (c.done) {
      cancelAnimationFrame(ui.clash && ui.clash.raf);
      const won = c.winner === me;
      $('.clash-play').classList.add('over');
      $('#clash').classList.add(won ? 'won' : 'lost');
      end.innerHTML = `<div class="panel clash-result ${won ? 'won' : 'lost'}">
        <h2>${won ? 'Du gewinnst den Domain Clash!' : `${esc(state.players[c.winner].name)} gewinnt den Domain Clash!`}</h2>
        <p>„${esc(item(c.domains[c.winner]).name)}“ setzt sich durch – alle Fähigkeiten des Siegers werden stärker, die Domain besonders${c.guarded[1 - c.winner] ? ' (durch Simple Domain etwas gebremst)' : ''}.</p>
        <button class="btn btn-primary btn-big" data-action="clash-done">Weiter zur Auswertung</button></div>`;
    } else if (c.hits[me].length >= c.rounds) {
      end.innerHTML = `<p class="hint">Du bist fertig – warte auf ${esc(state.players[foe()].name)} …</p>`;
    }
  }

  function startClashRound() {
    const c = state && state.clash;
    if (!c || state.phase !== 'clash' || !$('#clash')) return;
    const u = ui.clash;
    if (u.round >= c.rounds) { $('.clash-round').textContent = 'Fertig!'; $('.sh-btn').disabled = true; return; }
    const half = u.half;
    u.center = half + 0.04 + Math.random() * (1 - 2 * half - 0.08);
    u.speed = 0.55 + u.round * 0.2;   // Zeiger wird jede Runde schneller
    u.start = performance.now() + Math.random() * 400;
    u.locked = false;
    $('.sh-zone').style.left = ((u.center - half) * 100) + '%';
    $('.clash-round').textContent = `Runde ${u.round + 1} / ${c.rounds}`;
    $('.sh-btn').disabled = false;
    const needle = $('.sh-needle');
    const frame = (t) => {
      if (u.locked) return;
      const x = Math.max(0, (t - u.start) / 1000) * u.speed;
      u.pos = Math.abs((x % 2) - 1);
      needle.style.left = (u.pos * 100) + '%';
      u.raf = requestAnimationFrame(frame);
    };
    u.raf = requestAnimationFrame(frame);
    clearTimeout(u.timer);
    u.timer = setTimeout(() => clashPress(true), 4200); // zu lange gewartet = daneben
  }

  function clashPress(timeout) {
    const u = ui.clash;
    const c = state.clash;
    if (!u || u.locked || !c) return;
    u.locked = true;
    clearTimeout(u.timer);
    cancelAnimationFrame(u.raf);
    const offset = timeout ? 1 : Math.abs((u.pos || 0) - u.center);
    const kind = offset <= c.perfect[me] / 2 ? 'flash' : offset <= u.half ? 'hit' : 'miss';
    const fb = $('.clash-fb');
    fb.className = 'clash-fb ' + kind;
    fb.textContent = kind === 'flash' ? '⚡ BLACK FLASH! ⚡' : kind === 'hit' ? 'Sure Hit!' : timeout ? 'Zu langsam!' : 'Daneben …';
    if (kind === 'flash') { $('#clash').classList.remove('bf'); void $('#clash').offsetWidth; $('#clash').classList.add('bf'); }
    $('.sh-btn').disabled = true;
    doAction({ type: 'clashHit', round: u.round, offset });
    u.round++;
    setTimeout(startClashRound, 1000);
  }

  // ───────── Automat von Idle Death Gamble ─────────
  const REEL_SYMBOLS = ['7', '🔔', '🍒', '💎', '🎴', '🀄'];
  const OUTCOME_TEXT = {
    jackpot: { title: '🎰 JACKPOT!', text: 'Alle deine Fähigkeiten werden stärker – und deine Fluchkraft verdoppelt (ohne Fluchkraft-Runde zählen deine Domains doppelt). Der Automat stoppt.' },
    reach: { title: 'Trostpreis: REACH', text: 'Hörst du jetzt auf, werden alle deine Fähigkeiten etwas stärker. Drehst du weiter, setzt du ihn aufs Spiel.' },
    fever: { title: 'Trostpreis: FEVER', text: 'Hörst du jetzt auf, wird „Idle Death Gamble“ deutlich stärker. Drehst du weiter, setzt du ihn aufs Spiel.' },
    miss: { title: 'Nichts …', text: 'Kein Gewinn. Hörst du jetzt auf, passiert nichts. Endet dein letzter Spin so, wird alles 5 % schwächer.' },
  };

  function reelFace(outcome, seed) {
    const others = REEL_SYMBOLS.filter((x) => x !== '7' && x !== '🔔');
    const pick = (n) => others[(seed * 7 + n * 3) % others.length];
    if (outcome === 'jackpot') return ['7', '7', '7'];
    if (outcome === 'reach') return ['7', '7', pick(1)];
    if (outcome === 'fever') return ['🔔', '🔔', '🔔'];
    const a = pick(0), b = pick(2);
    return [a, b === a ? pick(4) : b, seed % 2 ? '7' : pick(5)];
  }

  function renderGamble() {
    const G = state.gamble;
    const owner = state.players[G.player];
    if (G.player !== me) {
      $('#game').innerHTML = `<div class="final"><div class="seal-box gamble-box">
        <div class="slot-lights"></div>
        <h2 class="final-title">Idle Death Gamble</h2>
        <p>🎰 ${esc(owner.name)} dreht am Automaten … <br><span class="muted">Was dabei herauskommt, bleibt bis zur Auswertung geheim.</span></p>
        <div class="inter-bar wait"><span></span></div></div></div>`;
      return;
    }
    const seen = ui.spinSeen || 0;
    const fresh = G.spins.length > seen;
    const shown = fresh ? G.spins.slice(0, seen) : G.spins;
    const last = shown[shown.length - 1];
    const face = last ? reelFace(last, shown.length) : ['?', '?', '?'];
    const info = last ? OUTCOME_TEXT[last] : null;
    const doneShown = G.done && !fresh;
    let actions;
    if (doneShown) {
      const res = G.outcome === 'jackpot' ? 'Jackpot!' : G.outcome === 'reach' ? 'Du nimmst den Trostpreis „Reach“ mit.' : G.outcome === 'fever' ? 'Du nimmst den Trostpreis „Fever“ mit.'
        : G.outcome === 'miss' ? 'Alle Spins verbraucht – alles wird 5 % schwächer.' : 'Du hast aufgehört – kein Gewinn, keine Strafe.';
      actions = `<p class="gamble-res ${G.outcome}">${res}</p><button class="btn btn-primary btn-big" data-action="gamble-done">Weiter zur Auswertung</button>`;
    } else {
      actions = `<div class="actions">
          <button class="btn btn-secondary" data-action="stop-spin" ${ui.spinning ? 'disabled' : ''}>Aufhören${last === 'reach' || last === 'fever' ? ' & Preis nehmen' : ''}</button>
          <button class="btn btn-primary" data-action="spin" ${ui.spinning || G.spinsLeft < 1 ? 'disabled' : ''}>🎰 Drehen (${G.spinsLeft} übrig)</button>
        </div>`;
    }
    $('#game').innerHTML = `<div class="final"><div class="seal-box gamble-box">
      <div class="slot-lights ${last === 'jackpot' && !fresh ? 'win' : ''}"></div>
      <h2 class="final-title">Idle Death Gamble</h2>
      <p class="muted">Nur du siehst den Automaten. ${G.total} Spins${G.total > 3 ? ' (inkl. 2 von „Rough Energy“)' : ''}.</p>
      <div class="machine"><div class="reels">${face.map((f, i) => `<div class="reel" id="reel${i}"><span>${f}</span></div>`).join('')}</div></div>
      <div class="spin-log">${G.spins.slice(0, shown.length).map((r, i) => `<span class="pip ${r}" title="Spin ${i + 1}">${i + 1}</span>`).join('')}${Array.from({ length: G.total - shown.length }, () => '<span class="pip"></span>').join('')}</div>
      ${info && !fresh ? `<div class="gamble-info ${last}"><b>${info.title}</b><p>${info.text}</p></div>` : '<div class="gamble-info"><p>Chancen pro Spin: ca. <b>15 %</b> Jackpot · <b>17 %</b> Reach · <b>13 %</b> Fever · sonst nichts.</p></div>'}
      ${actions}
    </div></div>`;
    if (fresh && !ui.spinning) animateSpin(G.spins[seen], seen + 1);
  }

  function animateSpin(outcome, n) {
    ui.spinning = true;
    renderGambleButtonsDisabled();
    const final = reelFace(outcome, n);
    const reels = [0, 1, 2].map((i) => document.querySelector('#reel' + i));
    reels.forEach((r) => r && r.classList.add('spinning'));
    const timers = reels.map((r, i) => setInterval(() => {
      if (r) r.firstElementChild.textContent = REEL_SYMBOLS[Math.floor(Math.random() * REEL_SYMBOLS.length)];
    }, 70));
    [0, 1, 2].forEach((i) => setTimeout(() => {
      clearInterval(timers[i]);
      const r = document.querySelector('#reel' + i);
      if (r) { r.classList.remove('spinning'); r.firstElementChild.textContent = final[i]; r.classList.add('stop'); }
      if (i === 2) setTimeout(() => { ui.spinning = false; ui.spinSeen = n; if (state && state.phase === 'gamble') renderGamble(); }, 450);
    }, 900 + i * 450));
  }
  function renderGambleButtonsDisabled() {
    document.querySelectorAll('[data-action=spin],[data-action=stop-spin]').forEach((b) => (b.disabled = true));
  }

  // Prison Realm: der Gegner schlägt 2 Fähigkeiten vor, der Besitzer versiegelt eine davon
  function renderSeal() {
    const sl = state.seal;
    const owner = state.players[sl.by], victim = state.players[sl.target];
    const iOwn = sl.by === me;
    let body;
    if (!sl.options && !iOwn) {
      if (!ui.sealPick) ui.sealPick = [];
      const tiles = Game.liveAbilities(state, me).map((id) => `<button class="pick ${ui.sealPick.includes(id) ? 'sac' : ''}" data-action="seal-pick" data-id="${id}">
        <span class="thumb">${art(item(id), 'sp' + id)}</span><b>${esc(item(id).name)}</b>${ui.sealPick.includes(id) ? '<em>vorgeschlagen</em>' : ''}</button>`).join('');
      body = `<p>${esc(owner.name)} benutzt <b>Prison Realm</b> gegen dich! Wähle <b>2</b> deiner Fähigkeiten – ${esc(owner.name)} versiegelt dann eine davon.</p>
        <p class="hint left">Tipp: Schlag Fähigkeiten vor, auf die du am ehesten verzichten kannst. Versiegelte Fähigkeiten zählen gar nicht – auch nicht für Kombos oder als Partner.</p>
        <div class="picks">${tiles}</div>
        <button class="btn btn-primary btn-big" data-action="seal-offer" ${ui.sealPick.length === 2 ? '' : 'disabled'}>Diese 2 vorschlagen</button>`;
    } else if (!sl.options) {
      body = `<p>Du benutzt <b>Prison Realm</b>! ${esc(victim.name)} wählt gerade 2 Fähigkeiten aus, von denen du eine versiegeln darfst …</p><div class="inter-bar wait"><span></span></div>`;
    } else if (iOwn) {
      const tiles = sl.options.map((id) => `<button class="pick" data-action="seal-choose" data-id="${id}">
        <span class="thumb">${art(item(id), 'sc' + id)}</span><b>${esc(item(id).name)}</b><em>versiegeln</em></button>`).join('');
      body = `<p>${esc(victim.name)} schlägt diese 2 Fähigkeiten vor. <b>Welche versiegelst du?</b></p><div class="picks two">${tiles}</div>`;
    } else {
      body = `<p>Du hast vorgeschlagen: <b>${sl.options.map((id) => esc(item(id).name)).join('</b> und <b>')}</b>. ${esc(owner.name)} entscheidet …</p><div class="inter-bar wait"><span></span></div>`;
    }
    $('#game').innerHTML = `<div class="final"><div class="seal-box">
      <div class="seal-cube">${art(item('gefaengnisreich'), 'cube')}</div>
      <h2 class="final-title">Prison Realm</h2>${body}</div></div>`;
  }

  // Vor der Auswertung: Bindungsschwur einsetzen / Ausrüstung wählen
  function renderFinal() {
    const my = state.players[me];
    const their = state.players[foe()];
    const allowed = Game.equipAllowed(state, me);
    if (!ui.final) ui.final = { sacrifice: null, target: null, noVow: false, equip: my.equip.slice(0, allowed) };
    const f = ui.final;
    const theirStatus = their.ready ? `${esc(their.name)} ist bereit ✓` : `${esc(their.name)} wählt noch …`;

    if (my.ready) {
      $('#game').innerHTML = `<div class="inter panel"><h2>Bereit!</h2><p>${theirStatus}</p><div class="inter-bar wait"><span></span></div></div>`;
      return;
    }

    let vowHTML = '';
    if (my.vow) {
      const tiles = my.slots.map((id) => {
        const role = f.noVow ? '' : id === f.sacrifice ? 'sac' : id === f.target ? 'tgt' : '';
        return `<button class="pick ${role}" data-action="pick-vow" data-id="${id}">
          <span class="thumb">${art(item(id), 'f' + id)}</span><b>${esc(item(id).name)}</b>
          ${role === 'sac' ? '<em>wird geopfert</em>' : role === 'tgt' ? '<em>wird verstärkt ⚡</em>' : ''}</button>`;
      }).join('');
      const step = f.noVow ? 'Du setzt den Schwur nicht ein.' : !f.sacrifice ? '1. Tippe auf die Fähigkeit, die du <b>opferst</b>.' : !f.target ? '2. Tippe auf die Fähigkeit, die <b>verstärkt</b> wird.' : 'Fertig – du kannst noch umentscheiden.';
      vowHTML = `<section class="final-sec">
        <h3>Binding Vow</h3>
        <p class="hint left">Opfere eine Fähigkeit – dafür wird eine andere viel stärker. Die geopferte zählt gar nicht mehr (auch nicht für Kombos).</p>
        <p class="step">${step}</p>
        <div class="picks ${f.noVow ? 'off' : ''}">${tiles}</div>
        <button class="btn btn-ghost small" data-action="novow">${f.noVow ? 'Schwur doch benutzen' : 'Schwur nicht benutzen'}</button>
      </section>`;
    }

    let eqHTML = '';
    if (state.mode === 'equipment' && my.equip.length > allowed) {
      const tiles = my.equip.map((id) => `<button class="pick ${f.equip.includes(id) ? 'tgt' : ''}" data-action="pick-eq" data-id="${id}">
        <span class="thumb">${art(item(id), 'e' + id)}</span><b>${esc(item(id).name)}</b>${f.equip.includes(id) ? '<em>wird benutzt</em>' : ''}</button>`).join('');
      eqHTML = `<section class="final-sec">
        <h3>Ausrüstung wählen</h3>
        <p class="hint left">Wähle genau ${allowed} von ${my.equip.length}. Tipp: Passt eine Waffe zu deinen Fähigkeiten oder ihrem Besitzer, gibt es Bonus.</p>
        <div class="picks">${tiles}</div>
      </section>`;
    }

    const vowOk = !my.vow || f.noVow || (f.sacrifice && f.target);
    const eqOk = !eqHTML || f.equip.length === allowed;
    $('#game').innerHTML = `<div class="final">
      <h2 class="final-title">Vor der Auswertung</h2>
      <div class="final-yours"><p class="eyebrow">Deine Fähigkeiten</p><div class="minis">${my.slots.map((id) => miniItem(id)).join('')}</div></div>
      ${vowHTML}${eqHTML}
      <button class="btn btn-primary btn-big" data-action="final" ${vowOk && eqOk ? '' : 'disabled'}>Bereit zur Auswertung</button>
      <p class="hint">${theirStatus}</p>
    </div>`;
  }

  function renderResult() {
    const r = state.result;
    if (!r) return;
    const order = [me, foe()];
    const a = r.scores[me].total, b = r.scores[foe()].total;
    const mineNum = Math.round((a / (a + b)) * 1000) / 10;
    const pctFmt = (n) => n.toLocaleString('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    const mine = pctFmt(mineNum);
    const theirs = pctFmt(Math.round((100 - mineNum) * 10) / 10);
    let banner, cls = '', sub;
    if (r.winner === -1) { banner = 'Unentschieden!'; sub = 'Beide Teams sind exakt gleich stark – 50 : 50.'; }
    else if (r.winner === me) { banner = 'Du gewinnst!'; sub = `Du hast mit <b>${mine} %</b> der Gesamtstärke gewonnen.`; }
    else { banner = `${esc(state.players[r.winner].name)} gewinnt!`; cls = 'lose'; sub = `Du hast mit <b>${mine} %</b> der Gesamtstärke verloren.`; }
    const diff = Math.abs(mineNum - 50) * 2;
    const verdict = r.winner === -1 ? '' : diff < 4 ? 'Hauchdünn!' : diff < 12 ? 'Knapp.' : diff < 25 ? 'Klarer Sieg.' : 'Totale Vernichtung!';

    const icons = { tag: '◆', user: '★', combo: '✦', all: '◎', counter: '⚔', vow: '⚡', equip: '🛡', energy: '🔥', debuff: '▼', copy: '⧉', duel: '⚔', jackpot: '🎰', nojackpot: '🎲' };
    const cols = order.map((p, ci) => {
      const pl = state.players[p], sc = r.scores[p];
      const ch = pl.choice || {};
      const items = pl.slots.map((id, i) => {
        const ab = item(id);
        const sub = pl.filled.includes(id) ? '<span class="rand">Zufall</span>' : `gekauft für ${pl.paid[id]} €`;
        const sealed = state.seal && state.seal.target === p && state.seal.sealed === id;
        const flags = [
          sealed ? '<div class="sacr">🔒 im Prison Realm versiegelt – zählt nicht</div>' : '',
          id === ch.sacrifice ? '<div class="sacr">✝ geopfert für den Binding Vow</div>' : '',
          id === ch.target && !sealed ? '<div class="boost">⚡ durch den Binding Vow verstärkt</div>' : '',
          id === ch.target && sealed ? '<div class="weak">⚡ Die Verstärkung durch den Binding Vow ist verloren.</div>' : '',
          sc.weakened.includes(id) ? `<div class="weak">⚠ geschwächt – ${esc(ab.needs.text)}</div>` : '',
        ].join('');
        return `<button class="ritem ${id === ch.sacrifice || sealed ? 'gone' : ''}" style="animation-delay:${(ci * 5 + i) * 60}ms" data-action="detail" data-id="${id}">
          <span class="thumb">${art(ab, 'r' + p + i)}</span>
          <span><div class="nm">${esc(ab.name)}</div><div class="sub">${esc(pack().types[ab.type].name)} · ${sub}</div>${flags}</span></button>`;
      }).join('');
      const eqItems = pl.equip.map((id, i) => {
        const used = (ch.equipUse || []).includes(id);
        const sub = pl.equipFilled.includes(id) ? '<span class="rand">Zufall</span>' : `gekauft für ${pl.paid[id]} €`;
        return `<button class="ritem ${used ? '' : 'gone'}" data-action="detail" data-id="${id}">
          <span class="thumb">${art(item(id), 're' + p + i)}</span>
          <span><div class="nm">${esc(item(id).name)}</div><div class="sub">Ausrüstung · ${sub}${used ? '' : ' · <b>nicht benutzt</b>'}</div></span></button>`;
      }).join('');
      const storageLine = pl.storage ? `<div class="vow-line storage-line">🐛 Inventory Curse – alle ${pl.equip.length} Ausrüstungen im Kampf${pl.paid[pl.storage] !== undefined ? ` (gekauft für ${pl.paid[pl.storage]} €)` : ''}</div>` : '';
      const vowLine = pl.vow ? `<div class="vow-line">📜 Binding Vow ${ch.sacrifice ? 'eingesetzt' : 'nicht eingesetzt'}${pl.paid[pl.vow] !== undefined ? ` (gekauft für ${pl.paid[pl.vow]} €)` : ''}</div>` : '';
      const BAD = ['debuff', 'nojackpot'];
      const lineHTML = (l) => `<div class="bonus-line ${BAD.includes(l.kind) ? 'bad' : ''} ${l.kind === 'jackpot' ? 'jp' : ''}" ${l.desc ? `title="${esc(l.desc)}"` : ''}><span><i class="bi">${icons[l.kind] || '+'}</i>${esc(l.label)}</span></div>`;
      const lines = sc.lines.filter((l) => !BAD.includes(l.kind)).map(lineHTML).join('');
      const badLines = sc.lines.filter((l) => BAD.includes(l.kind)).map(lineHTML).join('');
      const enItem = pl.energy[0] ? `<p class="eyebrow">Fluchkraft</p><div class="rlist"><button class="ritem" data-action="detail" data-id="${pl.energy[0]}">
          <span class="thumb">${art(item(pl.energy[0]), 'ren' + p)}</span>
          <span><div class="nm">${esc(item(pl.energy[0]).name)}</div><div class="sub">gekauft für ${pl.paid[pl.energy[0]]} €</div></span></button></div>`
        : state.energyMode ? '<p class="eyebrow">Fluchkraft</p><div class="vow-line muted">Keine Fluchkraft gekauft</div>' : '';
      return `<div class="rcol ${r.winner === p ? 'winner' : ''}">
        <h3><span>${esc(pl.name)}${p === me ? ' (Du)' : ''}</span><span class="pct">${p === me ? mine : theirs} %</span></h3>
        <div class="rlist">${items}</div>
        ${eqItems ? `<p class="eyebrow">Ausrüstung</p><div class="rlist">${eqItems}</div>` : ''}
        ${enItem}
        ${vowLine}${storageLine}
        <div class="bonus">
          <p class="eyebrow">Das hat ${p === me ? 'dein' : 'sein'} Team stärker gemacht</p>
          ${lines || '<div class="bonus-line muted"><span>Keine Boni – die Karten passen nicht zusammen.</span></div>'}
          ${badLines ? `<p class="eyebrow bad-title">Das hat ${p === me ? 'dein' : 'sein'} Team geschwächt</p>${badLines}` : ''}
        </div>
      </div>`;
    }).join('');

    const rematch = me === 0
      ? `<button class="btn btn-primary" data-action="rematch">${ui.rematchAsked ? 'Revanche annehmen' : 'Revanche'}</button>`
      : `<button class="btn btn-primary" data-action="rematch" ${ui.rematchSent === state.gameId ? 'disabled' : ''}>${ui.rematchSent === state.gameId ? 'Revanche angefragt …' : 'Revanche'}</button>`;

    $('#game').innerHTML = `
      <div class="result-banner ${cls}"><h2>${banner}</h2><p>${sub} ${verdict}</p></div>
      <div class="power">
        <div class="power-names"><span class="me">${esc(state.players[me].name)} · ${mine} %</span><span class="foe">${theirs} % · ${esc(state.players[foe()].name)}</span></div>
        <div class="power-bar"><span style="width:${mineNum}%"></span></div>
      </div>
      <div class="results">${cols}</div>
      <p class="hint">Tippe auf eine Karte für die Beschreibung. Wie stark jede Karte genau ist, bleibt geheim – das musst du selbst herausfinden!</p>
      <div class="result-actions">${rematch}<button class="btn btn-secondary" data-action="home">Zur Startseite</button></div>`;
  }

  function rulesHTML() {
    return `<div class="rules"><h2>So funktioniert's</h2><ol>
      <li>Zwei Spieler, jeder hat <b>20 €</b> und <b>5 Slots</b>.</li>
      <li>Ein <b>Münzwurf</b> entscheidet, wer bei der ersten Karte anfängt. Danach wechselt der Startspieler bei jeder Karte.</li>
      <li>Ihr bietet <b>abwechselnd</b>, kein Zeitlimit. Wer anfängt, <b>muss mindestens 1 € bieten</b>. Danach kann der andere überbieten oder <b>ablehnen</b> – dann bekommt der Höchstbietende die Karte.</li>
      <li><b>Spezial-Aktionen</b> (jede einmal):
        <br>⏭ <b>Skip</b> – überspringt die aktuelle Karte sofort, ohne Zustimmung. Geht nur, wenn <b>du dran bist</b> und das Gebot deines Gegners <b>höchstens 5 €</b> beträgt.
        <br>👁 <b>Sneak Peek</b> – du siehst heimlich die nächste Karte. Danach entscheidest du, ob du vorschlägst, sie zu überspringen. Dein Gegner kann dann selbst Sneak Peek benutzen oder blind zustimmen. Stimmen beide zu, fliegt sie raus.
        <br>⏩ <b>Final Skip</b> – kann dein Gegner nichts mehr kaufen, darfst du noch einmal skippen, egal ob du vorher schon geskippt hast.</li>
      <li>📜 <b>Binding Vow</b>: eine Spezialkarte für einen Extra-Slot. Vor der Auswertung opferst du eine Fähigkeit – dafür wird eine andere viel stärker.</li>
      <li>🎲 <b>Sets</b>: Hast du schon Karten eines Charakters (z. B. Gojo), kommen weitere Karten von ihm öfter – je mehr du hast, desto öfter. Hat dein Gegner auch welche, steigt die Chance noch mehr. Pro Spieler zählt nur ein Set: das, von dem noch die meisten Karten im Stapel sind.</li>
      <li>Leere Slots werden am Ende <b>zufällig</b> gefüllt.</li>
      <li>✦ <b>Spezial-Effekte</b>: Manche Karten wirken direkt auf den Gegner – z. B. <b>Deadly Sentencing</b> beschlagnahmt seine stärkste Fluchtechnik, <b>Cursed Speech</b> stoppt seinen stärksten Kampfskill, <b>Copy</b> kopiert einen Teil seiner stärksten Technik, <b>Boogie Woogie</b> weicht seinem stärksten Konter aus, <b>Reverse Cursed Technique</b> heilt Schwächungen, <b>Idle Death Gamble</b> lässt dich vor der Auswertung am Automaten drehen (siehe unten). Mehrere Karten desselben Charakters (Gojo, Sukuna, Yuta, Megumi …) verstärken sich gegenseitig.</li>
      <li>🎰 <b>Idle Death Gamble – Automat</b>: Wer die Karte hat, darf vor der Auswertung bis zu 3-mal drehen (mit „Rough Energy“ 5-mal) – nur er sieht den Automaten. Nach jedem Spin entscheidest du: weiter oder aufhören. <b>Jackpot</b> (ca. 15 %): alle Fähigkeiten stärker, deine Fluchkraft doppelt, die des Gegners etwas schwächer – ohne Fluchkraft-Runde zählen deine Domains doppelt. <b>Trostpreise</b> „Reach“ und „Fever“ geben kleine Boni, wenn du danach aufhörst. Hörst du bei „nichts“ auf, passiert nichts – sind aber alle Spins weg und der letzte war eine Niete, wird alles 5 % schwächer.</li>
      <li>⚔ <b>Domain Clash</b>: Haben beide eine Domain, kommt es vor der Auswertung zum Duell. 5 Runden lang saust ein Zeiger über einen Balken – drück, wenn er in deiner <b>Sure-Hit-Zone</b> ist. Je stärker deine Domain und je besser dein Team zu ihr passt, desto größer deine Zone. Genau in der Mitte gibt es einen <b>BLACK FLASH</b> (mit der Fähigkeit „Black Flash“ noch stärker). Simple Domain beim Gegner macht deine Treffer schwächer. Der Sieger bekommt Boni auf alle Fähigkeiten und besonders auf seine Domain.</li>
      <li>🧊 <b>Prison Realm</b> (Ausrüstung): Dein Gegner schlägt 2 seiner Fähigkeiten vor – du versiegelst eine davon, sie zählt dann nicht.</li>
      <li>🔥 <b>Zusatzmodus Fluchkraft-Runde</b>: Zum Schluss bietet ihr mit dem Restgeld um die Fluchkraft eines Charakters (nur eine pro Spieler). Viel <b>Menge</b> bringt Punkte und hilft energiehungrigen Fähigkeiten, gute <b>Kontrolle</b> gleicht Schwächen aus. Gojos Fluchkraft ist riesig – aber ohne Six Eyes schlecht kontrolliert.</li>
      <li><b>Modus „Mit Ausrüstung“</b>: Nach den Fähigkeiten wird dein Restgeld verdoppelt und ihr ersteigert 3 Ausrüstungen (Waffen, verfluchte Werkzeuge). Am Ende zählen 2 – mit der Spezialkarte <b>Inventory Curse</b> alle 3. Viele Ausrüstungen kontern außerdem, was dein Gegner hat (z. B. <b>Prison Realm</b> gegen Gojo, <b>Inverted Spear of Heaven</b> gegen Fluchtechniken). Passt eine Ausrüstung zu deinen Fähigkeiten oder ihrem ursprünglichen Besitzer, gibt es Bonus.</li>
      <li>Jede Karte hat einen <b>geheimen Wert</b>. Dazu kommen Boni für gleiche <b>Klassen</b>, gleichen <b>Charakter</b>, <b>Kombos</b>, <b>Allrounder</b> und <b>Konter</b>. Manche Fähigkeiten brauchen einen <b>Partner</b> (z. B. Unendlichkeit + Sechs Augen) – lies die Beschreibungen!</li>
      <li>Am Ende siehst du, mit wie viel Prozent der Gesamtstärke du gewonnen oder verloren hast.</li>
    </ol></div>`;
  }

  // ───────── Klicks ─────────
  document.addEventListener('click', (e) => {
    const el = e.target.closest('[data-action]');
    if (!el) {
      if (e.target.id === 'modal' || e.target.closest('.modal-close')) closeModal();
      return;
    }
    const act = el.dataset.action;
    const inp = $('#bid-input');
    if (act === 'step' && inp) {
      const v = Math.max(+inp.min, Math.min(+inp.max, (Number(inp.value) || 0) + Number(el.dataset.d)));
      inp.value = v; inp.dispatchEvent(new Event('input'));
    } else if (act === 'quick' && inp) {
      inp.value = Math.max(+inp.min, Number(el.dataset.v)); inp.dispatchEvent(new Event('input'));
    } else if (act === 'bid' && inp) {
      doAction({ type: 'bid', amount: inp.value });
    } else if (['pass', 'skip', 'endskip', 'peek', 'peekvote'].includes(act)) {
      doAction({ type: act });
    } else if (act === 'pick-vow' && ui.final) {
      const f = ui.final, id = el.dataset.id;
      f.noVow = false;
      if (id === f.sacrifice) f.sacrifice = null;
      else if (id === f.target) f.target = null;
      else if (!f.sacrifice) f.sacrifice = id;
      else f.target = id;
      renderFinal();
    } else if (act === 'novow' && ui.final) {
      ui.final.noVow = !ui.final.noVow;
      renderFinal();
    } else if (act === 'pick-eq' && ui.final) {
      const f = ui.final, id = el.dataset.id;
      if (f.equip.includes(id)) f.equip = f.equip.filter((x) => x !== id);
      else if (f.equip.length < Game.equipAllowed(state, me)) f.equip.push(id);
      else { f.equip.shift(); f.equip.push(id); }
      renderFinal();
    } else if (act === 'seal-pick') {
      const id = el.dataset.id;
      ui.sealPick = ui.sealPick || [];
      if (ui.sealPick.includes(id)) ui.sealPick = ui.sealPick.filter((x) => x !== id);
      else { ui.sealPick.push(id); if (ui.sealPick.length > 2) ui.sealPick.shift(); }
      renderSeal();
    } else if (act === 'clash-hit') {
      clashPress(false);
    } else if (act === 'clash-done') {
      doAction({ type: 'clashDone' });
    } else if (act === 'spin' && !ui.spinning) {
      doAction({ type: 'spin' });
    } else if (act === 'stop-spin' && !ui.spinning) {
      doAction({ type: 'stopSpin' });
    } else if (act === 'gamble-done') {
      doAction({ type: 'gambleDone' });
    } else if (act === 'seal-offer') {
      doAction({ type: 'sealOptions', ids: ui.sealPick || [] });
    } else if (act === 'seal-choose') {
      doAction({ type: 'seal', id: el.dataset.id });
    } else if (act === 'final' && ui.final) {
      const f = ui.final;
      doAction({ type: 'final', sacrifice: f.noVow ? null : f.sacrifice, target: f.noVow ? null : f.target, equipUse: f.equip });
    } else if (act === 'detail') {
      const it = item(el.dataset.id);
      if (it) openModal(abilityCard(it, { open: true, uid: 'modal' }));
    } else if (act === 'rematch') {
      if (me === 0) startGame();
      else { net && net.send({ t: 'rematch' }); ui.rematchSent = state.gameId; render(); }
    } else if (act === 'home') {
      location.href = location.pathname;
    }
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
    if (e.code === 'Space' && state && state.phase === 'clash' && ui.clash && !ui.clash.locked) { e.preventDefault(); clashPress(false); }
  });

  // Testmodus (nur mit ?debug in der Adresse): Spielstand lokal laden, ohne Online-Verbindung
  if (new URLSearchParams(location.search).has('debug')) {
    window.__fa = {
      load(s, asPlayer) { state = s; me = asPlayer || 0; net = net || { send() {} }; ui.gameId = null; render(); },
      get state() { return state; },
    };
  }

  window.addEventListener('beforeunload', (e) => {
    if (state && ['auction', 'intermission', 'final', 'seal', 'gamble', 'clash'].includes(state.phase)) { e.preventDefault(); e.returnValue = ''; }
  });
})();
