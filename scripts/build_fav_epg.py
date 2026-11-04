"""Build the XMLTV guide for the channels listed in a map TSV, today .. the end of the day after tomorrow (local time).

For each channel the candidate with the most programmes still to come in that window wins (first candidate on a tie).
Output channel ids are stable (nvfav.<xtream_id>), which Lineup maps itself; times are written in UTC.
Programmes keep only title, sub-title, desc and the first category, to keep the guide import fast.
Map columns: xtream_id, title, candidates (FILE:channel_id,...; empty = no guide on purpose).
usage: build_fav_epg.py MAP_TSV EPG_DIR OUT_XML_GZ
"""
import copy, gzip, os, re, sys
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

UTC_FMT = '%Y%m%d%H%M%S +0000'

map_tsv, epg_dir, out = sys.argv[1:4]
rows = {}
for line in open(map_tsv, encoding='utf-8'):
    if line.startswith('#') or not line.strip():
        continue
    xid, title, cands, *_ = line.rstrip('\n').split('\t')
    # first row wins: the overrides file comes before the auto map
    # split only at commas that start a new FILE: (NO1 channel ids contain commas)
    rows.setdefault(xid, (title, [tuple(c.split(':', 1)) for c in re.split(r',(?=[A-Z0-9_]+:)', cands) if c.strip()]))

def ts(s):
    t = datetime.strptime(s[:20], '%Y%m%d%H%M%S %z') if len(s) > 14 else datetime.strptime(s[:14], '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
    return t.astimezone(timezone.utc)

now = datetime.now(timezone.utc)
win_start = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
win_end = win_start + timedelta(days=3)  # today, tomorrow, the day after
KEEP = ('title', 'sub-title', 'desc', 'category')
wanted = {}  # file -> set of channel ids
for _, cands in rows.values():
    for f, cid in cands:
        wanted.setdefault(f, set()).add(cid)

chan_el, progs, upcoming, last = {}, {}, {}, {}
for f, ids in wanted.items():
    path = os.path.join(epg_dir, 'epg_ripper_%s.xml.gz' % f)
    for _, el in ET.iterparse(gzip.open(path), events=('end',)):
        if el.tag == 'channel':
            if el.get('id') in ids:
                chan_el[(f, el.get('id'))] = ET.tostring(el, encoding='unicode')
            el.clear()
        elif el.tag == 'programme':
            key = (f, el.get('channel'))
            start, stop = (ts(el.get('start')), ts(el.get('stop'))) if key[1] in ids else (None, None)
            if start and stop > win_start and start < win_end:
                progs.setdefault(key, []).append((start, stop, el))
                if stop > now:
                    upcoming[key] = upcoming.get(key, 0) + 1
                last[key] = max(last.get(key, stop), stop)
            else:
                el.clear()

n_prog = 0
with gzip.open(out + '.part', 'wt', encoding='utf-8') as w:
    w.write('<?xml version="1.0" encoding="UTF-8"?>\n<tv generator-info-name="iptv-epg nvision">\n')
    picks = []
    for xid, (title, cands) in rows.items():
        if not cands:
            continue  # "no guide" row (blocks the auto map row too)
        best = max(cands, key=lambda k: upcoming.get(k, 0))
        if not upcoming.get(best):
            print('NO UPCOMING DATA:', title, cands)
            continue
        picks.append((xid, best))
        print('%-32s -> %-34s upcoming %3d  until %s' % (title, '%s:%s' % best, upcoming[best], last[best].strftime('%Y-%m-%d %H:%MZ')))
    for xid, key in picks:
        ch = ET.Element('channel', id='nvfav.%s' % xid)
        ET.SubElement(ch, 'display-name').text = rows[xid][0]
        src = ET.fromstring(chan_el[key]) if key in chan_el else ET.Element('channel')
        ch.extend(e for e in src if e.tag != 'display-name')
        w.write(ET.tostring(ch, encoding='unicode'))
    for xid, key in picks:
        for start, stop, el in sorted(progs[key], key=lambda p: p[0]):
            p = ET.Element('programme')
            seen = set()
            for e in el:
                if e.tag in KEEP and e.tag not in seen:  # first of each only
                    p.append(copy.deepcopy(e)); seen.add(e.tag)
            p.set('start', start.strftime(UTC_FMT)); p.set('stop', stop.strftime(UTC_FMT)); p.set('channel', 'nvfav.%s' % xid)
            w.write(ET.tostring(p, encoding='unicode')); n_prog += 1
    w.write('</tv>\n')
os.replace(out + '.part', out)
print('channels', len(picks), 'of', len(rows), '| programmes', n_prog, '| window', win_start.strftime('%Y-%m-%d %H:%M'), '->', win_end.strftime('%Y-%m-%d %H:%M %Z'))
