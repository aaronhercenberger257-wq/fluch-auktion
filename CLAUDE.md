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
  → [final: Binding Vow / Ausrüstung wählen] → [seal: Prison Realm] → [ritual: Mahoraga] → [gamble: Idle Death Gamble, beide sehen zu]
  → [feast: Sukunas Finger, Glücksrad 1–3] → [resonance: Nobara] → [verdict: Waage von Deadly Sentencing] → [clash: Domain Clash] → result
- `js/main.js` – Oberfläche aller Phasen; `js/net.js` – Online über öffentliche MQTT-Broker (emqx, mosquitto, hivemq),
  Raum-Code 5 Zeichen; `js/art.js` – SVG-Kartenbilder; `js/cinematic.js` – Videos/Animationen nach dem Clash
- `blender/` – 3D-Animationen: `animelib.py` (Toon-Shader, Umrisse, Freestyle-Tusche `ink()` für Sammlung „Ink“, Kamera),
  `chars.py` (Figuren v2: Skin-Körper + Rig, geloftete Kleidung, modellierte Hände mit Fingern + Haltungen `hand_switch`,
  Anime-Schädel, Gesicht als aufprojizierte Decals = Augen/Brauen/Mund/Tattoos/Nähte, Haarbüschel), `cast.py` (alle Figuren nach
  Nutzer-Vorlagen: Gojo mit Binde, Sukuna Kimono, Jogo Vulkankopf, Mahito Poncho, Megumi, Mahoraga u. a.), `scenes.py` (10 Domains;
  Shrine/Volcano/Hands nach Vorlagen neu), `fight.py` (Kampf-Posen), `mahoraga.py` (Beschwörung + Kampf win/lose, 15,5 s),
  `extras.py` (Waage-Clips verdict_<up3…down3|exec> 9 s, Hakari-Hebel-Clip hakari_spin 2,5 s, finger_<1|2|3> 7 s,
  resonance 9 s; Nobara-Figur + Finger-Modell in cast.py),
  Testbilder: `lineup.py -- <out.png> gojo,sukuna,…` (Ganzkörper + Gesicht je Figur), `posetest.py -- <ordner> <figur>`
- `tools/simulate.js` – Regel-Simulation (`node tools/simulate.js 600`): Zufallspartien + gezielte Tests (Waage, RCT)
- `tools/sfx/synth.mjs` (aus dem Roblox-Projekt kopiert) + `tools/sfx/soundtrack.mjs` (Tonspuren aller Videos)
- `video/*.mp4` – fertige Videos mit Ton: Domains `<szene>.mp4` (18 s, Gegner immer der Fluch-Krieger – Nutzer wollte
  KEINE 9 Gegner-Skin-Varianten, zu lange Renderzeit), Mahoraga 15,5 s, Waage-, Finger-, Resonanz- und Hakari-Clips.
- `tools/render_all.sh [bilder-ordner] [parallel]` – rendert alle Domain-Videos + Clips neu (einige Stunden); NOCLIPS=1,
  SCENES="a b" wählen aus; SKINVARIANTS=1 wäre die abgelehnte 90-Video-Variante.

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
  +2 mit Rough Energy; Jackpot ~11 %, Reach, Fever, Niete −5 %). Mahoraga ohne Ten Shadows: beschwören (Chance nach
  Grundwerten 10–90 %; Sieg = volle Punkte, Niederlage = 0 + alle −15 %) oder halbe Punkte.
- Waage (Deadly Sentencing): jede Karte hat `karma` (+ böse, − gut, auf der Karte nur als Gesinnung). Summe des Gegners →
  Stufe −3…+3 (Schwellen 3/8/13). +1 DS-Domain +25 %, +2 alles +12 %, +3 mit Executioner's Sword: Clash ohne Kampf gewonnen +
  Gegner halbiert; +3 ohne Schwert: alles +25 %, Black Flash +8 Punkte, eine Sache versiegeln (keine Domain). Schuldig →
  stärkste Fluchtechnik beschlagnahmt. −1/−2/−3: Gegner +6/+12/+15 %, bei −3 zählt seine Domain ≥ 2× DS-Domain.
- Reverse Cursed Technique: verwandte Karten (pack.rct.linked: Red, Purple, Infinity, Idle Death Gamble, Rika) +12 % und
  alle Schwächungen aufgehoben.
- Sukunas Finger: Shrine + Dismantle & Cleave + Fuga + Finger (Ausrüstung) → Glücksrad 1/2/3 Finger (50/33/17 %),
  je Finger Sukuna-Techniken +12 % und +12 Punkte. Resonanz: Straw Doll + Hammer & Nails + Finger → Sukuna-Techniken des
  Gegners ×0,5. Fluchkraft-Modus: wer am Ende keine Fluchkraft hat, bekommt eine zufällige.
- Domain Clash (beide haben Domain): 5 Runden Sure-Hit-Timing, Black Flash in der Zonenmitte, danach 3D-Siegesvideo.

## Animationen & Sounds neu erzeugen
- Domain: `"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup -P blender/scenes.py -- <void|shrine|shadow|hands|volcano|court|gamble|swords|beach|frames> preview|full <ordner> [bilder] [foe=<figur>]`
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
