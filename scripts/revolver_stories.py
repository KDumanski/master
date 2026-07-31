"""
Revolver News stories — morning source sweep -> Google Doc.

Every morning this script:
  1. Fetches revolver.news (Drudge-style aggregator) to snapshot the headlines
     it is currently running: that gives the topic mix AND the editorial voice.
  2. Pulls fresh stories from the RSS feeds of the outlets Revolver actually
     links out to (NY Post, Fox, Breitbart, Zero Hedge, Headline USA, etc.).
  3. Collects the X/Twitter posts Revolver links (tweet text via the public
     oEmbed endpoint, no API key) and keeps a running roster of the accounts
     it surveys (top 200 by link count, grows daily).
  4. Has Claude pick the candidates that fit Revolver's editorial profile and
     write a one-line blurb for each in the same punchy voice (trailing "...",
     no em dashes).
  5. Pushes everything to the Google SHEET "Revolver News stories" (tabs:
     Stories / Social / Accounts, newest rows on top) AND prepends the dated
     Story | Description table to the Google Doc of the same name.

Usage:
  python scripts/revolver_stories.py           # full run, writes the doc
  python scripts/revolver_stories.py --test    # 3 sources, print only, no doc
  python scripts/revolver_stories.py --no-doc  # full scrape+blurbs, print only

State: .revolver_seen.json (next to this script, gitignored) remembers URLs
already published so the same story never lands in the doc twice.

Anthropic key: ANTHROPIC_API_KEY env var, else read from etls/.env.
Google auth: personal Drive token via google_auth.py (full drive scope covers
the Docs API, so no new consent is needed).
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from google_auth import service  # noqa: E402

import feedparser  # noqa: E402
import requests  # noqa: E402

DOC_NAME = 'Revolver News stories'
SEEN_FILE = os.path.join(SCRIPT_DIR, '.revolver_seen.json')
ETLS_ENV = r'c:\Propcheck Git\etls\.env'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

MAX_AGE_HOURS = 36        # ignore feed entries older than this
MAX_PER_SOURCE = 25       # candidates taken per outlet
MAX_CANDIDATES = 400      # hard cap sent to Claude
TARGET_STORIES = '30-50'  # how many stories Claude should pick
TOP_ACCOUNTS = 200        # roster size on the Accounts tab

# The outlets revolver.news links out to most (measured from its front page).
# Each source lists feed URLs to try in order; first one that parses wins.
SOURCES = {
    'NY Post':          ['https://nypost.com/feed/'],
    'Fox News':         ['https://moxie.foxnews.com/google-publisher/latest.xml',
                         'https://www.foxnews.com/rss'],
    'Breitbart':        ['https://www.breitbart.com/feed/'],
    'Zero Hedge':       ['https://cms.zerohedge.com/fullrss2.xml',
                         'https://feeds.feedburner.com/zerohedge/feed'],
    'Headline USA':     ['https://headlineusa.com/feed/'],
    # Western Journal blocks non-browser fetches outright; kept in case that
    # changes — a failed feed is skipped gracefully.
    'Western Journal':  ['https://www.westernjournal.com/feed/'],
    'Just The News':    ['https://justthenews.com/rss.xml',
                         'https://justthenews.com/feed'],
    'Daily Wire':       ['https://www.dailywire.com/feeds/rss.xml',
                         'https://www.dailywire.com/rss.xml'],
    'Slay News':        ['https://slaynews.com/feed/'],
    'Daily Caller':     ['https://dailycaller.com/feed/'],
    'CNBC':             ['https://search.cnbc.com/rs/search/combinedcms/view.xml'
                         '?partnerId=wrss01&id=100003114'],
    'American Thinker': ['https://feeds.feedburner.com/americanthinker'],
    'BizPac Review':    ['https://www.bizpacreview.com/feed/'],
    'LifeSiteNews':     ['https://www.lifesitenews.com/feed/'],
    'Mediaite':         ['https://www.mediaite.com/feed/'],
    'Discern Report':   ['https://discernreport.com/feed/'],
}


# ---------------------------------------------------------------- fetching

def fetch_url(url, timeout=30):
    """GET with a browser UA; Cloudflare-fronted sites 403 python's TLS
    fingerprint sometimes, so fall back to curl (which revolver.news accepts)."""
    try:
        r = requests.get(url, headers={'User-Agent': UA}, timeout=timeout)
        if r.status_code == 200:
            return r.text
    except requests.RequestException:
        pass
    try:
        out = subprocess.run(
            ['curl', '-sL', '--max-time', str(timeout), '-A', UA, url],
            capture_output=True, timeout=timeout + 10)
        if out.returncode == 0 and out.stdout:
            return out.stdout.decode('utf-8', errors='ignore')
    except (subprocess.SubprocessError, OSError):
        pass
    return None


SKIP_DOMAINS = ('revolver.news', 'x.com', 'twitter.com', 'youtube.com',
                'gab.com', 'gettr.com', 'archive.md', 'cloudflare.com',
                'twc.health', 'msn.com', 'aol.com', 'yahoo.com')


NOT_HANDLES = {'intent', 'share', 'home', 'hashtag', 'i', 'search', 'compose'}


def revolver_snapshot():
    """One pass over the revolver.news front page. Returns:
    heads          — external headlines (topic + voice reference for Claude)
    social_urls    — x.com / twitter.com status links Revolver is running
    handle_counts  — every X account linked this morning, with counts
    """
    html_text = fetch_url('https://revolver.news/')
    if not html_text:
        return [], [], {}
    heads, social_urls, handle_counts = [], [], {}
    for url, text in re.findall(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                                html_text, re.S):
        m = re.match(r'https?://(?:www\.)?(?:x|twitter)\.com/([A-Za-z0-9_]+)(/status/\d+)?',
                     url)
        if m:
            handle = m.group(1)
            if handle.lower() not in NOT_HANDLES:
                handle_counts[handle] = handle_counts.get(handle, 0) + 1
                if m.group(2):
                    clean = f'https://x.com/{handle}{m.group(2)}'
                    if clean not in social_urls:
                        social_urls.append(clean)
            continue
        if any(d in url for d in SKIP_DOMAINS):
            continue
        t = re.sub(r'<[^>]+>', '', text)
        t = re.sub(r'\s+', ' ', t).strip()
        t = (t.replace('&#8230;', '...').replace('&#8217;', "'")
              .replace('&#8216;', "'").replace('&#8220;', '"')
              .replace('&#8221;', '"').replace('&amp;', '&')
              .replace('&#8211;', '-').replace('&#8212;', '-'))
        if len(t) > 25 and t not in heads:
            heads.append(t)
    return heads[:45], social_urls, handle_counts


def fetch_social_posts(social_urls, seen_social):
    """Tweet text for each linked post via Twitter's public oEmbed endpoint
    (works without an X API key for public tweets)."""
    import html as html_mod
    posts = []
    for url in social_urls:
        if url in seen_social:
            continue
        try:
            r = requests.get(
                'https://publish.twitter.com/oembed',
                params={'url': url.replace('x.com', 'twitter.com'),
                        'omit_script': 'true', 'dnt': 'true'},
                headers={'User-Agent': UA}, timeout=20)
            if r.status_code != 200:
                continue
            d = r.json()
            text = re.sub(r'<[^>]+>', ' ', d.get('html', ''))
            text = html_mod.unescape(re.sub(r'\s+', ' ', text)).strip()
            # oEmbed appends "— Author (@handle) <date>"; the columns carry that.
            text = re.split(r'—\s*[^—]*\(@', text)[0].strip()
            handle = re.match(r'https://x\.com/([A-Za-z0-9_]+)/', url).group(1)
            posts.append({'account': d.get('author_name') or handle,
                          'handle': handle, 'text': text[:400], 'url': url})
        except (requests.RequestException, ValueError, AttributeError):
            continue
    return posts


def collect_candidates(sources, seen_urls):
    """Pull fresh entries from every source feed."""
    now = time.time()
    candidates, feed_report = [], []
    for name, feed_urls in sources.items():
        entries = []
        for fu in feed_urls:
            raw = fetch_url(fu)
            if not raw:
                continue
            parsed = feedparser.parse(raw)
            if parsed.entries:
                entries = parsed.entries
                break
        if not entries:
            feed_report.append(f'  {name}: FEED FAILED')
            continue
        kept = 0
        for e in entries:
            link = (e.get('link') or '').strip()
            title = re.sub(r'\s+', ' ', e.get('title') or '').strip()
            if not link or not title or link in seen_urls:
                continue
            ts = e.get('published_parsed') or e.get('updated_parsed')
            if ts and (now - time.mktime(ts)) > MAX_AGE_HOURS * 3600:
                continue
            summary = re.sub(r'<[^>]+>', '', e.get('summary') or '')
            summary = re.sub(r'\s+', ' ', summary).strip()[:160]
            candidates.append({'source': name, 'headline': title,
                               'url': link, 'summary': summary})
            kept += 1
            if kept >= MAX_PER_SOURCE:
                break
        feed_report.append(f'  {name}: {kept} fresh')
    return candidates[:MAX_CANDIDATES], feed_report


# ---------------------------------------------------------------- Claude

def anthropic_key():
    key = os.environ.get('ANTHROPIC_API_KEY')
    if key:
        return key
    for env_file in (ETLS_ENV, r'c:\Propcheck Git\front-end\web\.env'):
        try:
            with open(env_file, encoding='utf-8') as f:
                for line in f:
                    m = re.match(r'\s*ANTHROPIC_API_KEY\s*=\s*(\S+)', line)
                    if m and m.group(1):
                        return m.group(1)
        except OSError:
            continue
    raise RuntimeError('No ANTHROPIC_API_KEY in env, etls/.env, or front-end/web/.env')


STORY_SCHEMA = {
    'type': 'object',
    'additionalProperties': False,
    'required': ['stories'],
    'properties': {
        'stories': {
            'type': 'array',
            'items': {
                'type': 'object',
                'additionalProperties': False,
                'required': ['headline', 'url', 'source', 'blurb'],
                'properties': {
                    'headline': {'type': 'string'},
                    'url': {'type': 'string'},
                    'source': {'type': 'string'},
                    'blurb': {'type': 'string'},
                },
            },
        },
    },
}


def pick_and_blurb(revolver_heads, candidates):
    """Claude selects the on-profile stories and writes Revolver-voice blurbs."""
    import anthropic
    client = anthropic.Anthropic(api_key=anthropic_key())

    ref = '\n'.join(f'- {h}' for h in revolver_heads) or '(homepage unreachable today)'
    cand = '\n'.join(
        f'{i}. [{c["source"]}] {c["headline"]} | {c["url"]}'
        + (f' | {c["summary"]}' if c['summary'] else '')
        for i, c in enumerate(candidates, 1))

    prompt = f"""You are the morning editor of a Drudge-style news aggregator modeled on revolver.news.

SECTION A - the headlines currently running on revolver.news (this is your reference for BOTH the topic mix and the editorial voice):
{ref}

SECTION B - candidate stories pulled this morning from the source outlets' RSS feeds:
{cand}

Select the {TARGET_STORIES} candidates from SECTION B that best fit the aggregator's editorial profile shown in SECTION A: politics, immigration, crime, DOJ/FBI, culture-war fights, foreign policy, economy, media criticism, plus the occasional offbeat or big mainstream story. When several outlets carry the same underlying story, keep only the single strongest version. Skip pure celebrity filler, sports scores, and product/deal posts.

For each selected story write "blurb": a one-line description in the same voice as the SECTION A headlines. Rules for blurbs:
- punchy, wry, populist-right editorial framing, like the SECTION A examples
- under 25 words, sentence case, and it must end with "..."
- never use an em dash or double hyphen anywhere; use a comma or period instead
- do not just copy the headline; rewrite it the way this site would tease it

Copy "headline", "url" and "source" for each pick exactly as given in SECTION B."""

    # Per current Anthropic guidance, Opus 5 calls opt into server-side
    # refusal fallbacks by default; fall back to a plain call if the beta
    # surface rejects the combination.
    try:
        try:
            resp = client.beta.messages.create(
                model='claude-opus-5',
                max_tokens=16000,
                betas=['server-side-fallback-2026-07-01'],
                fallbacks='default',
                output_config={'format': {'type': 'json_schema', 'schema': STORY_SCHEMA}},
                messages=[{'role': 'user', 'content': prompt}],
            )
        except (TypeError, anthropic.BadRequestError):
            # Older SDKs don't know `fallbacks`; the API may also reject the combo.
            resp = client.messages.create(
                model='claude-opus-5',
                max_tokens=16000,
                output_config={'format': {'type': 'json_schema', 'schema': STORY_SCHEMA}},
                messages=[{'role': 'user', 'content': prompt}],
            )
    except anthropic.AuthenticationError:
        raise RuntimeError(
            'Anthropic API key rejected (401). The keys in etls/.env and '
            'front-end/web/.env were revoked after the July 2026 secrets '
            'exposure. Create a fresh key at https://console.anthropic.com/ '
            'and update ANTHROPIC_API_KEY in etls/.env, then re-run.')

    if resp.stop_reason == 'refusal':
        raise RuntimeError('Claude declined the selection request (refusal)')
    text = ''.join(b.text for b in resp.content if b.type == 'text')
    stories = json.loads(text)['stories']
    # Belt and braces on the two hard style rules.
    for s in stories:
        s['blurb'] = s['blurb'].replace('\u2014', ', ').replace('--', ',').strip()
        if not s['blurb'].endswith('...'):
            s['blurb'] = s['blurb'].rstrip('.') + '...'
    return stories


# ---------------------------------------------------------------- Google Doc

def load_state():
    try:
        with open(SEEN_FILE, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {'doc_id': None, 'seen': []}


def save_state(state):
    state['seen'] = state.get('seen', [])[-1500:]
    state['seen_social'] = state.get('seen_social', [])[-1000:]
    with open(SEEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=1)


def find_or_create_doc(state):
    docs = service('personal', 'drive', 'docs', 'v1')
    drive = service('personal', 'drive', 'drive', 'v3')
    if state.get('doc_id'):
        try:
            docs.documents().get(documentId=state['doc_id'],
                                 fields='documentId').execute()
            return docs, state['doc_id']
        except Exception:
            pass
    hits = drive.files().list(
        q=f"name = '{DOC_NAME}' and mimeType = 'application/vnd.google-apps.document' "
          "and trashed = false",
        fields='files(id)', pageSize=1).execute().get('files', [])
    if hits:
        doc_id = hits[0]['id']
    else:
        doc_id = docs.documents().create(body={'title': DOC_NAME}).execute()['documentId']
        print(f'Created new Google Doc "{DOC_NAME}" ({doc_id})')
    state['doc_id'] = doc_id
    return docs, doc_id


def _first_table(doc):
    for el in doc['body']['content']:
        if 'table' in el:
            return el
    return None


def push_to_doc(stories, date_label):
    """Prepend: date heading, then a (header + N)-row 2-column table."""
    docs, doc_id = find_or_create_doc(STATE)

    heading = date_label
    rows = len(stories) + 1
    docs.documents().batchUpdate(documentId=doc_id, body={'requests': [
        {'insertText': {'location': {'index': 1}, 'text': heading + '\n'}},
        {'updateParagraphStyle': {
            'range': {'startIndex': 1, 'endIndex': 1 + len(heading)},
            'paragraphStyle': {'namedStyleType': 'HEADING_2'},
            'fields': 'namedStyleType'}},
        {'insertTable': {'location': {'index': 1 + len(heading) + 1},
                         'rows': rows, 'columns': 2}},
    ]}).execute()

    # The new table is the FIRST table in the doc (we always prepend).
    doc = docs.documents().get(documentId=doc_id).execute()
    table = _first_table(doc)['table']

    cell_texts = [('Story', 'Description')]
    cell_texts += [(f'{s["headline"]} ({s["source"]})', s['blurb']) for s in stories]

    # Fill cells in reverse document order so earlier indexes stay valid.
    inserts = []
    for r_i, row in enumerate(table['tableRows']):
        for c_i, cell in enumerate(row['tableCells']):
            text = cell_texts[r_i][c_i]
            if text:
                inserts.append({'insertText': {
                    'location': {'index': cell['content'][0]['startIndex']},
                    'text': text}})
    inserts.reverse()
    docs.documents().batchUpdate(documentId=doc_id,
                                 body={'requests': inserts}).execute()

    # Styling pass: bold header row, hyperlink each headline.
    doc = docs.documents().get(documentId=doc_id).execute()
    table = _first_table(doc)['table']
    styles = []
    for r_i, row in enumerate(table['tableRows']):
        for c_i, cell in enumerate(row['tableCells']):
            para = cell['content'][0]
            start = para['startIndex']
            end = para['endIndex'] - 1  # trailing newline
            if end <= start:
                continue
            if r_i == 0:
                styles.append({'updateTextStyle': {
                    'range': {'startIndex': start, 'endIndex': end},
                    'textStyle': {'bold': True}, 'fields': 'bold'}})
            elif c_i == 0:
                s = stories[r_i - 1]
                head_end = start + len(s['headline'])
                styles.append({'updateTextStyle': {
                    'range': {'startIndex': start, 'endIndex': min(head_end, end)},
                    'textStyle': {'link': {'url': s['url']}},
                    'fields': 'link'}})
    if styles:
        docs.documents().batchUpdate(documentId=doc_id,
                                     body={'requests': styles}).execute()
    return doc_id


# ---------------------------------------------------------------- Google Sheet

SHEET_TABS = {
    'Stories':  ['Date', 'Story', 'Source', 'Description', 'Link'],
    'Social':   ['Date', 'Account', 'Post', 'Link'],
    'Accounts': ['Account', 'Times linked', 'Last seen', 'Profile'],
}

# Pixel widths per tab, in column order. Long prose columns get wrapped.
SHEET_WIDTHS = {
    'Stories':  [90, 400, 110, 450, 300],
    'Social':   [90, 190, 620, 280],
    'Accounts': [170, 100, 100, 240],
}


def format_sheet(sheets, sid, gids):
    """Column widths, wrapped text, top alignment, frozen bold header."""
    reqs = []
    for title, widths in SHEET_WIDTHS.items():
        gid = gids[title]
        for i, w in enumerate(widths):
            reqs.append({'updateDimensionProperties': {
                'range': {'sheetId': gid, 'dimension': 'COLUMNS',
                          'startIndex': i, 'endIndex': i + 1},
                'properties': {'pixelSize': w}, 'fields': 'pixelSize'}})
        reqs.append({'repeatCell': {
            'range': {'sheetId': gid, 'startRowIndex': 1},
            'cell': {'userEnteredFormat': {'wrapStrategy': 'WRAP',
                                           'verticalAlignment': 'TOP'}},
            'fields': 'userEnteredFormat(wrapStrategy,verticalAlignment)'}})
        reqs.append({'repeatCell': {
            'range': {'sheetId': gid, 'startRowIndex': 0, 'endRowIndex': 1},
            'cell': {'userEnteredFormat': {'textFormat': {'bold': True}}},
            'fields': 'userEnteredFormat.textFormat.bold'}})
        reqs.append({'updateSheetProperties': {
            'properties': {'sheetId': gid,
                           'gridProperties': {'frozenRowCount': 1}},
            'fields': 'gridProperties.frozenRowCount'}})
    sheets.spreadsheets().batchUpdate(spreadsheetId=sid,
                                      body={'requests': reqs}).execute()


def find_or_create_sheet(state):
    sheets = service('personal', 'drive', 'sheets', 'v4')
    drive = service('personal', 'drive', 'drive', 'v3')
    sid = state.get('sheet_id')
    if sid:
        try:
            sheets.spreadsheets().get(spreadsheetId=sid,
                                      fields='spreadsheetId').execute()
            return sheets, sid
        except Exception:
            pass
    hits = drive.files().list(
        q=f"name = '{DOC_NAME}' and mimeType = 'application/vnd.google-apps.spreadsheet' "
          "and trashed = false",
        fields='files(id)', pageSize=1).execute().get('files', [])
    if hits:
        sid = hits[0]['id']
    else:
        body = {'properties': {'title': DOC_NAME},
                'sheets': [{'properties': {'title': t,
                                           'gridProperties': {'frozenRowCount': 1}}}
                           for t in SHEET_TABS]}
        created = sheets.spreadsheets().create(body=body).execute()
        sid = created['spreadsheetId']
        gids = {s['properties']['title']: s['properties']['sheetId']
                for s in created['sheets']}
        for title, headers in SHEET_TABS.items():
            sheets.spreadsheets().values().update(
                spreadsheetId=sid, range=f'{title}!A1',
                valueInputOption='RAW', body={'values': [headers]}).execute()
        format_sheet(sheets, sid, gids)
        print(f'Created new Google Sheet "{DOC_NAME}" ({sid})')
    state['sheet_id'] = sid
    return sheets, sid


def _prepend_rows(sheets, sid, gid, title, rows):
    """New rows go directly under the header so newest always sits on top."""
    if not rows:
        return
    sheets.spreadsheets().batchUpdate(spreadsheetId=sid, body={'requests': [
        {'insertDimension': {
            'range': {'sheetId': gid, 'dimension': 'ROWS',
                      'startIndex': 1, 'endIndex': 1 + len(rows)},
            'inheritFromBefore': False}}]}).execute()
    sheets.spreadsheets().values().update(
        spreadsheetId=sid, range=f'{title}!A2',
        valueInputOption='RAW', body={'values': rows}).execute()


def push_to_sheet(stories, socials):
    sheets, sid = find_or_create_sheet(STATE)
    meta = sheets.spreadsheets().get(
        spreadsheetId=sid, fields='sheets(properties(sheetId,title))').execute()
    gids = {s['properties']['title']: s['properties']['sheetId']
            for s in meta['sheets']}
    day = f'{datetime.now(timezone.utc).astimezone():%Y-%m-%d}'
    _prepend_rows(sheets, sid, gids['Stories'], 'Stories',
                  [[day, s['headline'], s['source'], s['blurb'], s['url']]
                   for s in stories])
    _prepend_rows(sheets, sid, gids['Social'], 'Social',
                  [[day, f'{p["account"]} (@{p["handle"]})', p['text'], p['url']]
                   for p in socials])
    # Accounts roster: rewritten each run, ranked by how often Revolver links them.
    acct = STATE.get('accounts', {})
    top = sorted(acct.items(), key=lambda kv: -kv[1]['n'])[:TOP_ACCOUNTS]
    sheets.spreadsheets().values().clear(
        spreadsheetId=sid, range='Accounts!A2:D10000').execute()
    if top:
        sheets.spreadsheets().values().update(
            spreadsheetId=sid, range='Accounts!A2',
            valueInputOption='RAW',
            body={'values': [[f'@{h}', d['n'], d['last'], f'https://x.com/{h}']
                             for h, d in top]}).execute()
    return sid


def publish(stories, socials, handle_counts, date_label):
    """Doc + Sheet + state, in one place so manual runs behave like cron runs."""
    today = f'{datetime.now(timezone.utc).astimezone():%Y-%m-%d}'
    acct = STATE.setdefault('accounts', {})
    for h, n in handle_counts.items():
        entry = acct.setdefault(h, {'n': 0, 'last': today})
        entry['n'] += n
        entry['last'] = today
    doc_id = push_to_doc(stories, date_label)
    sheet_id = push_to_sheet(stories, socials)
    STATE['seen'] = STATE.get('seen', []) + [s['url'] for s in stories]
    STATE['seen_social'] = STATE.get('seen_social', []) + [p['url'] for p in socials]
    save_state(STATE)
    return doc_id, sheet_id


# ---------------------------------------------------------------- main

STATE = load_state()


def main():
    ap = argparse.ArgumentParser(description='Revolver-style morning story sweep')
    ap.add_argument('--test', action='store_true',
                    help='3 sources only, print picks, no doc write')
    ap.add_argument('--no-doc', action='store_true',
                    help='full run but print instead of writing the doc')
    args = ap.parse_args()

    sources = SOURCES
    if args.test:
        sources = {k: SOURCES[k] for k in list(SOURCES)[:3]}

    print(f'[{datetime.now():%Y-%m-%d %H:%M}] Snapshotting revolver.news ...')
    heads, social_urls, handle_counts = revolver_snapshot()
    print(f'  {len(heads)} reference headlines, {len(social_urls)} social links, '
          f'{len(handle_counts)} accounts')

    seen = set(STATE.get('seen', []))
    print(f'Pulling {len(sources)} source feeds ...')
    candidates, report = collect_candidates(sources, seen)
    print('\n'.join(report))
    print(f'  {len(candidates)} fresh candidates')
    if not candidates:
        print('Nothing new this morning; doc and sheet left untouched.')
        return

    print('Fetching linked social posts ...')
    socials = fetch_social_posts(social_urls, set(STATE.get('seen_social', [])))
    print(f'  {len(socials)} new posts')

    print('Asking Claude to pick stories and write blurbs ...')
    try:
        stories = pick_and_blurb(heads, candidates)
    except RuntimeError as e:
        # Keep the daily log readable: a bad key is a config problem, not a crash.
        print(f'STOPPED: {e}')
        sys.exit(1)
    print(f'  {len(stories)} stories selected')

    if args.test or args.no_doc:
        for s in stories:
            print(f'\n* {s["headline"]}  [{s["source"]}]')
            print(f'    {s["blurb"]}')
            print(f'    {s["url"]}')
        for p in socials:
            print(f'\n@ {p["account"]} (@{p["handle"]}): {p["text"][:120]}')
        return

    date_label = f'{datetime.now(timezone.utc).astimezone():%A, %B %d, %Y}'
    doc_id, sheet_id = publish(stories, socials, handle_counts, date_label)
    print(f'Done: {len(stories)} stories, {len(socials)} social posts')
    print(f'  Sheet: https://docs.google.com/spreadsheets/d/{sheet_id}/edit')
    print(f'  Doc:   https://docs.google.com/document/d/{doc_id}/edit')


if __name__ == '__main__':
    main()
