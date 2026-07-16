"""
Omar Chacón site — Drive photo sync.

Omar drops painting photos into the shared Drive folder "Omar Website Photos";
this script pulls anything new, converts it to a web-ready JPEG (max 2400px,
TIFF/PNG/HEIC handled), registers it as a work in the site's content file, and
pushes — which triggers the GitHub Pages deploy. The site itself is fully
static (KDumanski/Omar-art-website); this local script IS the upload pipeline,
running where the Drive OAuth tokens already live (masters/.secrets/).

Alongside the photos, an "Omar Website Info" Google Sheet lives in the same
folder. Omar fills one row per photo (file name + Title / Year / Medium / Size /
Price-or-status / Show). This script reads that sheet every run and applies those
fields to the matching work — so Omar can also FIX a painting's info later
without re-uploading. Filename-only still works: a photo with no sheet row just
gets a title guessed from its file name. The sheet is optional; if it's missing
the sync behaves exactly as it did before.

Usage:
  python scripts/omar_site_sync.py            # sync + commit + push
  python scripts/omar_site_sync.py --dry-run  # show what would happen
  python scripts/omar_site_sync.py --no-push  # sync + commit, don't push

Idempotent: a Drive file is skipped for RE-DOWNLOAD when its slug already has a
JPEG in public/uploads/, but sheet info is re-applied to existing works every
run. New works land at the top of the Paintings page.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import tempfile

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from google_auth import service  # noqa: E402
from googleapiclient.http import MediaIoBaseDownload  # noqa: E402
from PIL import Image  # noqa: E402

try:  # iPhone photos — optional; without it HEIC files are reported and skipped
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_OK = True
except ImportError:
    HEIC_OK = False

FOLDER_ID = '1J37tudsgrwjvyH8DX8GZ7oL9GkmAL1ip'  # Drive: "Omar Website Photos"
INFO_SHEET_NAME = 'Omar Website Info'  # Google Sheet in that folder; Omar fills it
# Where the site repo lives. Defaults to the local Windows clone; GitHub Actions
# sets OMAR_APP_DIR to its checkout so the same script runs unmodified in CI.
APP_DIR = os.environ.get('OMAR_APP_DIR', r'c:\Propcheck Git\clone\Omar-app')
UPLOADS = os.path.join(APP_DIR, 'public', 'uploads')
SITE_DATA = os.path.join(APP_DIR, 'content', 'site-data.json')

IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.heic'}
MAX_SIDE = 2400
JPEG_QUALITY = 88


def slugify(stem):
    s = re.sub(r'[^a-z0-9]+', '-', stem.lower()).strip('-')
    return s or 'untitled'


def prettify(stem):
    """Filename → display title: drop resolution/scan suffixes, tidy spacing."""
    t = re.sub(r'[_\-]+', ' ', stem)
    t = re.sub(r'\b\d{2,4}\s?dpi\b', '', t, flags=re.I)
    t = re.sub(r'\s{2,}', ' ', t).strip()
    return t or 'Untitled'


def year_of(stem):
    m = re.search(r'\b(19|20)\d{2}\b', stem)
    return int(m.group(0)) if m else None


def match_key(name):
    """Loose key for pairing a sheet row to a photo: lowercase, drop the file
    extension, strip everything but letters/digits. So "BDPM IX.jpg",
    "bdpm ix", and "BDPM_IX" all collapse to the same key."""
    stem = os.path.splitext(name)[0] if '.' in name else name
    return re.sub(r'[^a-z0-9]', '', stem.lower())


def load_show_lookup(data):
    """Map a loosely-typed show name back to its slug. Omar can type "Sin Seine"
    or "sin-seine"; both resolve. Returns {normalized_name: slug}."""
    norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
    lookup = {}
    for s in data.get('shows', []):
        lookup[norm(s.get('slug'))] = s['slug']
        lookup[norm(s.get('title'))] = s['slug']
    return lookup


def read_info_sheet(sheets_api, drive):
    """Return {match_key: {where, title, year, medium, dimensions, status, show}}
    from the "Omar Website Info" sheet in the folder. Empty dict if the sheet is
    missing or unreadable — the sync then falls back to filename-only behavior.

    Columns by position (header row skipped): A file name, B where-on-site,
    C title, D year, E medium, F size, G price/status, H show. Blank cells are
    ignored so a partly-filled row still helps."""
    q = ("'%s' in parents and trashed=false and "
         "mimeType='application/vnd.google-apps.spreadsheet' and name='%s'"
         % (FOLDER_ID, INFO_SHEET_NAME))
    found = drive.files().list(q=q, fields='files(id,name)').execute().get('files', [])
    if not found:
        print(f'  (no "{INFO_SHEET_NAME}" sheet found — using file names only)')
        return {}
    sid = found[0]['id']
    rows = sheets_api.spreadsheets().values().get(
        spreadsheetId=sid, range='A2:H').execute().get('values', [])

    def cell(row, i):
        return row[i].strip() if i < len(row) and row[i] is not None else ''

    info = {}
    for row in rows:
        fname = cell(row, 0)
        if not fname or fname.startswith('('):  # skip the placeholder helper rows
            continue
        year = cell(row, 3)
        info[match_key(fname)] = {
            'where': cell(row, 1) or None,   # Homepage / Paintings / a show name
            'title': cell(row, 2) or None,
            'year': int(re.search(r'\d{4}', year).group(0)) if re.search(r'\d{4}', year) else None,
            'medium': cell(row, 4) or None,
            'dimensions': cell(row, 5) or None,
            'status': cell(row, 6) or None,
            'show': cell(row, 7) or None,
        }
    print(f'  read {len(info)} info row(s) from "{INFO_SHEET_NAME}".')
    return info


def resolve_destination(row, show_lookup):
    """Turn Omar's "Where on site" cell into an action. Returns one of:
      ('homepage', None)      -> add the image to the homepage hero list
      ('show', <slug>)        -> attach the work to that exhibition
      ('paintings', None)     -> normal: just the paintings gallery
    The 'Which show' column (H) still works too and wins if 'where' names a show.
    Unrecognized text falls back to 'paintings' so a typo never hides a photo."""
    norm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
    # An explicit show in column H takes precedence.
    if row.get('show') and show_lookup.get(norm(row['show'])):
        return ('show', show_lookup[norm(row['show'])])
    where = norm(row.get('where'))
    if where in ('homepage', 'home', 'frontpage', 'titlepage', 'mainpage', 'landing'):
        return ('homepage', None)
    if where and where not in ('paintings', 'painting', 'gallery', 'work', 'works'):
        slug = show_lookup.get(where)  # maybe they typed a show name in column B
        if slug:
            return ('show', slug)
    return ('paintings', None)


def apply_info(work, row, show_lookup):
    """Overlay non-empty sheet values onto a work dict. Returns True if it changed
    anything. Only fields Omar actually filled are touched — a blank cell never
    wipes existing data. Also honors the "Where on site" routing for shows (the
    homepage list is rebuilt separately in main(), not here)."""
    changed = False
    for field in ('title', 'year', 'medium', 'dimensions', 'status'):
        val = row.get(field)
        if val not in (None, '') and work.get(field) != val:
            work[field] = val
            changed = True
    dest, slug = resolve_destination(row, show_lookup)
    if dest == 'show' and work.get('showSlug') != slug:
        work['showSlug'] = slug
        changed = True
    return changed


def list_drive_images(drive):
    files, token = [], None
    while True:
        resp = drive.files().list(
            q=f"'{FOLDER_ID}' in parents and trashed = false",
            fields='nextPageToken, files(id, name, mimeType, size)',
            pageToken=token,
        ).execute()
        files += resp.get('files', [])
        token = resp.get('nextPageToken')
        if not token:
            break
    return [f for f in files if os.path.splitext(f['name'])[1].lower() in IMAGE_EXT]


def download(drive, file_id, dest):
    with open(dest, 'wb') as fh:
        req = drive.files().get_media(fileId=file_id)
        dl = MediaIoBaseDownload(fh, req)
        done = False
        while not done:
            _, done = dl.next_chunk()


def to_web_jpeg(src, dest):
    img = Image.open(src)
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    img.thumbnail((MAX_SIDE, MAX_SIDE))  # no-op when already smaller
    img.save(dest, 'JPEG', quality=JPEG_QUALITY, optimize=True)


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-push', action='store_true')
    args = ap.parse_args()

    drive = service('personal', 'drive', 'drive', 'v3')
    sheets_api = service('personal', 'drive', 'sheets', 'v4')  # drive-scope token covers Sheets
    images = list_drive_images(drive)
    print(f"Drive folder has {len(images)} image file(s).")

    os.makedirs(UPLOADS, exist_ok=True)
    with open(SITE_DATA, encoding='utf-8') as f:
        data = json.load(f)
    known_slugs = {w['slug'] for w in data.get('works', [])}

    info = read_info_sheet(sheets_api, drive)  # {match_key: {title, year, ...}}
    show_lookup = load_show_lookup(data)
    # Remember each work's match key so sheet edits can find already-synced works.
    key_to_work = {match_key(w['slug']): w for w in data.get('works', [])}

    added = []      # newly-downloaded photos
    for f in images:
        stem, ext = os.path.splitext(f['name'])
        slug = slugify(stem)
        out_path = os.path.join(UPLOADS, f'{slug}.jpg')
        if os.path.exists(out_path):
            continue
        if ext.lower() == '.heic' and not HEIC_OK:
            print(f"  SKIP (install pillow-heif for iPhone photos): {f['name']}")
            continue
        print(f"  new: {f['name']} -> uploads/{slug}.jpg")
        if args.dry_run:
            added.append(slug)
            continue
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = tmp.name
        try:
            download(drive, f['id'], tmp_path)
            to_web_jpeg(tmp_path, out_path)
        finally:
            os.unlink(tmp_path)
        if slug not in known_slugs:
            row = info.get(match_key(f['name']), {})
            work = {
                'slug': slug,
                'title': row.get('title') or prettify(stem),
                'year': row.get('year') if row.get('year') is not None else year_of(stem),
                'medium': row.get('medium') or '',
                'dimensions': row.get('dimensions') or '',
                'image': f'/uploads/{slug}.jpg',
                'status': row.get('status'),
                'surface': None,
                'tier': None,
                'showSlug': None,
                'sort_order': -1,  # newest first until curated
            }
            dest, show_slug = resolve_destination(row, show_lookup)
            if dest == 'show':
                work['showSlug'] = show_slug
            data['works'].insert(0, work)
            known_slugs.add(slug)
            key_to_work[match_key(slug)] = work
        added.append(slug)

    # Second pass: apply sheet edits to works that already existed (so Omar can
    # correct a painting's title/year/medium/size/status/show without re-uploading).
    edited = 0
    for key, row in info.items():
        work = key_to_work.get(key)
        if work and match_key(work['slug']) not in {match_key(s) for s in added}:
            if not args.dry_run and apply_info(work, row, show_lookup):
                edited += 1
    if edited:
        print(f'  updated info on {edited} existing work(s) from the sheet.')

    # Rebuild the homepage hero list from every photo Omar tagged "Homepage".
    # Only touch heroImages if he has tagged at least one — otherwise his current
    # hand-picked lead images (the "Vancouver airport" set) stay untouched.
    hero_changed = False
    hero_imgs = []
    for key, row in info.items():
        dest, _ = resolve_destination(row, show_lookup)
        if dest == 'homepage':
            w = key_to_work.get(key)
            if w and w.get('image') and w['image'] not in hero_imgs:
                hero_imgs.append(w['image'])
    if hero_imgs and hero_imgs != data.get('heroImages'):
        if not args.dry_run:
            data['heroImages'] = hero_imgs
        hero_changed = True
        print(f'  homepage lead images set to {len(hero_imgs)} tagged photo(s).')

    if not added and not edited and not hero_changed:
        print('Nothing new — site already up to date.')
        return
    if args.dry_run:
        print(f'DRY RUN: would add {len(added)} work(s).')
        return

    with open(SITE_DATA, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    parts = []
    if added:
        parts.append(f"add {len(added)} new painting photo(s)")
    if edited:
        parts.append(f"update info on {edited} work(s)")
    if hero_changed:
        parts.append(f"set {len(hero_imgs)} homepage image(s)")
    msg = "Sync Omar's Drive folder: " + " + ".join(parts)
    run(['git', 'add', 'content/site-data.json', 'public/uploads'], APP_DIR)
    run(['git', 'commit', '-m', msg], APP_DIR)
    if args.no_push:
        print(f'Committed: {msg[len("Sync Omar\'s Drive folder: "):]}; push skipped (--no-push).')
        return
    run(['git', 'push', 'origin', 'main'], APP_DIR)
    print(f'Pushed ({" + ".join(parts)}) — GitHub Pages will redeploy in ~2 minutes.')


if __name__ == '__main__':
    main()
