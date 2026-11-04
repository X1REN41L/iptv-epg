"""Index guide sources: per file, channel id -> display names and programmes in the 3-day window.
usage: index_all_src.py SRC_DIR OUT_JSON"""
import gzip, json, os, sys
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET
src, out = sys.argv[1:3]
today = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
lo, hi = today, today + timedelta(days=3)
now = datetime.now(timezone.utc)
def ts(s):
    s = s.strip()
    return datetime.strptime(s[:20], '%Y%m%d%H%M%S %z') if len(s) > 14 else datetime.strptime(s[:14], '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
idx = {}
for fn in sorted(os.listdir(src)):
    if not fn.endswith('.xml.gz'): continue
    f = fn[len('epg_ripper_'):-len('.xml.gz')]
    ch = {}
    try:
        for _, el in ET.iterparse(gzip.open(os.path.join(src, fn)), events=('end',)):
            if el.tag == 'channel':
                ch.setdefault(el.get('id'), {'names': [], 'win': 0, 'up': 0})['names'] = [d.text or '' for d in el.findall('display-name')]
                el.clear()
            elif el.tag == 'programme':
                c = ch.setdefault(el.get('channel'), {'names': [], 'win': 0, 'up': 0})
                try:
                    a, b = ts(el.get('start')), ts(el.get('stop'))
                    if b > lo and a < hi: c['win'] += 1
                    if b > now: c['up'] += 1
                except Exception: pass
                el.clear()
    except Exception as e:
        print('ERR', fn, e)
    idx[f] = ch
    print(f, len(ch), sum(1 for c in ch.values() if c['up']))
json.dump(idx, open(out, 'w'), ensure_ascii=False)
