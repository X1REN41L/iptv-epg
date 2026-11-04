"""Fetch the guide sources listed in work/channels.tsv and build out/premium_nvision_epg.xml.gz.

Window: today .. the end of the day after tomorrow (local time). For each channel the candidate with the most
programmes still to come wins (first candidate on a tie). Output channel ids are stable (nvfav.<xtream_id>), which
Lineup maps itself; times are written in UTC. Programmes keep only title, sub-title, desc and the first category.
Map columns: xtream_id, title, candidates (FILE:channel_id,...; empty = no guide on purpose).
A failed download or build exits non-zero and keeps the previous guide.
usage: python3 -I scripts/fetch_epg.py
"""
import copy, gzip, os, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_TSV = os.path.join(ROOT, 'work', 'channels.tsv')
OUT = os.path.join(ROOT, 'out', 'premium_nvision_epg.xml.gz')
SPECIAL_URLS = {'IPTVX': 'https://iptvx.one/EPG_LITE', 'IT999': 'http://epg.it999.ru/edem.xml.gz'}
KEEP = ('title', 'sub-title', 'desc', 'category')
UTC_FMT = '%Y%m%d%H%M%S +0000'


def source_url(f):
    return SPECIAL_URLS.get(f, 'https://epgshare01.online/epgshare01/epg_ripper_%s.xml.gz' % f)


def ts(s):
    t = datetime.strptime(s[:20], '%Y%m%d%H%M%S %z') if len(s) > 14 else datetime.strptime(s[:14], '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
    return t.astimezone(timezone.utc)


rows = {}
for line in open(MAP_TSV, encoding='utf-8'):
    if line.startswith('#') or not line.strip():
        continue
    xid, title, cands, *_ = line.rstrip('\n').split('\t')
    # split only at commas that start a new FILE: (NO1 channel ids contain commas)
    rows[xid] = (title, [tuple(c.split(':', 1)) for c in re.split(r',(?=[A-Z0-9_]+:)', cands) if c.strip()])

wanted = {}  # file -> set of channel ids
for _, cands in rows.values():
    for f, cid in cands:
        wanted.setdefault(f, set()).add(cid)

now = datetime.now(timezone.utc)
win_start = datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
win_end = win_start + timedelta(days=3)  # today, tomorrow, the day after
os.makedirs(os.path.dirname(OUT), exist_ok=True)

with tempfile.TemporaryDirectory() as tmp:
    def fetch(f):
        path = os.path.join(tmp, f + '.xml.gz')
        ok = subprocess.run(['curl', '-sSfL', '-m', '180', '-o', path, source_url(f)]).returncode == 0 \
            and subprocess.run(['gzip', '-t', path]).returncode == 0
        return f, ok

    print('downloading:', ' '.join(sorted(wanted)))
    with ThreadPoolExecutor(max_workers=16) as pool:
        failed = [f for f, ok in pool.map(fetch, sorted(wanted)) if not ok]
    if failed:
        sys.exit('download FAILED: %s; previous guide kept' % ' '.join(failed))

    chan_el, progs, upcoming, last = {}, {}, {}, {}
    for f, ids in wanted.items():
        for _, el in ET.iterparse(gzip.open(os.path.join(tmp, f + '.xml.gz')), events=('end',)):
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
    part = OUT + '.part'
    with gzip.open(part, 'wt', encoding='utf-8') as w:
        w.write('<?xml version="1.0" encoding="UTF-8"?>\n<tv generator-info-name="iptv-epg nvision">\n')
        picks = []
        for xid, (title, cands) in rows.items():
            if not cands:
                continue  # "no guide" row
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
    if subprocess.run(['gzip', '-t', part]).returncode != 0:
        sys.exit('build FAILED; previous guide kept')
    os.replace(part, OUT)

print('channels', len(picks), 'of', len(rows), '| programmes', n_prog, '| window', win_start.strftime('%Y-%m-%d %H:%M'), '->', win_end.strftime('%Y-%m-%d %H:%M %Z'))
