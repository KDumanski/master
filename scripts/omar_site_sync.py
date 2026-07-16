"""
Omar Chacón site — Drive photo sync.

Omar drops painting photos into the shared Drive folder "Omar Website Photos";
this script pulls anything new, converts it to a web-ready JPEG (max 2400px,
TIFF/PNG/HEIC handled), registers it as a work in the site's content file, and
pushes — which triggers the GitHub Pages deploy. The site itself is fully
static (KDumanski/Omar-art-website); this local script IS the upload pipeline,
running where the Drive OAuth tokens already live (masters/.secrets/).

Usage:
  python scripts/omar_site_sync.py            # sync + commit + push
  python scripts/omar_site_sync.py --dry-run  # show what would happen
  python scripts/omar_site_sync.py --no-push  # sync + commit, don't push

Idempotent: a Drive file is skipped when its slug already has a JPEG in
public/uploads/. New works land at the top of the Paintings page (year taken
from a 4-digit number in the filename when present).
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
APP_DIR = r'c:\Propcheck Git\clone\Omar-app'
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
    images = list_drive_images(drive)
    print(f"Drive folder has {len(images)} image file(s).")

    os.makedirs(UPLOADS, exist_ok=True)
    with open(SITE_DATA, encoding='utf-8') as f:
        data = json.load(f)
    known_slugs = {w['slug'] for w in data.get('works', [])}

    added = []
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
            data['works'].insert(0, {
                'slug': slug,
                'title': prettify(stem),
                'year': year_of(stem),
                'medium': '',
                'dimensions': '',
                'image': f'/uploads/{slug}.jpg',
                'status': None,
                'surface': None,
                'tier': None,
                'showSlug': None,
                'sort_order': -1,  # newest first until curated
            })
            known_slugs.add(slug)
        added.append(slug)

    if not added:
        print('Nothing new — site already up to date.')
        return
    if args.dry_run:
        print(f'DRY RUN: would add {len(added)} work(s).')
        return

    with open(SITE_DATA, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    run(['git', 'add', 'content/site-data.json', 'public/uploads'], APP_DIR)
    run(['git', 'commit', '-m',
         f"Sync {len(added)} new painting photo(s) from Omar's Drive folder"], APP_DIR)
    if args.no_push:
        print(f'Committed {len(added)} new work(s); push skipped (--no-push).')
        return
    run(['git', 'push', 'origin', 'main'], APP_DIR)
    print(f'Pushed {len(added)} new work(s) — GitHub Pages will redeploy in ~2 minutes.')


if __name__ == '__main__':
    main()
