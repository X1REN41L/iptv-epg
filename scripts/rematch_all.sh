#!/bin/bash
# Re-match every nvision live channel to a guide by name: rewrites work/nvision_all_map.tsv, then refreshes the guide.
# Channel list comes from Lineup's cached `main` playlist. A failed download or match keeps the current map.
# usage: bash ~/workspace/iptv-epg/scripts/rematch_all.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIVE="$HOME/workspace/lineup-iptv-player/data/playlists/main/playlist.json"
TMP=$(mktemp -d "$ROOT/epg_all.XXXXXX") || exit 1
trap 'rm -rf "$TMP"' EXIT
SRC="$TMP/src"; mkdir "$SRC" || exit 1

get() {  # output name (epg_ripper_<KEY>.xml.gz), url
  ( curl -sSfL -m 300 -o "$SRC/$1" "$2" && gzip -t "$SRC/$1" ) || { echo "download FAILED: $1"; touch "$TMP/failed"; }
}
skip='US_LOCALS1|ALL_SOURCES1|RAKUTEN1|PLEX1|DUMMY_CHANNELS|DISTROTV1|WHALETVPLUS1|AUDACY1|DRAFTKINGS1|MUSICBOX1|TBNPLUS1|VOA1|PEACOCK1'
files=$(curl -sS -m 60 https://epgshare01.online/epgshare01/ | grep -oE 'epg_ripper_[A-Z0-9_]+\.xml\.gz' | sort -u | grep -vE "_($skip)\.xml")
[ -n "$files" ] || { echo "source listing FAILED, map kept"; exit 1; }
for f in $files; do get "$f" "https://epgshare01.online/epgshare01/$f" & done
get epg_ripper_IPTVX.xml.gz https://iptvx.one/EPG_LITE &
get epg_ripper_IT999.xml.gz http://epg.it999.ru/edem.xml.gz &
wait
[ ! -e "$TMP/failed" ] || { echo "rematch aborted, map kept"; exit 1; }

python3 -I - "$LIVE" "$TMP/live.tsv" <<'PY' || { echo "channel list FAILED, map kept"; exit 1; }
import json, sys
p = json.load(open(sys.argv[1], encoding='utf-8'))
cats = {c['id']: c['name'] for c in p['categories']}
with open(sys.argv[2], 'w', encoding='utf-8') as w:
    for c in p['channels']:
        for k in c['cats']:
            w.write('%s\t%s\t%s\n' % (c['sid'], cats.get(k, ''), c['name']))
PY
python3 -I "$ROOT/scripts/index_all_src.py" "$SRC" "$TMP/index.json" >/dev/null \
  && python3 -I "$ROOT/scripts/match_all_channels.py" "$TMP/live.tsv" "$TMP/index.json" "$ROOT/work/nvision_overrides.tsv" "$TMP/all_map.tsv" \
  && [ -s "$TMP/all_map.tsv" ] && mv "$TMP/all_map.tsv" "$ROOT/work/nvision_all_map.tsv" \
  || { echo "match FAILED, map kept"; exit 1; }

bash "$ROOT/scripts/refresh_fav_epg.sh"
