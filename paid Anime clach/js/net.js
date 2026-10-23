// Online-Verbindung über öffentliche MQTT-Vermittlungs-Server (kostenlos, ohne Konto).
// Die Nachrichten laufen über einen Server statt direkt von Gerät zu Gerät –
// dadurch klappt es auch mit Handy-Internet, VPN oder strengen Routern.
// Host = Raum-Ersteller (Spieler 1), Gast = Spieler 2.

(function () {
  const BROKERS = [
    'wss://broker.emqx.io:8084/mqtt',
    'wss://test.mosquitto.org:8081/mqtt',
    'wss://broker.hivemq.com:8884/mqtt',
  ];
  const ROOT = 'fluch-auktion-v1/';
  const CODE_CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  const PING_MS = 3000;
  const LOST_MS = 15000;

  const makeCode = () => Array.from({ length: 5 }, () => CODE_CHARS[Math.floor(Math.random() * CODE_CHARS.length)]).join('');
  const makeId = () => Math.random().toString(36).slice(2, 10);
  const topics = (code) => ({ toHost: ROOT + code + '/h', toGuest: ROOT + code + '/g' });

  function connect(url, will) {
    return mqtt.connect(url, { connectTimeout: 7000, reconnectPeriod: 2000, clean: true, will });
  }

  function parse(buf) {
    try { return JSON.parse(buf.toString()); } catch (e) { return null; }
  }

  // Gemeinsam: Nummerierung gegen doppelte Nachrichten + Lebenszeichen
  function link(handlers) {
    const l = { seq: 0, lastIn: 0, seen: Date.now(), closed: false, timer: null };
    l.accept = (env) => {
      l.seen = Date.now();
      if (typeof env.n === 'number') {
        if (env.n <= l.lastIn) return false;
        l.lastIn = env.n;
      }
      return true;
    };
    l.startWatch = (sendPing) => {
      l.seen = Date.now();
      clearInterval(l.timer);
      l.timer = setInterval(() => {
        sendPing();
        if (Date.now() - l.seen > LOST_MS) l.close();
      }, PING_MS);
    };
    l.close = () => {
      if (l.closed) return;
      l.closed = true;
      clearInterval(l.timer);
      handlers.onClose();
    };
    return l;
  }

  // handlers: onOpen(code), onGuest(), onMessage(msg), onClose(), onError(text)
  function host(handlers) {
    const code = makeCode();
    const t = topics(code);
    const l = link(handlers);
    let opened = false;
    let guest = null; // { id, client }

    const net = {
      role: 'host',
      code,
      send(m) {
        if (!guest) return;
        guest.client.publish(t.toGuest, JSON.stringify({ to: guest.id, n: ++l.seq, m }), { qos: 1 });
      },
    };

    const clients = BROKERS.map((url) => {
      const c = connect(url, { topic: t.toGuest, payload: JSON.stringify({ to: '*', m: { t: 'bye' } }), qos: 1 });
      c.on('connect', () => {
        c.subscribe(t.toHost, { qos: 1 });
        if (!opened) { opened = true; handlers.onOpen(code); }
      });
      c.on('message', (_topic, buf) => {
        const env = parse(buf);
        if (!env || !env.id || !env.m) return;
        const m = env.m;
        if (m.t === 'knock') {
          if (!guest || guest.id === env.id) {
            const isNew = !guest;
            guest = { id: env.id, client: c };
            c.publish(t.toGuest, JSON.stringify({ to: env.id, m: { t: 'welcome' } }), { qos: 1 });
            if (isNew) {
              l.startWatch(() => net.send({ t: 'ping' }));
              handlers.onGuest();
            }
          } else {
            c.publish(t.toGuest, JSON.stringify({ to: env.id, m: { t: 'full' } }), { qos: 1 });
          }
          return;
        }
        if (!guest || env.id !== guest.id || !l.accept(env)) return;
        if (m.t === 'bye') return l.close();
        if (m.t === 'ping') return;
        handlers.onMessage(m);
      });
      return c;
    });

    setTimeout(() => {
      if (!opened) handlers.onError('Keine Verbindung zum Server. Prüfe dein Internet und versuch es nochmal.');
    }, 12000);

    window.addEventListener('pagehide', () => {
      if (guest) guest.client.publish(t.toGuest, JSON.stringify({ to: guest.id, m: { t: 'bye' } }));
      clients.forEach((c) => c.end(true));
    });
    return net;
  }

  function join(code, handlers) {
    code = code.toUpperCase();
    const t = topics(code);
    const id = makeId();
    const l = link(handlers);
    let client = null;
    let welcomed = false;

    const net = {
      role: 'guest',
      code,
      send(m) {
        if (client) client.publish(t.toHost, JSON.stringify({ id, n: ++l.seq, m }), { qos: 1 });
      },
    };

    // Server nacheinander probieren, bis der Host antwortet
    function tryBroker(i) {
      if (welcomed) return;
      if (i >= BROKERS.length) {
        handlers.onError('Raum nicht gefunden. Stimmt der Code? Ist der Raum-Ersteller noch auf der Seite?');
        return;
      }
      const c = connect(BROKERS[i], { topic: t.toHost, payload: JSON.stringify({ id, m: { t: 'bye' } }), qos: 1 });
      let knockTimer = null;
      const giveUp = setTimeout(() => {
        if (welcomed) return;
        clearInterval(knockTimer);
        c.end(true);
        tryBroker(i + 1);
      }, 7000);

      c.on('connect', () => {
        c.subscribe(t.toGuest, { qos: 1 }, () => {
          const knock = () => c.publish(t.toHost, JSON.stringify({ id, m: { t: 'knock' } }), { qos: 1 });
          knock();
          clearInterval(knockTimer);
          knockTimer = setInterval(knock, 1500);
        });
      });
      c.on('message', (_topic, buf) => {
        const env = parse(buf);
        if (!env || !env.m || (env.to !== id && env.to !== '*')) return;
        const m = env.m;
        if (m.t === 'welcome') {
          clearInterval(knockTimer);
          clearTimeout(giveUp);
          if (!welcomed) {
            welcomed = true;
            client = c;
            l.startWatch(() => net.send({ t: 'ping' }));
            handlers.onOpen(code);
          }
          return;
        }
        if (m.t === 'full') {
          clearInterval(knockTimer);
          clearTimeout(giveUp);
          c.end(true);
          handlers.onMessage({ t: 'full' });
          return;
        }
        if (c !== client || !l.accept(env)) return;
        if (m.t === 'bye') return l.close();
        if (m.t === 'ping') return;
        handlers.onMessage(m);
      });
    }
    tryBroker(0);

    window.addEventListener('pagehide', () => {
      if (client) client.publish(t.toHost, JSON.stringify({ id, m: { t: 'bye' } }));
    });
    return net;
  }

  window.Net = { host, join };
})();
