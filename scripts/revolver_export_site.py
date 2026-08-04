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
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from google_auth import service  # noqa: E402
from revolver_stories import find_or_create_sheet, load_state  # noqa: E402

SITE_DIR = os.environ.get(
    'REVOLVER_SITE_DIR', r'c:\Propcheck Git\clone\Revolver')
OUT_FILE = os.path.join(SITE_DIR, 'data', 'feed.json')

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
    low = text.lower()
    for name, keys in SECTIONS:
        if any(k in low for k in keys):
            return name
    return 'Politics'


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
    for r in rows(sheets, sid, 'Stories!A2:E'):
        headline, url = cell(r, 1), cell(r, 4)
        if not headline or not url:
            continue
        stories.append({
            'pulled': cell(r, 0),
            'headline': headline,
            'source': cell(r, 2),
            'blurb': cell(r, 3),
            'url': url,
            'section': classify(f'{headline} {cell(r, 3)}'),
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
