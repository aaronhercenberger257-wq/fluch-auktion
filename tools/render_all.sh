#!/bin/bash
# Rendert ALLE Videos neu (läuft viele Stunden, am besten über Nacht):
#   bash tools/render_all.sh [ordner-für-einzelbilder] [parallel]
# Domain-Videos: ein Video pro Domain → video/<szene>.mp4 (SKINVARIANTS=1: 9 Varianten mit Gegner-Skins,
#   video/<szene>__<gegner>.mp4). Bilder 61–190 (nur der Sieger im Bild) werden pro Domain einmal gerendert und geteilt.
# Dazu: Finger-, Resonanz- und Hakari-Clips (NOCLIPS=1 überspringt sie, SCENES="a b" wählt Szenen).
P="$(cd "$(dirname "$0")/.." && pwd)"
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
F="${1:-$P/../render_frames}"
PAR="${2:-3}"
cd "$P"
mkdir -p "$F"
node tools/sfx/soundtrack.mjs > /dev/null

declare -A OWNER=([void]=gojo [shrine]=sukuna [shadow]=megumi [hands]=mahito [volcano]=jogo [court]=higuruma
                  [gamble]=hakari [swords]=yuta [beach]=dagon [frames]=naoya)
SCENES=(${SCENES:-shrine void gamble swords court volcano shadow beach frames hands})   # z. B. SCENES="void shrine" bash …
SKINS=(gojo sukuna megumi mahito jogo higuruma hakari yuta dagon naoya)
SHARED=$(seq -s, 61 190)
OWN=$( (seq 1 60; seq 191 432) | paste -sd, -)

mux() {  # mux <ordner> <video-name> <ton-name>
  ffmpeg -loglevel error -y -framerate 24 -i "$1/frame_%04d.png" -i "tools/sfx/tracks/$3.wav" -c:v libx264 -crf 23 -pix_fmt yuv420p \
    -c:a aac -shortest -movflags +faststart "video/$2.mp4" && echo "OK $2 ($(ls "$1" | wc -l) Bilder)" || echo "FEHLER $2"
}
shared() {   # shared <szene>: die Bilder ohne Gegner einmal rendern
  d="$F/${1}__shared"; mkdir -p "$d"
  [ "$(ls "$d" | wc -l)" -ge 130 ] || "$B" -b --factory-startup -P blender/scenes.py -- "$1" preview "$d" "$SHARED" > "$d.log" 2>&1
  echo "GETEILT $1"
}
variant() {  # variant <szene> <gegner>
  name="${1}__$2"; [ "$2" = foe ] && name="$1"   # Standard-Gegner → video/<szene>.mp4
  d="$F/$name"; mkdir -p "$d"
  [ -s "video/$name.mp4" ] && { echo "SCHON DA $name"; return; }
  "$B" -b --factory-startup -P blender/scenes.py -- "$1" preview "$d" "$OWN" "foe=$2" > "$d.log" 2>&1
  while [ ! -f "$F/${1}__shared.done" ]; do sleep 10; done
  cp "$F/${1}__shared/"frame_*.png "$d/"
  mux "$d" "$name" "$1" && rm -rf "$d"   # Einzelbilder löschen (Platz sparen)
}
clip() {     # clip <name> <blender-argumente…>
  n="$1"; shift
  d="$F/$n"; mkdir -p "$d"
  "$B" -b --factory-startup -P blender/extras.py -- "$@" "$d" > "$d.log" 2>&1
  mux "$d" "$n" "$n" && rm -rf "$d"
}

JOBS=()
[ -n "$NOCLIPS" ] || JOBS=("CLIP finger_1 finger 1 full" "CLIP finger_2 finger 2 full" "CLIP finger_3 finger 3 full" "CLIP resonance resonance full"
      "CLIP hakari_spin spin full")
for sc in "${SCENES[@]}"; do
  JOBS+=("SHARED $sc")
  if [ -n "$SKINVARIANTS" ]; then
    for sk in "${SKINS[@]}"; do [ "$sk" != "${OWNER[$sc]}" ] && JOBS+=("VAR $sc $sk"); done
  else
    JOBS+=("VAR $sc foe")   # Standard: ein Video pro Domain mit dem Fluch-Krieger als Gegner
  fi
done

for j in "${JOBS[@]}"; do
  while [ "$(jobs -rp | wc -l)" -ge "$PAR" ]; do sleep 5; done
  set -- $j
  case "$1" in
    SHARED) ( shared "$2"; touch "$F/${2}__shared.done" ) & ;;
    VAR) variant "$2" "$3" & ;;
    CLIP) shift; clip "$@" & ;;
  esac
done
wait
echo ALLDONE
