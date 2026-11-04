#!/bin/bash
# Save one frame per nvision live stream to OUT_DIR/<id>.jpg, one connection at a time.
# usage: grab_frames.sh OUT_DIR XTREAM_ID...   (credentials read from Lineup's settings, never printed)
out=$1; shift; mkdir -p "$out"
IFS=$'\t' read -r SRV USR PWD < <(python3 -I -c "
import json, os
s = next(p for p in json.load(open(os.path.expanduser('~/workspace/lineup-iptv-player/data/settings.json')))['playlists'] if p['id'] == 'main')['source']
print(s['server'], s['username'], s['password'], sep='\t')")
for id in "$@"; do
  ffmpeg -v error -y -rw_timeout 15000000 -i "$SRV/live/$USR/$PWD/$id.ts" -ss 3 -frames:v 1 -vf scale=960:-2 "$out/$id.jpg" 2>&1 \
    | sed "s#$USR#***#g; s#$PWD#***#g" | head -2
  echo "$id $(date -u +%H:%M:%SZ) $( [ -s "$out/$id.jpg" ] && echo ok || echo FAIL)"
done
