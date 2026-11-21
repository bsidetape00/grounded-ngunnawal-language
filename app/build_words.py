"""Build app/words.json from the two established sources in the repository.

Sources (inside ngunnawal_language_database_package.zip):
  - Louise Baird XML dictionary 2022-10-04 (Dictonary 20221004.xml)
  - A Sketch Grammar of Ngunnawal, Louise Baird 2019, Appendix C 17.3 Ngl to English word list

No words are added. Every headword and meaning comes from one of these two files.
Usage: python3 build_words.py <path to zip> <out dir>
Needs: beautifulsoup4, pdftotext (poppler-utils)
"""
import sys, re, json, zipfile, subprocess, tempfile, collections, os
from bs4 import BeautifulSoup

ZIP, OUT = sys.argv[1], sys.argv[2]
tmp = tempfile.mkdtemp()
with zipfile.ZipFile(ZIP) as z:
    xml = z.read('ngunnawal_language_database/01_sources/original/Dictonary 20221004.xml').decode('utf-8')
    pdf = os.path.join(tmp, 'sketch.pdf')
    open(pdf, 'wb').write(z.read('ngunnawal_language_database/01_sources/original/A Sketch Grammar of Ngl.pdf'))
subprocess.run(['pdftotext', '-layout', pdf, os.path.join(tmp, 's.txt')], check=True)
L = open(os.path.join(tmp, 's.txt'), encoding='utf-8').read().split('\n')

def tx(e): return re.sub(r'\s+', ' ', e.get_text(' ', strip=True)).strip() if e else ''

# ---- Baird 2022 XML: main-entry senses only (sub-entries are separate entries) ----
soup = BeautifulSoup(xml, 'html.parser')
X = []
for div in soup.find_all('div', class_='entry'):
    eid = div.get('id', '')
    senses, dl = [], []
    for s in div.find_all(class_='sense'):
        if s.get('entryguid') != eid: continue
        d = [tx(x) for x in s.find_all(class_='definitionorgloss')]
        senses.append('; '.join(dict.fromkeys(z for z in d if z)))
        for x in s.find_all(class_='dialectlabelsr'):
            t = tx(x)
            if t and t not in dl: dl.append(t)
    pos = []
    for p in div.find_all(class_='partofspeech'):
        t = tx(p)
        if t and t not in pos: pos.append(t)
    X.append(dict(hw=tx(div.find(class_='mainheadword')), g=' | '.join(z for z in senses if z),
                  pos=pos, dl=dl, com=[tx(c) for c in div.find_all(class_='comment')]))

# ---- Sketch grammar 17.3 Ngl to English ----
start = next(i for i, l in enumerate(L) if l.strip() == '17.3 Ngl to English')
end = next(i for i, l in enumerate(L) if i > start and re.match(r'^\s*(18\s|References)', l))
S, pg = [], 117
for l in L[start + 2:end]:
    if not l.strip(): continue
    if re.fullmatch(r'\s*\d{2,3}\s*', l): pg = int(l) + 1; continue
    m = re.match(r'^\s*(\S(?:.*?\S)?)\s{2,}(\S.*)$', l)
    if m and len(l) - len(l.lstrip()) < 5:
        S.append(dict(hw=m.group(1).strip(), gl=m.group(2).strip(), p=pg))
    elif S:
        S[-1]['gl'] += ' ' + l.strip()
fix = {  # three rows where the PDF wraps the English onto the line above the headword
 'gulangurundji': '2sg.ASS, you and others associated with you',
 'gulangurungula': '1du.incl.ASS, us two (including the listener) and others associated with us',
 'gulangurungulaya': '1du.excl.ASS, us two (excluding listener) and others associated with us'}
for r in S:
    if r['hw'] in fix: r['gl'] = fix[r['hw']]
S = [r for r in S if r['hw'] != '/ŋunawal/']

# ---- compare by meaning, not just spelling ----
def norm(h): return re.sub(r'\s+\d+$', '', h.strip().lower()).replace('ɟ', 'dj')
STOP = set("a an the of to for in on with and or as is be by at from that this it its ones who which used usually especially something someone part type kind very not general term".split())
def toks(g, stop=True):
    g = re.sub(r'\b[123](sg|du|pl)\S*', '', g.lower()).replace('-', ''); out = set()
    for w in re.findall(r'[a-z]+', g):
        if (stop and w in STOP) or len(w) < 2: continue
        w = re.sub(r'ies$', 'y', w)
        if len(w) > 4: w = re.sub(r'(es|s|ed)$', '', w)
        out.add(w)
    return out or (toks(g, False) if stop else out)

PERSON = re.compile(r'\b(male name|female name|also known as|man\'s name|woman\'s name)\b', re.I)
sk_by = collections.defaultdict(list)
for r in S: sk_by[norm(r['hw'])].append(r)
used, entries, held_back = set(), [], 0
# Notes from the language authority (Cheyne Halloran). Recorded word for word in authority_notes.json.
NOTES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'authority_notes.json')
NOTES = json.load(open(NOTES_PATH, encoding='utf-8')) if os.path.exists(NOTES_PATH) else []
note_by = {norm(n['w']): n for n in NOTES}
for n in NOTES:  # sketch meanings the authority has confirmed are not treated as conflicts
    for r in sk_by.get(norm(n['w']), []):
        if r['gl'] in n.get('confirms', []): used.add(id(r))
NAMEPAIR = re.compile(r'^[A-Z][a-z]+ [A-Z][a-z]+$')
keep = [x for x in X if x['hw'] and x['g']]
for x in keep:
    x['rows'] = sk_by.get(norm(x['hw']), [])
    x['agree'] = [r for r in x['rows'] if toks(r['gl']) & toks(x['g'])]
    for r in x['agree']: used.add(id(r))
for x in keep:
    if PERSON.search(x['g']) or NAMEPAIR.match(x['hw']): held_back += 1; continue
    if x['agree']: st, show = 'ok', x['agree']
    else:
        show = [r for r in x['rows'] if id(r) not in used]  # rows not explained by a sibling homograph
        st = 'chk' if show else 'b'
    entries.append(dict(w=x['hw'], g=x['g'], pos=', '.join(x['pos']), dl=', '.join(x['dl']),
                        sg=' / '.join(r['gl'] for r in show), sp=', '.join(sorted({str(r['p']) for r in show})),
                        st=st, com=' '.join(x['com'])))
    n = note_by.get(norm(x['hw']))
    if n: entries[-1].update(cn=n['note'], cnby=n['by'], cnd=n['date'], cnc='; '.join(n.get('confirms', [])))
baird_norms = {norm(x['hw']) for x in X}
for r in S:
    if id(r) in used or norm(r['hw']) in baird_norms: continue
    entries.append(dict(w=r['hw'], g='', pos='', dl='', sg=r['gl'], sp=str(r['p']), st='s', com=''))

# ---- grouping by English meaning (for browsing only; not a linguistic claim) ----
def short(e): return re.split(r'[;:]', (e['g'] or e['sg']).split('|')[0])[0].strip()
CATS = [
 ('People words', None, r'\b(i|me|my|you|youse|your|we|us|our|he|she|him|her|his|they|them|their|those two|1sg|2sg|3sg|1du|2du|3du|1pl|2pl|3pl)\b'),
 ('Numbers', None, r'\b(one|two|three|four|five|six|seven|eight|nine|ten|twenty|number)\b'),
 ('Body', None, r'\b(head|hand|hands|foot|feet|arm|leg|eye|eyes|ear|nose|mouth|tooth|teeth|hair|skin|bone|blood|belly|stomach|back|finger|fingers|fingernail|toe|knee|neck|shoulder|chest|heart|tongue|lip|nail|penis|bottom|urine|beard|forehead|cheek|thigh|elbow|breast|navel|ankle|wrist|chin|throat)\b'),
 ('Things people make', None, r'\b(boomerang|spear|shield|club|bag|coolamon|collamon|dish|net|headband|browband|apron|kilt|blanket|clothes|garment|axe|tomahawk|knife|canoe|cloak|rug|string|basket|pipe|tobacco|hut|house|bucket|nulla)\b'),
 ('Animals', None, r'\b(kangaroo|wallaby|possum|opossum|snake|lizard|goanna|bird|duck|emu|fish|eel|echidna|dog|dingo|parrot|rosella|cockatoo|crow|kookaburra|frog|toad|insect|ant|fly|grub|grubs|mussel|wombat|koala|bat|owl|mopoke|eagle|eaglehawk|hawk|swan|magpie|platypus|rat|bandicoot|spider|louse|mosquito|turtle|tortoise|crayfish|yabby|cod|perch|herring|pelican|plover|quail|pigeon|squirrel|glider|bee|moth|butterfly|horse|bull ant|centipede|cicada|worm|wren|curlew|ibis|heron|cormorant|galah|lyrebird|monitor|bilby|marsupial|reptile|animal)\b'),
 ('Plants', None, r'\b(tree|eucalypt|eucalyptus|bark|leaf|leaves|grass|plant|root|wattle|oak|casuarina|gum|box|stringybark|ironbark|flower|seed|fruit|yam|wood|cherry|pine|reed|bush|scrub|branch|log|kurrajong|daisy|orchid|fern|moss)\b'),
 ('Country and sky', None, r'\b(sun|moon|star|stars|rain|wind|cloud|sky|water|river|lake|creek|swamp|fire|smoke|hill|mountain|rock|stone|ground|country|land|night|day|morning|dusk|dawn|evening|cold|hot|fog|thunder|lightning|frost|snow|ice|plain|valley|sand|mud|ochre|clay|camp|track|road|pathway|sea|ashes)\b'),
 ('Family', None, r'\b(mother|father|brother|sister|aunt|uncle|child|children|baby|son|daughter|wife|husband|cousin|grandmother|grandfather|sibling|man|woman|women|men|boy|girl|old man|old woman)\b'),
]
for e in entries:
    p, s = e['pos'], short(e).lower()
    if 'nprop' in p: e['c'] = 'Places'; continue
    if 'cardnum' in p: e['c'] = 'Numbers'; continue
    if p.startswith(('pro', 'dem')): e['c'] = 'People words'; continue
    if p.startswith('v') and not p.startswith('v;'):
        e['c'] = 'Actions'; continue
    e['c'] = next((c for c, _, rx in CATS if re.search(rx, s)), 'Other')
for e in entries: e['s'] = short(e)

entries.sort(key=lambda e: (norm(e['w']).lstrip('-=').lower(), e['w']))
os.makedirs(OUT, exist_ok=True)
json.dump(entries, open(os.path.join(OUT, 'words.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print('entries', len(entries), collections.Counter(e['st'] for e in entries), 'held back (personal names):', held_back)
print(collections.Counter(e['c'] for e in entries if e['st'] == 'ok'))
