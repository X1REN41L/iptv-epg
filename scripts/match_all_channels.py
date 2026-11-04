"""Match every nvision live channel to guide channels by name (exact after normalising).
The name prefix picks the country's sources; every one of them listing the name becomes a candidate, and the
build takes the candidate with the most programmes to come. Skips 24/7, VOD-style, live-event and separator
entries, and names with a stream in the overrides file.
Per name only the best-quality stream gets a guide (4K/UHD > FHD > HD > rest).
usage: match_all_channels.py ALL_LIVE_TSV SRC_INDEX_JSON OVERRIDES_TSV OUT_MAP_TSV"""
import json, re, sys, unicodedata
live_tsv, index_json, overrides_tsv, out = sys.argv[1:5]

US, UK, AFR = ['US2', 'US_SPORTS1', 'FANDUEL1'], ['UK1', 'IE1'], ['ZA1', 'NG1', 'KE1']
IND = ['IN1', 'IN4', 'IPTVX', 'IT999', 'IN2']
ARAB = ['BEIN1', 'AE1', 'SA2', 'ALJAZEERA1', 'EG1']
YU = ['RS1', 'HR1', 'BA1', 'SPORTKLUB1']
LAT_C = ['SV1', 'CR1', 'PA1']
FILES = {  # name prefix (upper-cased) -> sources in the channel's own country
    'US': US, 'USA': US, 'CAR': US, 'CA': ['CA2'], 'UK': UK, 'IE': ['IE1', 'UK1'],
    'AF': AFR, 'DSTV': AFR, 'ZA': AFR, 'NG': ['NG1'], 'AL': ['AL1'],
    'AR': ARAB, 'AE': ARAB, 'QA': ARAB, 'SA': ARAB, 'EG': ARAB, 'BHR': ARAB, 'DZ': ARAB, 'IQ': ARAB, 'JO': ARAB,
    'KW': ARAB, 'LB': ARAB, 'LY': ARAB, 'MA': ARAB, 'OM': ARAB, 'PS': ARAB, 'SD': ARAB, 'SY': ARAB, 'TN': ARAB, 'YE': ARAB,
    'ARG': ['AR1'], 'AT': ['AT1', 'DE1'], 'AU': ['AU1'], 'BE': ['BE2'], 'BG': ['BG1'], 'BIH': ['BA1', 'SPORTKLUB1'],
    'BR': ['BR1', 'BR2'], 'CH': ['CH1'], 'CL': ['CL1'], 'CN': ['IPTVX', 'IT999'], 'CO': ['CO1'], 'CR': ['CR1'], 'CY': ['CY1'],
    'CZ': ['CZ1'], 'SK': ['SK1', 'CZ1'], 'DE': ['DE1', 'AT1'], 'DK': ['DK1'], 'DO': ['DO1'], 'EC': ['EC1'],
    'ES': ['ES1'], 'EX-YU': YU, 'HR': ['HR1', 'SPORTKLUB1'], 'RS': ['RS1', 'SPORTKLUB1'], 'FI': ['FI1'], 'FR': ['FR1'],
    'GR': ['GR1'], 'GT': LAT_C, 'HN': LAT_C, 'NI': LAT_C, 'SV': LAT_C, 'PA': ['PA1'], 'HK': ['HK1', 'IPTVX', 'IT999'],
    'HU': ['HU1'], 'ID': ['ID1', 'IPTVX', 'IT999'], 'IL': ['IL1'], 'IT': ['IT1'], 'JP': ['JP1', 'JP2'], 'KR': ['KR1'],
    'KZ': ['KZ1'], 'LA': ['MX1'], 'LT': ['LT1'], 'LV': ['LV1'], 'MN': ['MN1'], 'MT': ['MT1'], 'MX': ['MX1'],
    'MY': ['MY1', 'IPTVX', 'IT999'], 'NL': ['NL1'], 'NO': ['NO1'], 'NZ': ['NZ1'], 'PE': ['PE1'], 'PH': ['PH2', 'IPTVX', 'IT999'],
    'PL': ['PL1'], 'PT': ['PT1'], 'RO': ['RO1', 'RO2'], 'RU': ['IPTVX', 'IT999', 'UA1'], 'UKR': ['UA1'], 'SE': ['SE1'],
    'SG': ['SG1'], 'TH': ['TH1'], 'TR': ['TR1', 'TR3'], 'TW': ['IPTVX', 'IT999'], 'UY': ['UY1'], 'VN': ['VN1', 'IPTVX', 'IT999'],
    'IN': IND, 'IND': IND, 'IIND': IND, 'ININD': IND, 'IND-REGIONAL': IND, 'IND-BANGLA': IND, 'IND-PUNJABI': IND,
    'IND-PUN': IND, 'IN-GUJ': IND, 'IN-KN': IND, 'IN-MAR': IND, 'IN-MY': IND, 'IN-ODIA': IND, 'IN-TM': IND,
    'DOC': IND, 'KIDS': IND, 'CRI': IND, 'USA ASIAN': IND + ['ASIANTELEVISION1'],
    'PK': ['PK1', 'ASIANTELEVISION1'] + IND, 'PAK': ['PK1', 'ASIANTELEVISION1'] + IND,
    'BD': IND, 'BD-LOC': IND, 'BD-UK': UK + IND,
}
CAT_FILES = [(r'^(INDIAN|IND \||CRICKET)', IND), (r'^(PAKISTAN|ISLAMIC)', ['PK1', 'ASIANTELEVISION1'] + IND),
             (r'^(UK \| ASIA)', UK + IND), (r'^(BANGLADESH)', IND), (r'^DSTV', AFR), (r'^(BEIN|MBC)', ARAB)]
SKIP_CAT = re.compile(r'24/7|24x7|cinemania|vibe|live event|world cup|bigg boss|cinebox|netflix|boxoffice|skyflix|beoutq|'
                      r'sky store|ncaa|motogp|f1|betting|scottish|snooker|multi audio|ramazan|d2h active', re.I)
SKIP_TITLE = re.compile(r'24/7|24x7|\bevent|ppv|welcome|===|[★●✦#*]|\bvip\b|backup|only during|\d{1,2}[:.]\d\d\s*(am|pm)|'
                        r'\b(mon|tue|wed|thu|fri|sat|sun)\b \d|\bplayer|multi ?cam|\bpop.?up', re.I)
QUAL = re.compile(r'\b(4k|uhd|fhd|hd|sd|hevc|h\.?26[45]|1080[pi]?|720p|50 ?fps|hdr|raw|low|uk feed)\b', re.I)

def qrank(t):
    t = t.lower()
    return 4 if re.search(r'\b(4k|uhd)\b', t) else 3 if re.search(r'\bfhd\b|1080', t) else 2 if re.search(r'\bhd\b|720', t) else 1

def norm(s):
    s = unicodedata.normalize('NFKC', s).lower().replace('&', ' and ').replace('+', ' plus ')
    s = ''.join(ch for ch in unicodedata.normalize('NFKD', s) if not unicodedata.combining(ch))  # Cinéma = Cinema
    s = re.sub(r'[\(\[][^\)\]]*[\)\]]', ' ', s)
    s = QUAL.sub(' ', s)
    s = re.sub(r'[^\w]+', ' ', s.replace('_', ' ')).strip()
    for a, b in ALIASES:
        s = re.sub(a, b, s)
    return s.replace(' ', '')

ALIASES = [(r'^u and ', ''), (r'\bjunior\b', 'jr'), (r'\bnorthern ireland\b', 'ni'), (r'\bscotland\b', 'scot'),
           (r'\bwales\b', 'wal'), (r'\blondon\b', 'lon'), (r'^bbc one$', 'bbc one lon'), (r'^bbc two$', 'bbc two lon'),
           (r' (tv|channel)$', ''), (r'^bally sports\b', 'fanduel sports'), (r'^fanduel sports network\b', 'fanduel sports')]

# Extra source-side keys: the name in brackets (Cable.Pulse.24.(CP24) = CP24), the name without the source's own
# country (Disney.Channel.Canada, MTV.España) and without a TV call-sign suffix (CHCH-DT).
# Not Polska / Italia / France / Portugal: there they are part of other channels' names (Kino Polska, Rai Italia).
HOME_WORD = {'CA2': 'canada', 'ES1': 'espana|spain', 'DE1': 'deutschland|germany', 'UK1': 'uk', 'IE1': 'ireland',
             'NL1': 'nederland|netherlands'}

def source_names(f, name):
    yield name
    for b in re.findall(r'\(([^)]*)\)', name):
        if len(re.sub(r'\W', '', b)) >= 3 and re.search(r'\d|^[A-Z0-9 ]+$', b):
            yield b
    plain = re.sub(r'\s*\([^)]*\)', '', name)
    if f in HOME_WORD:
        yield re.sub(r'(?i)[\s.]+(%s)$' % HOME_WORD[f], '', plain)
    yield re.sub(r'[-\s.]DT$', '', plain)

# A source often lists one name in several feeds, e.g. Comedy.Central.HD.us2 and Comedy.Central.HD.(Pacific).us2
# (3h later) or Eurosport.1.(hr).cz (Croatian) next to Eurosport.1.cz. nvision carries the East / home-country feed.
OTHER_ZONE = re.compile(r'\b(pacific|west|mountain|alternate)\b', re.I)
TAG_CC = {'bh': 'ba', 'bih': 'ba', 'canada': 'ca', 'us': 'us', 'uk': 'uk', 'niem': 'de', 'dsf': 'de'}

def feed_rank(cid):
    """0 = home feed, 1 = unknown tag, 2 = other time zone or other country's feed."""
    if OTHER_ZONE.search(cid):
        return 2
    cc = re.sub(r'\d+$', '', cid.rsplit('.', 1)[-1].lower())
    tags = [t.strip(' .').lower() for p in re.findall(r'\(([^)]*)\)', cid) for t in p.split('/')]
    codes = [TAG_CC.get(t, t if re.fullmatch(r'[a-z]{2}', t) else None) for t in tags]
    if any(c and c != cc for c in codes):
        return 2
    return 1 if None in codes else 0

def split_prefix(t):
    t = t.strip()
    m = re.match(r'^\s*([A-Za-z][A-Za-z \-]{0,13}?)\s*[:|]\s*(.*)$', t)
    if not m:
        return None, t
    p, rest = m.group(1).upper().strip(), m.group(2)
    m2 = re.match(r'^(DSTV|SRB|TG|AP|TS)\s*[:|]\s*(.*)$', rest, re.I)  # second-level prefixes
    if m2:
        rest = m2.group(2)
    return p, rest

idx = json.load(open(index_json))
by_key = {}  # file -> normalised name -> [(cid, win)]
for f, chans in idx.items():
    d = by_key.setdefault(f, {})
    for cid, c in chans.items():
        if not c['win']:
            continue
        stem = re.sub(r'\.[a-z]{2,3}$', '', cid)
        keys = {norm(v) for n in c['names'] + [stem.replace('.', ' ')] for v in source_names(f, n)}
        if f == 'US2':  # US cable feeds: HBO.East.us2 is plain HBO (West / Pacific get feed_rank 2)
            keys |= {re.sub(r'(east|west)$', '', k) for k in keys}
        for k in keys - {''}:
            d.setdefault(k, []).append((cid, c['win']))

def bein_name(cid):
    """BEIN1 ids (e.g. beIN_SPORTS1_ENGLISH_Digital_Mono_EN) -> (channel name, listing language AR/EN)."""
    core = re.sub(r'NEW_|LOGOS-_|_?DIGITAL|_MONO(-D-1|-01)?|_BEIN\.COM|\.BEIN$', '', cid.upper())
    core, lang = core[:-3], core[-2:]
    if core in ('NEWS', '4K'):
        return 'bein sports news' if core == 'NEWS' else 'bein 4k', lang
    m = re.match(r'BEIN[_-]?SPORTS[_-]?(MAX|XTRA)?[_-]?0?(\d)(?:_(ENGLISH|FRENCH))?$', core)
    if not m:
        return None, lang
    return ' '.join(x for x in ('bein sports', m.group(1), m.group(3), m.group(2)) if x), lang

bein = {}  # key -> {lang: (cid, win)}; English/French channels take the EN listing, the rest AR
for cid, c in idx.get('BEIN1', {}).items():
    name, lang = bein_name(cid)
    if name and c['win']:
        bein.setdefault(norm(name), {})[lang] = (cid, c['win'])
by_key['BEIN1'] = {k: [v.get('EN' if re.search('english|french', k) else 'AR') or next(iter(v.values()))]
                   for k, v in bein.items()}

overrides = set()
for line in open(overrides_tsv, encoding='utf-8'):
    if not line.startswith('#') and line.strip():
        overrides.add(line.split('\t')[0])

groups = {}  # (files, key) -> [(rank, xid, title)]
seen_xid, skipped = set(), {'cat': 0, 'title': 0, 'nosrc': 0}
for line in open(live_tsv, encoding='utf-8'):
    xid, cat, title = line.rstrip('\n').split('\t')[:3]
    if xid in seen_xid:
        continue
    seen_xid.add(xid)
    if SKIP_CAT.search(cat): skipped['cat'] += 1; continue
    if SKIP_TITLE.search(title): skipped['title'] += 1; continue
    p, name = split_prefix(title)
    files = FILES.get(p) if p else None
    if files is None:
        files = next((fl for rx, fl in CAT_FILES if re.search(rx, cat.strip())), None)
    if not files: skipped['nosrc'] += 1; continue
    k = norm(name)
    if not k or re.search(r'[:|]', name): skipped['title'] += 1; continue
    groups.setdefault((tuple(files), k), []).append((qrank(title), xid, title))

rows, nomatch = [], 0
for (files, k), members in groups.items():
    if any(x in overrides for _, x, _ in members):
        continue  # a stream of this name is in the overrides file
    cands = [(f, cid) for f in files for cid, _ in by_key.get(f, {}).get(k, [])]
    if not cands:
        nomatch += 1; continue
    home = min(feed_rank(cid) for _, cid in cands)
    cands = [c for c in cands if feed_rank(c[1]) == home]
    best = max(members, key=lambda m: (m[0], -int(m[1])))
    rows.append((best[1], best[2], ','.join('%s:%s' % c for c in dict.fromkeys(cands))))
rows.sort(key=lambda r: int(r[0]))
with open(out, 'w', encoding='utf-8') as w:
    w.write('# auto-generated by match_all_channels.py: xtream_id\ttitle\tcandidates\n')
    for r in rows:
        w.write('\t'.join(r) + '\n')
print('names', len(groups), 'matched', len(rows), 'no guide', nomatch, 'skipped', skipped)
