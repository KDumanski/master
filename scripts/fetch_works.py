"""
Download Omar's catalogued paintings from Drive, downscale for web, and emit
a catalog JS file the static site loads (window.OMAR_WORKS).

Pulls only "primary" titled works that carry a medium + dimensions in the
filename (skips installation/detail/snapshot shots and untitled files).
Saves <=1800px JPEGs into  Omars Art Website/assets/works/  and writes
assets/works/catalog.js.

Usage: python scripts/fetch_works.py
"""
import sys, io, os, re, json, unicodedata
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from google_auth import service  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

SITE = r"c:/Propcheck Git/clone/Omars Art Website"
OUT_DIR = os.path.join(SITE, "assets", "works")
os.makedirs(OUT_DIR, exist_ok=True)
MAX_EDGE = 1800

drive = service('personal', 'drive', 'drive', 'v3')

# show folders worth pulling (clean titled JPGs spanning 2008–2023)
FOLDERS = [
    ('Fluid Borders', '1WgIrxfjBJWavl76SrkM3WP9aB5CttcKR'),       # Thatcher 2021
    ('Sin Seine', '1U7u4iI1AHHnVzUSE3u9UnitObVM_zM_r'),           # Fouladi 2023
    ('Adapt / Applied Matter', '1Z_CHKe6mAjcIK9wH5O5BEF1w7o7pSnJ7'),  # Robischon 2020/21
    ('Orcutt (2011 series)', '1d0fy6cNnWAi3MSMVomsBtJgqUavaGRWz'),  # Bacanal / CC works
]

IMG_EXT = ('.jpg', '.jpeg', '.png')
YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')
DIMS_RE = re.compile(r'(\d+(?:\.\d+|[¼½¾⅓⅔])?)\s*(?:in|")?\s*[x×]\s*(\d+(?:\.\d+|[¼½¾⅓⅔])?)\s*(?:in|")?', re.I)
MEDIUM_KW = re.compile(r'(acrylic|canvas|paper|resin|panel|wax|mixed media)', re.I)
SECONDARY = re.compile(r'\b(detail|detalle|side\s*view|side|installation|install|view|shot|gallery|studio|opening|collector|arrival|happening)\b', re.I)
FRAC = {'¼': .25, '½': .5, '¾': .75, '⅓': .33, '⅔': .67}


def numf(s):
    if s and s[-1] in FRAC:
        return int(s[:-1]) + FRAC[s[-1]]
    try:
        return float(s)
    except ValueError:
        return 0


def clean(name):
    b = re.sub(r'\.(jpe?g|png|tiff?)$', '', name, flags=re.I)
    b = re.sub(r'[_\s]*(300dpi|jpg|jpeg|tif|tiff|pg|hi-?res|RE|_?DSC\d+)\b', '', b, flags=re.I)
    return b.replace('_', ' ').strip(' _-,')


def parse(name):
    base = clean(name)
    if SECONDARY.search(base):
        return None
    ym = YEAR_RE.search(base); year = ym.group(0) if ym else ''
    dm = DIMS_RE.search(base)
    if not dm:
        return None
    a, b = numf(dm.group(1)), numf(dm.group(2))
    if {a, b} <= {1024.0, 512.0}:   # pixel export size, not canvas
        return None
    dims = f"{dm.group(1)} × {dm.group(2)} in"
    long_in = max(a, b)
    segs = [s.strip() for s in re.split(r'[,]', base) if s.strip()]
    if len(segs) < 2:
        segs = [s.strip() for s in re.split(r'\s[-–]\s|_', base) if s.strip()]
    medium = next((s for s in segs if MEDIUM_KW.search(s)), '')
    surface = 'Paper' if re.search(r'paper', medium, re.I) else \
              'Wood panel' if re.search(r'panel|wood', medium, re.I) else 'Canvas'
    title = ''
    for s in segs:
        low = s.lower()
        if 'omar' in low and 'chac' in low:
            rem = YEAR_RE.sub('', re.sub(r'omar\s*chac[oó]n', '', s, flags=re.I)).strip(' -,')
            if rem and not MEDIUM_KW.search(rem) and not DIMS_RE.search(rem):
                title = rem; break
            continue
        if s == year or MEDIUM_KW.search(s) or DIMS_RE.search(s):
            continue
        title = s; break
    title = YEAR_RE.sub('', title).strip(' -,#').replace('  ', ' ')
    if not title or len(title) < 2 or title.isdigit():
        return None
    tier = 'pequeno' if long_in <= 18 else 'mediano' if long_in <= 38 else 'grande'
    return {'title': title, 'surface': surface, 'dims': dims, 'year': year, 'tier': tier, 'long_in': long_in}


def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')


def walk(fid):
    out, tok = [], None
    while True:
        r = drive.files().list(q=f"'{fid}' in parents and trashed=false",
                               pageSize=200, fields="nextPageToken,files(id,name,mimeType)",
                               pageToken=tok).execute()
        for f in r.get('files', []):
            if f['mimeType'] == 'application/vnd.google-apps.folder':
                out += walk(f['id'])
            elif f['name'].lower().endswith(IMG_EXT):
                out.append(f)
        tok = r.get('nextPageToken')
        if not tok:
            break
    return out


catalog = {}   # key -> record (dedup, keep larger source)
for show, fid in FOLDERS:
    files = walk(fid)
    print(f"\n{show}: scanning {len(files)} images")
    for f in files:
        rec = parse(f['name'])
        if not rec:
            continue
        key = slug(rec['title']) + '-' + (rec['year'] or 'na')
        if key in catalog and catalog[key]['long_in'] >= rec['long_in']:
            continue
        try:
            data = drive.files().get_media(fileId=f['id']).execute()
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert('RGB')
            w, h = im.size
            if max(w, h) > MAX_EDGE:
                im = im.resize((round(w * MAX_EDGE / max(w, h)), round(h * MAX_EDGE / max(w, h))), Image.LANCZOS)
            fname = key + '.jpg'
            im.save(os.path.join(OUT_DIR, fname), 'JPEG', quality=82, optimize=True)
            rec.update({'src': 'assets/works/' + fname, 'show': show})
            catalog[key] = rec
            print(f"  ✓ {rec['title']} ({rec['year']}) {rec['dims']} [{rec['tier']}/{rec['surface']}]")
        except Exception as e:
            print(f"  ✗ {f['name']}: {e}")

works = sorted(catalog.values(), key=lambda r: (-(int(r['year']) if r['year'] else 0), r['title']))
for w in works:
    w.pop('long_in', None)
js = "window.OMAR_WORKS = " + json.dumps(works, ensure_ascii=False, indent=2) + ";\n"
with open(os.path.join(OUT_DIR, 'catalog.js'), 'w', encoding='utf-8') as fh:
    fh.write(js)
print(f"\nWROTE {len(works)} works → assets/works/catalog.js")
