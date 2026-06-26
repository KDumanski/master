"""
Parse Omar's paintings out of the Drive folder filenames.
Most files are named like:
  "Omar Chacon, <Title>, acrylic on canvas, 7.25in x 11.25in, 2021_300dpi.jpg"
…with many variants. We extract title / medium / dimensions / year and group
by the top-level show folder. Secondary shots (detail / side / installation)
are tagged so primary works can be listed once.

Usage: python scripts/paintings_inventory.py <folderId>
Output: TSV — group <tab> kind <tab> title <tab> medium <tab> dims <tab> year <tab> file
"""
import sys, io, os, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from google_auth import service  # noqa: E402

drive = service('personal', 'drive', 'drive', 'v3')

IMG_EXT = ('.jpg', '.jpeg', '.png', '.tif', '.tiff')
YEAR_RE = re.compile(r'\b(19|20)\d{2}\b')
# decimal alternative FIRST so "11.25" isn't truncated to "11."
DIMS_RE = re.compile(r'(\d+(?:\.\d+|[¼½¾⅓⅔])?)\s*(?:in|")?\s*[x×]\s*'
                     r'(\d+(?:\.\d+|[¼½¾⅓⅔])?)\s*(?:in|")?', re.I)
MEDIUM_KW = re.compile(r'(acrylic|canvas|paper|resin|panel|wax|mixed media)', re.I)
SECONDARY = re.compile(r'\b(detail|detalle|side\s*view|side|installation|install|view|shot|gallery|studio)\b', re.I)


def list_children(folder_id):
    out, tok = [], None
    while True:
        r = drive.files().list(q=f"'{folder_id}' in parents and trashed=false",
                               pageSize=200, fields="nextPageToken,files(id,name,mimeType)",
                               pageToken=tok, orderBy='name').execute()
        out += r.get('files', [])
        tok = r.get('nextPageToken')
        if not tok:
            break
    return out


def clean(name):
    base = re.sub(r'\.(jpe?g|png|tiff?)$', '', name, flags=re.I)
    # strip common trailing tokens
    base = re.sub(r'[_\s]*(300dpi|jpg|jpeg|tif|tiff|pg|hi-?res|RE|_?DSC\d+)\b', '', base, flags=re.I)
    base = base.replace('_', ' ').strip(' _-,')
    return base


def parse(name):
    base = clean(name)
    kind = 'detail/view' if SECONDARY.search(base) else 'primary'
    year = YEAR_RE.search(base)
    year = year.group(0) if year else ''
    dm = DIMS_RE.search(base)
    dims = f"{dm.group(1)} × {dm.group(2)} in" if dm else ''
    # ignore pixel dimensions like 1024x1024 (export artifacts, not canvas size)
    if dm and (dm.group(1) in ('1024', '512') and dm.group(2) in ('1024', '512')):
        dims = ''
    # work on comma segments where present, else dash segments
    segs = [s.strip() for s in re.split(r'[,]', base) if s.strip()]
    if len(segs) < 2:
        segs = [s.strip() for s in re.split(r'\s[-–]\s|_', base) if s.strip()]
    medium = next((s for s in segs if MEDIUM_KW.search(s)), '')
    medium = re.sub(r'\s+', ' ', medium).strip()
    # title = first segment that is not the artist name, not the year, not medium, not dims
    title = ''
    for s in segs:
        low = s.lower()
        if 'omar' in low and 'chac' in low:
            # may be "Omar Chacon 2011" or "Omar Chacon" — strip name, keep remainder
            rem = re.sub(r'omar\s*chac[oó]n', '', s, flags=re.I)
            rem = YEAR_RE.sub('', rem).strip(' -,')
            if rem and not MEDIUM_KW.search(rem) and not DIMS_RE.search(rem):
                title = rem
                break
            continue
        if s == year:
            continue
        if MEDIUM_KW.search(s) or DIMS_RE.search(s):
            continue
        title = s
        break
    title = YEAR_RE.sub('', title).strip(' -,#').replace('  ', ' ')
    return kind, title, medium, dims, year


def walk(folder_id, group):
    for f in list_children(folder_id):
        if f['mimeType'] == 'application/vnd.google-apps.folder':
            # nested folder: keep the top-level group label
            walk(f['id'], group)
        elif f['name'].lower().endswith(IMG_EXT):
            kind, title, medium, dims, year = parse(f['name'])
            print('\t'.join([group, kind, title, medium, dims, year, f['name']]))


root = sys.argv[1]
for f in list_children(root):
    if f['mimeType'] == 'application/vnd.google-apps.folder':
        walk(f['id'], f['name'])
    elif f['name'].lower().endswith(IMG_EXT):
        kind, title, medium, dims, year = parse(f['name'])
        print('\t'.join(['(loose / Fluid Borders 2021)', kind, title, medium, dims, year, f['name']]))
