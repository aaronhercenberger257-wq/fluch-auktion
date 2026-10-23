# Fluch-Auktion – Projektgedächtnis

2-Spieler-Online-Browserspiel nach dem TikTok-Trend „$20 Draft“ mit Jujutsu-Kaisen-Fähigkeiten.
Nutzer: Aaron, schreibt Deutsch (oft mit Tippfehlern), Anfänger beim Programmieren → einfach und auf Deutsch erklären,
Schritt-für-Schritt-Anleitungen mit genauen Klicks. Er will Qualität („wie ein echter Anime“), nichts selbst bauen müssen
(VRoid abgelehnt), keine Konten bei KI-Diensten (IMG.LY abgelehnt), nichts bezahlen.

## Wo & wie es läuft
- Live: **https://aaronhercenberger257-wq.github.io/fluch-auktion/** (GitHub Pages, kostenlos)
- Repo: `aaronhercenberger257-wq/fluch-auktion`, Branch `main`. Dieser Ordner ist das Git-Repo.
- **Updates hochladen: ich selbst** per `git add -A && git commit && git push origin main` (Login über Git Credential
  Manager ist eingerichtet, Nutzer hat das gewünscht). Danach 1–2 Min warten, mit curl prüfen, ob online.
- Commit-Autor: `aaronhercenberger257-wq <aaronhercenberger257-wq@users.noreply.github.com>` (repo-lokal gesetzt).
- Altes Netlify-Projekt (luxury-blini-9e5fda) nicht mehr benutzen (Credits).
- Lokal testen: `.claude/launch.json` → Server „fluch-auktion“ (Port 8137). Testmodus: `?debug` in der URL →
  `window.__fa.load(state, spieler)` lädt einen Spielstand ohne Online-Verbindung.

## Dateien
- `index.html`, `style.css`, `cinematic.css`
- `js/packs/jjk.js` – alle Karten (48 Fähigkeiten, 2 Binding Vows, 17 Ausrüstungen inkl. Inventory Curse,
  11 Fluchkraft-Karten), Kombos, Konter, Effekte, Set-Synergien, Werte. **Namen englisch, Texte deutsch.**
- `js/game.js` – Regeln (Host rechnet, Gast bekommt den Zustand). Phasen:
  coin → auction (Fähigkeiten) → [intermission → auction Ausrüstung] → [intermission → auction Fluchkraft]
  → [final: Binding Vow / Ausrüstung wählen] → [seal: Prison Realm] → [ritual: Mahoraga] → [gamble: Idle Death Gamble]
  → [clash: Domain Clash] → result
- `js/main.js` – Oberfläche aller Phasen; `js/net.js` – Online über öffentliche MQTT-Broker (emqx, mosquitto, hivemq),
  Raum-Code 5 Zeichen; `js/art.js` – SVG-Kartenbilder; `js/cinematic.js` – Videos/Animationen nach dem Clash
- `blender/` – 3D-Animationen: `animelib.py` (Toon-Shader, Umrisse, Kamera), `chars.py` (Figuren: Skin-Modifier-Körper,
  Rig, Anime-Kopf, Strähnen-Haare), `cast.py` (alle Domain-Besitzer + Gegner), `scenes.py` (10 Domains),
  `mahoraga.py` (Beschwörung win/lose), `lineup.py`/`posetest.py`/`mahotest.py` (Testbilder)
- `tools/sfx/synth.mjs` (aus dem Roblox-Projekt kopiert) + `tools/sfx/soundtrack.mjs` (Tonspuren aller Videos)
- `video/*.mp4` – fertige Videos (Domains je 18 s, Mahoraga je 9 s, mit Ton)

## Spielregeln (vom Nutzer festgelegt)
- 2 Spieler, je 20 €, 5 Slots. Münzwurf → Startspieler, danach wechselt der Starter je Karte.
- Bieten abwechselnd, kein Zeitlimit, Betrag frei. Starter muss ≥ 1 € bieten; Ablehnen erst nach einem Gebot.
- Spezial-Aktionen je 1× (pro Runde): **Skip** (nur wenn man dran ist und Gebot ≤ 5 €), **Sneak Peek** (nächste Karte
  sehen, dann selbst entscheiden ob Skip vorschlagen; gegen vollen Gegner sofortiger Skip; mit vollen Slots gesperrt),
  **Final Skip** (nur wenn der Gegner nichts mehr kaufen kann).
- Leere Slots am Ende zufällig (nicht bei Fluchkraft). Nur eine Domain pro Spieler; haben beide eine, keine mehr versteigert.
- Werte sind **geheim**; Ergebnis zeigt nur Prozent der Gesamtstärke + welche Boni/Schwächungen gewirkt haben.
- Set-Chancen: eigenes Set (Charakter mit den meisten Restkarten) kommt öfter.
- Partner-Abhängigkeiten (z. B. Infinity braucht Six Eyes), Kombos, Klassen, Charakter-Synergie, Konter, Allrounder,
  Effekte (Deadly Sentencing, Cursed Speech, Copy, Boogie Woogie, Reverse Cursed Technique), Domain-Boost +12 wenn nur
  einer eine Domain hat.
- Modi: Klassisch / Mit Ausrüstung (Restgeld ×2, 3 Slots, 2 zählen) / + Fluchkraft-Runde (Restgeld, 1 Karte).
- Prison Realm versiegelt eine gegnerische Fähigkeit (Gegner schlägt 2 vor). Idle Death Gamble = Automat (3 Spins,
  +2 mit Rough Energy; Jackpot ~15 %, Reach, Fever, Niete −5 %). Mahoraga ohne Ten Shadows: beschwören (Chance nach
  Grundwerten 10–90 %; Sieg = volle Punkte, Niederlage = 0 + alle −15 %) oder halbe Punkte.
- Domain Clash (beide haben Domain): 5 Runden Sure-Hit-Timing, Black Flash in der Zonenmitte, danach 3D-Siegesvideo.

## Animationen & Sounds neu erzeugen
- Domain: `"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/scenes.py -- <void|shrine|shadow|hands|volcano|court|gamble|swords|beach|frames> preview|full <ordner>`
- Mahoraga: `... -P blender/mahoraga.py -- win|lose preview|full <ordner>`
- Vorschau-Bilder zu Übersichtsbild: ffmpeg `concat:` + `tile`. Immer erst preview ansehen, dann full.
- Tonspuren: `node tools/sfx/soundtrack.mjs` → `tools/sfx/tracks/*.wav` (nicht versioniert).
- Muxen: `ffmpeg -framerate 24 -i <ordner>/frame_%04d.png -i tools/sfx/tracks/<name>.wav -c:v libx264 -crf 23 -pix_fmt yuv420p -c:a aac -shortest -movflags +faststart video/<name>.mp4`
- Szenen werden mit 288 Bildern gebaut und auf 432 (18 s) gestreckt (`retime`); Schrift-Zeitpunkte in `js/cinematic.js` (CUES).
- Keine echten Anime-Bilder ins Spiel übernehmen (Urheberrecht) – Vorlagen nur als Referenz.

## Offene Ideen / nächste Schritte
- Nutzer soll die Videos/Sounds anschauen und Feedback geben (Sounds nur gemessen, nicht gehört).
- Mögliche Erweiterungen: weitere Anime-Pakete (One Piece, Naruto), Charaktere statt Fähigkeiten, Anime mischen,
  Rangliste über Revanchen, noch detailreichere Figuren/Animationen.
