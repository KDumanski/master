"""
Export the "Revolver News stories" sheet -> the static site's data file.

The site (clone/Revolver) is plain HTML/CSS/JS on GitHub Pages, so it cannot
call the Sheets API with a private token. Instead this writes a small JSON
feed into the site repo; committing that file is what publishes an update.

  python scripts/revolver_export_site.py            # write data/feed.json
  python scripts/revolver_export_site.py --stdout   # print, write nothing

Run it after a sweep (or on a schedule) and push the site repo.
"""
import argparse
import concurrent.futures
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from google_auth import service  # noqa: E402
from revolver_stories import find_or_create_sheet, load_state  # noqa: E402

SITE_DIR = os.environ.get(
    'REVOLVER_SITE_DIR', r'c:\Propcheck Git\clone\Revolver')
OUT_FILE = os.path.join(SITE_DIR, 'data', 'feed.json')
# url -> og:image (or "" for a known miss, so failures aren't refetched daily).
IMG_CACHE = os.path.join(SITE_DIR, 'data', 'images.json')
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
     '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

# Keyword -> section. First match wins, so order matters: narrower topics sit
# above the catch-alls. Sections drive the site's filter chips.
SECTIONS = [
    ('Immigration', ['migrant', 'immigra', 'border', 'ice ', 'deport', 'asylum',
                     'illegal alien', 'ceuta']),
    ('Fauci & COVID', ['fauci', 'covid', 'pandemic', 'vaccine', 'birx',
                       'ivermectin', 'lockdown']),
    ('Foreign policy', ['iran', 'israel', 'gaza', 'hamas', 'ukraine', 'russia',
                        'china', 'nato', 'houthi', 'tehran', 'war']),
    ('Elections', ['voter', 'ballot', 'election', 'midterm', 'primary',
                   'senate seat', 'poll']),
    ('Crime & courts', ['arrest', 'convicted', 'shooting', 'police', 'sentenced',
                        'lawsuit', 'sue', 'doj', 'fbi', 'prosecut', 'indicted',
                        'terror', 'investigation']),
    ('Culture war', ['trans', 'lgbt', 'gender', 'woke', 'dei', 'wnba', 'school',
                     'church', 'catholic', 'abortion', 'pride']),
    ('Economy', ['inflation', 'fed', 'rates', 'market', 'stock', 'econom',
                 'debt', 'tariff', 'gold', 'earnings', 'profit', 'price']),
    ('Media', ['cnn', 'msnbc', 'reporter', 'anchor', 'media', 'broadcast',
               'podcast', 'newsroom']),
]


def classify(text):
    """All matching sections in priority order (max 3); first is primary."""
    low = text.lower()
    hits = [name for name, keys in SECTIONS if any(k in low for k in keys)]
    return (hits or ['Politics'])[:3]


def _og_image(url):
    """Best-effort og:image / twitter:image from an article page."""
    try:
        r = requests.get(url, headers={'User-Agent': UA}, timeout=10)
        if r.status_code != 200:
            return ''
        head = r.text[:250000]
        for pat in (
            r'<meta[^>]+property=["\']og:image["\'][^>]*content=["\']([^"\']+)',
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*property=["\']og:image',
            r'<meta[^>]+name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)',
        ):
            m = re.search(pat, head, re.I)
            if m:
                img = m.group(1).strip().replace('&amp;', '&')
                if img.startswith('//'):
                    img = 'https:' + img
                if img.startswith('http'):
                    return img
        return ''
    except requests.RequestException:
        return ''


def enrich_images(stories):
    """Attach `image` to each story, fetching only URLs the cache hasn't seen."""
    try:
        with open(IMG_CACHE, encoding='utf-8') as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}
    todo = [s['url'] for s in stories if s['url'] not in cache]
    if todo:
        print(f'Fetching og:image for {len(todo)} new stories ...')
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            for url, img in zip(todo, ex.map(_og_image, todo)):
                cache[url] = img
        os.makedirs(os.path.dirname(IMG_CACHE), exist_ok=True)
        with open(IMG_CACHE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=0)
    hits = 0
    for s in stories:
        s['image'] = cache.get(s['url'], '')
        hits += 1 if s['image'] else 0
    print(f'  images: {hits}/{len(stories)} stories have one')


def rows(sheets, sid, rng):
    return sheets.spreadsheets().values().get(
        spreadsheetId=sid, range=rng).execute().get('values', [])


def cell(row, i):
    return row[i].strip() if len(row) > i and row[i] else ''


def main():
    ap = argparse.ArgumentParser(description='Export sheet -> site feed.json')
    ap.add_argument('--stdout', action='store_true', help='print instead of write')
    args = ap.parse_args()

    state = load_state()
    sheets, sid = find_or_create_sheet(state)

    stories = []
    for r in rows(sheets, sid, 'Stories!A2:G'):
        headline, url = cell(r, 1), cell(r, 4)
        if not headline or not url:
            continue
        secs = classify(f'{headline} {cell(r, 3)}')
        stories.append({
            'pulled': cell(r, 0),
            'headline': headline,
            'source': cell(r, 2),
            'blurb': cell(r, 3),
            'url': url,
            'section': secs[0],     # primary (back-compat)
            'sections': secs,       # all, for multi-chip display + filtering
            'summary': cell(r, 5),  # AI editorial read, shown on hover
            'tags': [t.strip() for t in cell(r, 6).split(',') if t.strip()],
        })

    social = []
    for r in rows(sheets, sid, 'Social!A2:D'):
        text, url = cell(r, 2), cell(r, 3)
        if not text or not url:
            continue
        account = cell(r, 1)
        handle = account.split('(@')[-1].rstrip(')') if '(@' in account else ''
        social.append({
            'pulled': cell(r, 0),
            'account': account.split(' (@')[0],
            'handle': handle,
            'text': text,
            'url': url,
        })

    accounts = []
    for r in rows(sheets, sid, 'Accounts!A2:D'):
        if not cell(r, 0):
            continue
        try:
            n = int(cell(r, 1) or 0)
        except ValueError:
            n = 0
        accounts.append({'handle': cell(r, 0).lstrip('@'), 'count': n,
                         'last': cell(r, 2), 'url': cell(r, 3)})

    runs = [{'pulled': cell(r, 0), 'status': cell(r, 4)}
            for r in rows(sheets, sid, 'Runs!A2:E') if cell(r, 0)]

    enrich_images(stories)

    feed = {
        'generated': f'{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}',
        'counts': {'stories': len(stories), 'social': len(social),
                   'accounts': len(accounts), 'runs': len(runs)},
        'sections': [s for s, _ in SECTIONS] + ['Politics'],
        'sources': [s for s, _ in Counter(x['source'] for x in stories).most_common()],
        'last_pull': runs[0]['pulled'] if runs else (
            stories[0]['pulled'] if stories else ''),
        'stories': stories,
        'social': social,
        'accounts': accounts,
    }

    if args.stdout:
        print(json.dumps(feed, indent=1)[:2000])
        return

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(feed, f, ensure_ascii=False, separators=(',', ':'))
    kb = os.path.getsize(OUT_FILE) / 1024
    print(f'Wrote {OUT_FILE} ({kb:.1f} KB)')
    print(f"  {feed['counts']['stories']} stories, {feed['counts']['social']} posts, "
          f"{feed['counts']['accounts']} accounts")
    tally = Counter(s['section'] for s in stories)
    print('  sections: ' + ', '.join(f'{k} {v}' for k, v in tally.most_common()))


if __name__ == '__main__':
    main()
