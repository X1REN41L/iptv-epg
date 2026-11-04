#!/bin/bash
# Manual refresh of the nvision guide: all name-matched channels (auto map) plus the overrides,
# today .. day after tomorrow, original language.
# usage: bash ~/workspace/iptv-epg/scripts/refresh_fav_epg.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/out/premium_nvision_epg.xml.gz"
mkdir -p "$ROOT/out" && TMP=$(mktemp -d "$ROOT/epg_fav.XXXXXX") || exit 1
trap 'rm -rf "$TMP"' EXIT

MAP="$TMP/map.tsv"
cat "$ROOT/work/nvision_overrides.tsv" "$ROOT/work/nvision_all_map.tsv" > "$MAP" || exit 1
files=$(cut -f3 "$MAP" | grep -v '^#\|^candidate' | grep -oE '(^|,)[A-Z0-9_]+:' | tr -d ',:' | sort -u)
echo "downloading: $(echo $files)"
for c in $files; do
  f="epg_ripper_$c.xml.gz"
  # IPTVX comes from iptvx.one (lite), IT999 from epg.it999.ru, the rest from epgshare01
  case $c in
    IPTVX) url="https://iptvx.one/EPG_LITE" ;;
    IT999) url="http://epg.it999.ru/edem.xml.gz" ;;
    *) url="https://epgshare01.online/epgshare01/$f" ;;
  esac
  ( curl -sSfL -m 180 -o "$TMP/$f" "$url" && gzip -t "$TMP/$f" ) \
    || { echo "download FAILED: $f" > "$TMP/$c.failed"; } &
done
wait
if ls "$TMP"/*.failed >/dev/null 2>&1; then
  cat "$TMP"/*.failed; echo "refresh aborted, previous guide kept"; exit 1
fi

/usr/bin/env python3 -I "$ROOT/scripts/build_fav_epg.py" "$MAP" "$TMP" "$OUT" \
  && gzip -t "$OUT" || { echo "build FAILED, previous guide kept"; exit 1; }

echo "done. Lineup picks up the new guide on its next guide refresh."
