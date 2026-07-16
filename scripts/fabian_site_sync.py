"""
Oceanic Ventures (Fabian) — Drive photo sync.

Fabian drops photos into the shared Drive folder "Oceanic Ventures — Website Assets"
(he already has writer access). This pulls anything new, converts it to a web-ready
JPEG, commits it into the site repo, and pushes — which triggers the GitHub Pages
deploy. The site is fully static (KDumanski/fabians-tours); this script IS his upload
path, running where the Drive OAuth tokens live (masters/.secrets/).

HOW HE CONTROLS WHERE A PHOTO LANDS — by the filename:

  1. Name it after a SLOT to replace that stock image everywhere it appears:
       gizaPyramids.jpg   dolphins.jpg   redSea.jpg   karnak.jpg   nileFelucca.jpg ...
     (full list: SLOTS below — these are the keys in the site's lib/images.js)

  2. Name it after a JOURNEY SLUG to set that journey's hero image:
       eclipse-dolphin-journey.jpg   wild-dolphins-red-sea.jpg  ...

  3. Anything else just lands in the gallery pool (public/photos/) for later use.

Usage:
  python scripts/fabian_site_sync.py             # sync + commit + push
  python scripts/fabian_site_sync.py --dry-run   # show what would happen
  python scripts/fabian_site_sync.py --no-push   # sync + commit, don't push

Idempotent: a Drive file is skipped once its converted JPEG already exists.
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

try:  # iPhone photos
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_OK = True
except ImportError:
    HEIC_OK = False

# Fabian shares his photos back via his OWN folder, not the one we created for him.
# "New Website photos for Keith" (owned by fabianguhl@gmail.com, shared 2026-07-14).
FOLDER_ID = '14dDJp9wtC8sf9QMwxdhK8My52-4lYZ6C'
APP_DIR = r'c:\Propcheck Git\clone\Fabians Tours'
PHOTOS = os.path.join(APP_DIR, 'public', 'photos')
OVERRIDES = os.path.join(APP_DIR, 'lib', 'imageOverrides.json')

IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.heic'}
MAX_SIDE = 2400
QUALITY = 86

# The image slots in lib/images.js — naming a file after one of these replaces that
# stock photo across the whole site.
SLOTS = [
    'gizaPyramids', 'sphinx', 'pyramidDusk', 'camelGiza',
    'nileFelucca', 'nileSunset', 'aswan',
    'karnak', 'luxorTemple', 'abuSimbel', 'hieroglyphs', 'templeColumns',
    'redSea', 'diving', 'dolphins', 'coral',
    'cairoBazaar', 'egyptDesert', 'scarab', 'goldMask',
    'desertCaravan', 'starsDesert',
]
SLOT_BY_LOWER = {s.lower(): s for s in SLOTS}

# Journey slugs — naming a file after one sets that journey's hero image.
JOURNEYS = [
    'eclipse-dolphin-journey', 'pre-eclipse-dolphin-journey', 'post-eclipse-dolphin-journey',
    'river-of-remembering', 'complete-egypt-initiation', 'wild-dolphins-red-sea',
    'ancient-temples-river-pilgrimage', 'somatic-water-therapy-training',
]


def slugify(stem):
    return re.sub(r'[^a-z0-9]+', '-', stem.lower()).strip('-') or 'photo'


def classify(stem):
    """Return (kind, key) from the filename: a slot, a journey, or the gallery pool."""
    bare = re.sub(r'[^a-z0-9]', '', stem.lower())
    if bare in SLOT_BY_LOWER:
        return 'slot', SLOT_BY_LOWER[bare]
    slug = slugify(stem)
    if slug in JOURNEYS:
        return 'journey', slug
    return 'gallery', slug


def list_images(drive):
    files, token = [], None
    while True:
        r = drive.files().list(
            q=f"'{FOLDER_ID}' in parents and trashed = false",
            fields='nextPageToken, files(id, name, mimeType, size)',
            pageToken=token, supportsAllDrives=True, includeItemsFromAllDrives=True,
        ).execute()
        files += r.get('files', [])
        token = r.get('nextPageToken')
        if not token:
            break
    return [f for f in files if os.path.splitext(f['name'])[1].lower() in IMAGE_EXT]


def download(drive, fid, dest):
    with open(dest, 'wb') as fh:
        dl = MediaIoBaseDownload(fh, drive.files().get_media(fileId=fid))
        done = False
        while not done:
            _, done = dl.next_chunk()


def to_web_jpeg(src, dest):
    img = Image.open(src)
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    img.save(dest, 'JPEG', quality=QUALITY, optimize=True)


def run(cmd):
    r = subprocess.run(cmd, cwd=APP_DIR, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-push', action='store_true')
    args = ap.parse_args()

    drive = service('personal', 'drive', 'drive', 'v3')
    images = list_images(drive)
    print(f"Drive folder has {len(images)} image file(s).")

    os.makedirs(PHOTOS, exist_ok=True)
    overrides = {}
    if os.path.exists(OVERRIDES):
        with open(OVERRIDES, encoding='utf-8') as f:
            overrides = json.load(f)
    overrides.setdefault('slots', {})    # imageKey -> /photos/x.jpg
    overrides.setdefault('journeys', {})  # slug -> /photos/x.jpg

    added = []
    for f in images:
        stem, ext = os.path.splitext(f['name'])
        kind, key = classify(stem)
        out_name = f'{slugify(stem)}.jpg'
        out_path = os.path.join(PHOTOS, out_name)
        if os.path.exists(out_path):
            continue
        if ext.lower() == '.heic' and not HEIC_OK:
            print(f"  SKIP (pip install pillow-heif for iPhone photos): {f['name']}")
            continue
        print(f"  new: {f['name']}  ->  photos/{out_name}   [{kind}: {key}]")
        if args.dry_run:
            added.append(out_name)
            continue
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = tmp.name
        try:
            download(drive, f['id'], tmp_path)
            to_web_jpeg(tmp_path, out_path)
        finally:
            os.unlink(tmp_path)
        web = f'/photos/{out_name}'
        if kind == 'slot':
            overrides['slots'][key] = web
        elif kind == 'journey':
            overrides['journeys'][key] = web
        added.append(out_name)

    if not added:
        print('Nothing new — site already up to date.')
        return
    if args.dry_run:
        print(f'DRY RUN: would add {len(added)} photo(s).')
        return

    with open(OVERRIDES, 'w', encoding='utf-8') as f:
        json.dump(overrides, f, ensure_ascii=False, indent=2)

    run(['git', 'add', 'public/photos', 'lib/imageOverrides.json'])
    run(['git', 'commit', '-m', f"Sync {len(added)} photo(s) from Fabian's Drive folder"])
    if args.no_push:
        print(f'Committed {len(added)} photo(s); push skipped (--no-push).')
        return
    run(['git', 'push', 'origin', 'HEAD:main'])
    print(f'Pushed {len(added)} photo(s) — the site redeploys in ~2 minutes.')


if __name__ == '__main__':
    main()
