"""
Revolver News stories — half-hourly multi-platform sweep -> Google Sheet.

Runs every 30 minutes (cron on the GCP box, see deploy_revolver_gcp.sh) and:
  1. Fetches revolver.news (Drudge-style aggregator) to snapshot the headlines
     it is currently running: that gives the topic mix AND the editorial voice.
  2. Pulls fresh candidates from every source in revolver_sources.json: news
     RSS, Substack, Medium, blogs, Reddit, Trump's Truth Social feed, YouTube
     channels (native RSS), Rumble channels (scraped), Telegram channels
     (public t.me/s pages). Add a source by editing the JSON, no code change.
  3. Collects the X/Twitter posts Revolver links (tweet text via the public
     oEmbed endpoint, no API key) and keeps a running roster of the accounts
     it surveys (top 200 by link count, grows daily).
  4. Fetches a mainstream "radar" corpus (CNN/NYT/BBC/... headlines, never
     candidates) and clusters candidates across sources, so each one carries
     how many outlets ran it and whether the mainstream has it. Single-outlet
     stories missing from the radar are DEEP CUTS and get selection priority.
  5. Has Claude pick the candidates that fit Revolver's editorial profile,
     write a one-line blurb in the same punchy voice (trailing "...", no em
     dashes), and label each story: Deep Cut / Opinion / News / Video / Social.
  6. Pushes to the Google SHEET "Revolver News stories" — tabs Stories /
     Social / Accounts / Runs, newest rows on top, every row stamped with the
     exact pull time. The Runs tab records EVERY check, including the quiet
     ones, so you can see the job is alive and when each pull happened.

Usage:
  python scripts/revolver_stories.py            # the scheduled run
  python scripts/revolver_stories.py --test     # 3 sources, print only
  python scripts/revolver_stories.py --dry-run  # full sweep, print only
  python scripts/revolver_stories.py --doc      # also append to the Doc

State: the SHEET itself is the source of truth for what's already published
(the Link columns are re-read each run), so this runs unchanged on any machine.
.revolver_seen.json is only a local cache. Set REVOLVER_SHEET_ID to pin the
target spreadsheet without a state file.

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
# Checked in order for ANTHROPIC_API_KEY when the env var isn't set. Covers the
# Windows laptop and the GCP box, so the same script runs unmodified on both.
ENV_FILES = [
    r'c:\Propcheck Git\etls\.env',
    r'c:\Propcheck Git\front-end\web\.env',
    '/root/etls/.env',
    os.path.join(SCRIPT_DIR, '..', '.env'),
]
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

MAX_AGE_HOURS = 36        # ignore feed entries older than this
MAX_PER_SOURCE = 25       # default candidates taken per source (config can lower)
MAX_CANDIDATES = 400      # hard cap sent to Claude
TARGET_STORIES = '30-50'  # how many stories Claude should pick
TOP_ACCOUNTS = 200        # roster size on the Accounts tab

STORY_LABELS = ['Deep Cut', 'Opinion', 'News', 'Video', 'Social']

SOURCES_FILE = os.path.join(SCRIPT_DIR, 'revolver_sources.json')


def load_sources_config():
    """revolver_sources.json holds the whole roster (news RSS, Substack,
    Medium, YouTube, Rumble, Telegram, Truth Social, blogs, Reddit) plus the
    mainstream radar feeds. Fall back to a minimal news list if the config is
    missing so the cron never goes fully dark."""
    try:
        with open(SOURCES_FILE, encoding='utf-8') as f:
            cfg = json.load(f)
        sources = [s for s in cfg.get('sources', []) if s.get('enabled')]
        return sources, cfg.get('radar', {})
    except (OSError, ValueError) as e:
        print(f'  WARNING: could not read {SOURCES_FILE} ({e}); '
              'falling back to built-in news feeds')
        fallback = [
            {'name': 'NY Post', 'platform': 'News', 'type': 'rss',
             'feeds': ['https://nypost.com/feed/']},
            {'name': 'Breitbart', 'platform': 'News', 'type': 'rss',
             'feeds': ['https://www.breitbart.com/feed/']},
            {'name': 'Zero Hedge', 'platform': 'News', 'type': 'rss',
             'feeds': ['https://cms.zerohedge.com/fullrss2.xml']},
            {'name': 'Daily Caller', 'platform': 'News', 'type': 'rss',
             'feeds': ['https://dailycaller.com/feed/']},
        ]
        return fallback, {}


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


def rss_entries(feed_urls):
    """Feed URLs tried in order; first that parses wins."""
    for fu in feed_urls:
        raw = fetch_url(fu)
        if not raw:
            continue
        parsed = feedparser.parse(raw)
        if parsed.entries:
            return parsed.entries
    return []


def resolve_youtube_channel(handle):
    """@handle -> UC... channel id (every channel has a built-in RSS feed).
    Cached in local state so the page fetch happens once per channel. The
    SOCS/CONSENT cookies skip YouTube's consent interstitial, which otherwise
    replaces the whole page on some networks."""
    cache = STATE.setdefault('yt_channels', {})
    if handle in cache:
        return cache[handle]
    try:
        r = requests.get(f'https://www.youtube.com/@{handle}',
                         headers={'User-Agent': UA,
                                  'Accept-Language': 'en-US,en;q=0.9'},
                         cookies={'SOCS': 'CAI', 'CONSENT': 'YES+1'},
                         timeout=30)
        page = r.text if r.status_code == 200 else None
    except requests.RequestException:
        page = None
    m = page and re.search(
        r'"(?:externalId|browseId|channelId)":"(UC[\w-]{22})"', page)
    if m:
        cache[handle] = m.group(1)
        return m.group(1)
    return None


def youtube_entries(src):
    cid = resolve_youtube_channel(src['handle'])
    if not cid:
        return []
    return rss_entries([f'https://www.youtube.com/feeds/videos.xml?channel_id={cid}'])


def rumble_entries(src, seen_urls):
    """Latest own-channel videos from a Rumble channel. The video LIST is
    JS-rendered, but the channel page and /videos tab each server-render the
    newest item(s), marked with e9s=src_v1_ucp (sidebar recommendations carry
    other e9s tags and must be ignored). At a 30-minute cadence that still
    catches every upload. Titles come from each video page's og:title, only
    fetched for URLs not already in the sheet."""
    links = []
    base = src['channel'].rstrip('/')
    for path in ('', '/videos'):
        page = fetch_url(base + path)
        if not page:
            continue
        for m in re.finditer(
                r'href="(/v[a-z0-9]+-[^"]+?\.html)\?e9s=src_v1_ucp', page):
            url = 'https://rumble.com' + m.group(1)
            if url not in links:
                links.append(url)
    entries = []
    for url in links[:6]:
        if url in seen_urls:
            continue
        title = ''
        vid = fetch_url(url)
        m = vid and (re.search(r'property="og:title"[^>]*content="([^"]+)"', vid)
                     or re.search(r'content="([^"]+)"[^>]*property="og:title"', vid))
        if m:
            title = (m.group(1).replace('&amp;', '&').replace('&#39;', "'")
                     .replace('&quot;', '"'))
        else:
            slug = re.sub(r'^v[a-z0-9]+-', '', url.rsplit('/', 1)[-1])
            title = re.sub(r'\.html$', '', slug).replace('-', ' ').capitalize()
        entries.append({'title': title, 'link': url, 'summary': ''})
    return entries


def telegram_entries(src):
    """Public Telegram channels expose a scrape-friendly t.me/s/<name> page.
    The message text becomes the headline (posts have no titles)."""
    page = fetch_url(f'https://t.me/s/{src["channel"]}')
    if not page:
        return []
    entries = []
    for m in re.finditer(
            r'data-post="([^"]+/\d+)".*?tgme_widget_message_text[^>]*>(.*?)</div>',
            page, re.S):
        post, html_text = m.group(1), m.group(2)
        text = re.sub(r'<br\s*/?>', ' ', html_text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        text = (text.replace('&#39;', "'").replace('&quot;', '"')
                    .replace('&amp;', '&'))
        if len(text) < 30:      # stickers, emoji-only posts, join links
            continue
        entries.append({'title': text[:180], 'link': f'https://t.me/{post}',
                        'summary': text[180:400]})
    return entries[::-1]        # t.me/s lists oldest first; newest first here


def collect_candidates(sources, seen_urls):
    """Pull fresh entries from every configured source, any platform."""
    now = time.time()
    candidates, feed_report = [], []
    run_seen = set()      # feeds sometimes list the same URL twice in one pull
    for src in sources:
        name, platform = src['name'], src.get('platform', 'News')
        stype = src.get('type', 'rss')
        cap = src.get('max', MAX_PER_SOURCE)
        try:
            if stype == 'youtube':
                entries = youtube_entries(src)
            elif stype == 'rumble':
                entries = rumble_entries(src, seen_urls)
            elif stype == 'telegram':
                entries = telegram_entries(src)
            else:
                entries = rss_entries(src.get('feeds', []))
        except Exception as e:
            feed_report.append(f'  {name}: ERROR {e}')
            continue
        if not entries:
            feed_report.append(f'  {name}: FEED FAILED')
            continue
        kept = 0
        for e in entries:
            link = (e.get('link') or '').strip()
            title = re.sub(r'\s+', ' ', e.get('title') or '').strip()
            if not link or not title or link in seen_urls or link in run_seen:
                continue
            ts = e.get('published_parsed') or e.get('updated_parsed')
            if ts and (now - time.mktime(ts)) > MAX_AGE_HOURS * 3600:
                continue
            run_seen.add(link)
            summary = re.sub(r'<[^>]+>', '', e.get('summary') or '')
            summary = re.sub(r'\s+', ' ', summary).strip()[:160]
            candidates.append({'source': name, 'platform': platform,
                               'headline': title, 'url': link,
                               'summary': summary})
            kept += 1
            if kept >= cap:
                break
        feed_report.append(f'  {name}: {kept} fresh')
    return candidates[:MAX_CANDIDATES], feed_report


# ------------------------------------------------------- rarity / Deep Cuts

STOP_WORDS = {
    'the', 'and', 'for', 'that', 'with', 'this', 'from', 'have', 'has', 'was',
    'are', 'will', 'his', 'her', 'its', 'their', 'they', 'them', 'you', 'your',
    'who', 'what', 'when', 'where', 'why', 'how', 'not', 'but', 'out', 'over',
    'after', 'before', 'into', 'about', 'says', 'said', 'new', 'just', 'more',
    'been', 'were', 'than', 'then', 'now', 'off', 'all', 'can', 'could',
    'would', 'should', 'may', 'might', 'get', 'gets', 'amid', 'during',
    'against', 'while', 'because', 'video', 'watch', 'report', 'breaking',
}


def sig_tokens(title):
    """Significant title tokens for cross-outlet story matching."""
    return {w for w in re.findall(r"[a-z][a-z']+", title.lower())
            if w not in STOP_WORDS and len(w) > 2}


def _same_story(a, b):
    """Two headlines describe the same underlying story if their significant
    tokens overlap enough. Calibrated on live pairs (2026-08-05): true matches
    score inter 4-7 / jaccard 0.25-0.55. Leaning loose is the safe direction:
    a missed match falsely brands a common story a Deep Cut, which cheapens
    the label; an extra match merely withholds it."""
    if not a or not b:
        return False
    inter = len(a & b)
    jac = inter / len(a | b)
    return inter >= 5 or (inter >= 4 and jac >= 0.25) or jac >= 0.45


def fetch_radar(radar_feeds):
    """Headline token sets from the mainstream comparison corpus. These are
    NEVER candidates; they only tell us what the mainstream is covering."""
    titles = []
    for name, feed_urls in radar_feeds.items():
        for e in rss_entries(feed_urls)[:40]:
            t = re.sub(r'\s+', ' ', e.get('title') or '').strip()
            if t:
                titles.append(sig_tokens(t))
    return titles


def annotate_rarity(candidates, radar_tokens):
    """Cluster candidates across sources and tag each with how many outlets
    ran the story and whether the mainstream radar has it. outlets=1 and
    mainstream=False is the Deep Cut signal."""
    toks = [sig_tokens(c['headline']) for c in candidates]
    cluster_of = [-1] * len(candidates)
    clusters = []      # each: {'rep': token_set, 'sources': set()}
    for i, tk in enumerate(toks):
        for ci, cl in enumerate(clusters):
            if _same_story(tk, cl['rep']):
                cluster_of[i] = ci
                cl['sources'].add(candidates[i]['source'])
                cl['rep'] = cl['rep'] | tk
                break
        else:
            cluster_of[i] = len(clusters)
            clusters.append({'rep': set(tk),
                             'sources': {candidates[i]['source']}})
    for i, c in enumerate(candidates):
        c['outlets'] = len(clusters[cluster_of[i]]['sources'])
        c['mainstream'] = any(_same_story(toks[i], r) for r in radar_tokens)
    return candidates


# ---------------------------------------------------------------- Claude

def anthropic_key():
    key = os.environ.get('ANTHROPIC_API_KEY')
    if key:
        return key
    for env_file in ENV_FILES:
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
                'required': ['headline', 'url', 'source', 'blurb', 'summary',
                             'tags', 'labels'],
                'properties': {
                    'headline': {'type': 'string'},
                    'url': {'type': 'string'},
                    'source': {'type': 'string'},
                    'blurb': {'type': 'string'},
                    'summary': {'type': 'string'},
                    'tags': {'type': 'array', 'items': {'type': 'string'}},
                    'labels': {'type': 'array',
                               'items': {'type': 'string',
                                         'enum': STORY_LABELS}},
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
        f'{i}. [{c.get("platform", "News")}: {c["source"]}] {c["headline"]} | {c["url"]}'
        + (f' | {c["summary"]}' if c['summary'] else '')
        + f' | outlets:{c.get("outlets", 1)}'
        + f' | mainstream:{"yes" if c.get("mainstream") else "no"}'
        for i, c in enumerate(candidates, 1))

    # Runs every 30 minutes, so a batch may be 5 candidates or 250. Scale the
    # ask to what actually arrived instead of demanding a fixed count.
    target = max(3, min(50, round(len(candidates) * 0.25)))

    prompt = f"""You are the editor of a Drudge-style news aggregator modeled on revolver.news, doing a routine check for newly published stories.

SECTION A - the headlines currently running on revolver.news (this is your reference for BOTH the topic mix and the editorial voice):
{ref}

SECTION B - candidate items pulled this run from the source roster. Each line shows [Platform: Source], the headline (for video and social posts, the title or post text), the URL, sometimes a summary, then two rarity signals: "outlets:" = how many of our sources ran this same underlying story this run, and "mainstream:" = whether it also appears in a mainstream wire/network radar (CNN, NYT, BBC, NPR, ABC, CBS, The Hill):
{cand}

Select roughly {target} candidates from SECTION B that best fit the aggregator's editorial profile shown in SECTION A: politics, immigration, crime, DOJ/FBI, culture-war fights, foreign policy, economy, media criticism, plus the occasional offbeat or big mainstream story. Quality over quota: if fewer genuinely fit, return fewer. When several outlets carry the same underlying story, keep only the single strongest version. Skip pure celebrity filler, sports scores, and product/deal posts.

PRIORITIZE RARE FINDS: a candidate with outlets:1 and mainstream:no is a story nobody else is running. When such a story genuinely fits the profile, prefer it over the tenth version of a story everyone already has. These are the site's most valuable picks.

For each selected story also write "labels": 1-2 labels from exactly this set: "Deep Cut", "Opinion", "News", "Video", "Social". Rules:
- "Deep Cut" when outlets:1 and mainstream:no (rare story nobody else has); it can combine with any other label
- "Opinion" for essays, columns, and analysis pieces (most Substack, Medium, and American Thinker items)
- "News" for straight reported stories
- "Video" for YouTube and Rumble items
- "Social" for Telegram and Truth Social posts
Every story gets exactly one of Opinion/News/Video/Social, plus Deep Cut when it qualifies.

For each selected story also write "summary": a 2-3 sentence EDITORIAL read in the site's voice. First state what happened (drawn ONLY from the headline and feed summary given, never invent facts), then give the sharp take: why it matters, what it reveals, the pattern it fits. Opinionated and punchy like a columnist's note, but every factual claim must come from the given material. No em dashes.

For each selected story also write "tags": 3-6 short tags naming the concrete WHO/WHERE/WHAT of the story: people (e.g. "Trump", "Fauci"), organizations ("DOJ", "WNBA", "FIFA"), places ("Ceuta", "Berlin"), and named events or running stories ("Iran war", "Fauci hearing", "migrant crisis"). Reuse the same spelling for the same entity across stories so tags aggregate.

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
            'Anthropic API key rejected (401). Set a working key as '
            'ANTHROPIC_API_KEY, or in one of: ' + ', '.join(ENV_FILES))
    except anthropic.BadRequestError as e:
        # Out of credit reads as a 400, not a 401 — say so plainly rather than
        # letting it look like a malformed request.
        if 'credit balance' in str(e).lower():
            raise RuntimeError(
                'Anthropic account is out of credit. Top up at '
                'https://console.anthropic.com/ (Plans & Billing); the API key '
                'itself is valid and nothing else needs changing.')
        raise

    if resp.stop_reason == 'refusal':
        raise RuntimeError('Claude declined the selection request (refusal)')
    text = ''.join(b.text for b in resp.content if b.type == 'text')
    stories = json.loads(text)['stories']
    # Belt and braces on the two hard style rules, plus label hygiene: every
    # story carries its platform, a base type label, and the Deep Cut label
    # whenever the rarity signals say it qualifies (even if the model forgot).
    by_url = {c['url']: c for c in candidates}
    base_by_platform = {'YouTube': 'Video', 'Rumble': 'Video',
                        'Telegram': 'Social', 'Truth Social': 'Social',
                        'X': 'Social', 'TikTok': 'Video',
                        'Substack': 'Opinion', 'Medium': 'Opinion'}
    for s in stories:
        s['blurb'] = s['blurb'].replace('\u2014', ', ').replace('--', ',').strip()
        if not s['blurb'].endswith('...'):
            s['blurb'] = s['blurb'].rstrip('.') + '...'
        c = by_url.get(s['url'], {})
        s['platform'] = c.get('platform', 'News')
        labels = [lb for lb in s.get('labels', []) if lb in STORY_LABELS]
        if not any(lb != 'Deep Cut' for lb in labels):
            labels.append(base_by_platform.get(s['platform'], 'News'))
        if (c.get('outlets', 1) == 1 and not c.get('mainstream')
                and 'Deep Cut' not in labels):
            labels.insert(0, 'Deep Cut')
        s['labels'] = labels
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
    'Stories':  ['Pulled', 'Story', 'Source', 'Description', 'Link', 'Summary',
                 'Tags', 'Labels', 'Platform'],
    'Social':   ['Pulled', 'Account', 'Post', 'Link'],
    'Accounts': ['Account', 'Times linked', 'Last seen', 'Profile'],
    'Runs':     ['Pulled', 'Candidates', 'Stories added', 'Social added', 'Status'],
    # Ledger of every URL already shown to the model. Without it a 30-minute
    # cadence would re-send the same rejected stories ~48 times a day.
    'Seen':     ['URL', 'First seen', 'Source', 'Picked'],
}

# Pixel widths per tab, in column order. Long prose columns get wrapped.
SHEET_WIDTHS = {
    'Stories':  [140, 400, 110, 450, 300, 460, 220, 140, 110],
    'Social':   [140, 190, 620, 280],
    'Accounts': [170, 100, 100, 240],
    'Runs':     [140, 100, 110, 110, 420],
    'Seen':     [420, 140, 120, 70],
}

# Where each tab keeps the URL that identifies a row, for sheet-based dedup.
DEDUP_COLS = {'Stories': 'E', 'Social': 'D', 'Seen': 'A'}


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
    sid = state.get('sheet_id') or os.environ.get('REVOLVER_SHEET_ID')
    if sid:
        try:
            sheets.spreadsheets().get(spreadsheetId=sid,
                                      fields='spreadsheetId').execute()
            state['sheet_id'] = sid
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


def ensure_tabs(sheets, sid):
    """Add any missing tab (and its header) so old sheets pick up new tabs."""
    meta = sheets.spreadsheets().get(
        spreadsheetId=sid, fields='sheets(properties(sheetId,title))').execute()
    gids = {s['properties']['title']: s['properties']['sheetId']
            for s in meta['sheets']}
    missing = [t for t in SHEET_TABS if t not in gids]
    if missing:
        added = sheets.spreadsheets().batchUpdate(spreadsheetId=sid, body={
            'requests': [{'addSheet': {'properties': {'title': t}}} for t in missing]
        }).execute()
        for rep in added['replies']:
            props = rep['addSheet']['properties']
            gids[props['title']] = props['sheetId']
        for t in missing:
            sheets.spreadsheets().values().update(
                spreadsheetId=sid, range=f'{t}!A1', valueInputOption='RAW',
                body={'values': [SHEET_TABS[t]]}).execute()
        format_sheet(sheets, sid, gids)
        print(f'  added missing tab(s): {", ".join(missing)}')
    # Header migration: an existing sheet predating new columns (e.g. Labels /
    # Platform on Stories) gets its header row extended in place.
    try:
        head = sheets.spreadsheets().values().get(
            spreadsheetId=sid, range='Stories!1:1').execute().get('values', [[]])[0]
        want = SHEET_TABS['Stories']
        if len(head) < len(want):
            sheets.spreadsheets().values().update(
                spreadsheetId=sid, range='Stories!A1', valueInputOption='RAW',
                body={'values': [want]}).execute()
            format_sheet(sheets, sid, gids)
            print(f'  extended Stories header to {len(want)} columns')
    except Exception:
        pass
    return gids


def load_seen_from_sheet(sheets, sid):
    """The sheet is the source of truth for what's already been published, so
    the job can run from any machine without carrying a state file around."""
    seen = {}
    for tab, col in DEDUP_COLS.items():
        try:
            vals = sheets.spreadsheets().values().get(
                spreadsheetId=sid, range=f'{tab}!{col}2:{col}').execute().get('values', [])
            seen[tab] = {r[0].strip() for r in vals if r and r[0].strip()}
        except Exception:
            seen[tab] = set()
    accounts = {}
    try:
        vals = sheets.spreadsheets().values().get(
            spreadsheetId=sid, range='Accounts!A2:C').execute().get('values', [])
        for row in vals:
            if not row or not row[0].strip():
                continue
            handle = row[0].strip().lstrip('@')
            try:
                n = int(row[1]) if len(row) > 1 and str(row[1]).strip() else 0
            except ValueError:
                n = 0
            accounts[handle] = {'n': n, 'last': row[2] if len(row) > 2 else ''}
    except Exception:
        pass
    # A story counts as "seen" once the model has looked at it, whether or not
    # it was picked, so rejects are never re-sent on the next half-hourly pull.
    return (seen.get('Stories', set()) | seen.get('Seen', set()),
            seen.get('Social', set()), accounts)


def push_to_sheet(sheets, sid, gids, stamp, stories, socials, accounts):
    _prepend_rows(sheets, sid, gids['Stories'], 'Stories',
                  [[stamp, s['headline'], s['source'], s['blurb'], s['url'],
                    s.get('summary', ''), ', '.join(s.get('tags', [])),
                    ', '.join(s.get('labels', [])), s.get('platform', 'News')]
                   for s in stories])
    _prepend_rows(sheets, sid, gids['Social'], 'Social',
                  [[stamp, f'{p["account"]} (@{p["handle"]})', p['text'], p['url']]
                   for p in socials])
    # Accounts roster: rewritten each run, ranked by how often Revolver links them.
    top = sorted(accounts.items(), key=lambda kv: -kv[1]['n'])[:TOP_ACCOUNTS]
    sheets.spreadsheets().values().clear(
        spreadsheetId=sid, range='Accounts!A2:D10000').execute()
    if top:
        sheets.spreadsheets().values().update(
            spreadsheetId=sid, range='Accounts!A2', valueInputOption='RAW',
            body={'values': [[f'@{h}', d['n'], d['last'], f'https://x.com/{h}']
                             for h, d in top]}).execute()


def log_seen(sheets, sid, gids, stamp, candidates, picked_urls):
    """Record every candidate the model evaluated, picked or not."""
    _prepend_rows(sheets, sid, gids['Seen'], 'Seen',
                  [[c['url'], stamp, c['source'],
                    'yes' if c['url'] in picked_urls else '']
                   for c in candidates])


def log_run(sheets, sid, gids, stamp, n_cand, n_stories, n_social, status):
    """Every check writes a row here, including the quiet ones, so the sheet
    shows the job is alive and exactly when each pull happened."""
    _prepend_rows(sheets, sid, gids['Runs'], 'Runs',
                  [[stamp, n_cand, n_stories, n_social, status]])


# ---------------------------------------------------------------- main

STATE = load_state()


def main():
    ap = argparse.ArgumentParser(
        description='Revolver-style story + social sweep (runs every 30 min)')
    ap.add_argument('--test', action='store_true',
                    help='3 sources only, print picks, write nothing')
    ap.add_argument('--dry-run', action='store_true',
                    help='full sweep but print instead of writing')
    ap.add_argument('--doc', action='store_true',
                    help='also append a table to the companion Google Doc')
    args = ap.parse_args()

    sources, radar_feeds = load_sources_config()
    if args.test:
        sources = sources[:3]

    stamp = f'{datetime.now(timezone.utc).astimezone():%Y-%m-%d %H:%M}'
    print(f'[{stamp}] Revolver sweep starting ...')

    # The sheet is opened first because it carries the dedup state.
    sheets = sid = gids = None
    seen_stories, seen_social, accounts = set(), set(), {}
    if not (args.test or args.dry_run):
        sheets, sid = find_or_create_sheet(STATE)
        gids = ensure_tabs(sheets, sid)
        seen_stories, seen_social, accounts = load_seen_from_sheet(sheets, sid)
        print(f'  sheet state: {len(seen_stories)} stories, '
              f'{len(seen_social)} posts, {len(accounts)} accounts already logged')
    else:
        seen_stories = set(STATE.get('seen', []))
        seen_social = set(STATE.get('seen_social', []))
        accounts = dict(STATE.get('accounts', {}))

    heads, social_urls, handle_counts = revolver_snapshot()
    print(f'  revolver.news: {len(heads)} headlines, {len(social_urls)} social links, '
          f'{len(handle_counts)} accounts')

    candidates, report = collect_candidates(sources, seen_stories)
    print('\n'.join(report))
    print(f'  {len(candidates)} new candidates')

    socials = fetch_social_posts(social_urls, seen_social)
    print(f'  {len(socials)} new social posts')

    today = stamp[:10]
    for h, n in handle_counts.items():
        entry = accounts.setdefault(h, {'n': 0, 'last': today})
        entry['n'] += n
        entry['last'] = today

    # Quiet check: log the pull, refresh the roster, skip the model entirely.
    if not candidates:
        print('Nothing new since the last pull.')
        if sheets:
            push_to_sheet(sheets, sid, gids, stamp, [], socials, accounts)
            log_run(sheets, sid, gids, stamp, 0, 0, len(socials), 'no new stories')
            print(f'  Sheet: https://docs.google.com/spreadsheets/d/{sid}/edit')
        return

    # Rarity pass: how many of our sources ran each story, and does the
    # mainstream have it. Feeds the Deep Cut label + selection priority.
    radar_tokens = fetch_radar(radar_feeds)
    candidates = annotate_rarity(candidates, radar_tokens)
    n_rare = sum(1 for c in candidates
                 if c['outlets'] == 1 and not c['mainstream'])
    print(f'  radar: {len(radar_tokens)} mainstream headlines; '
          f'{n_rare}/{len(candidates)} candidates look like deep cuts')

    print('Asking Claude to pick stories and write blurbs ...')
    try:
        stories = pick_and_blurb(heads, candidates)
    except RuntimeError as e:
        # A bad key is a config problem, not a crash: log it and leave a clean line.
        print(f'STOPPED: {e}')
        if sheets:
            log_run(sheets, sid, gids, stamp, len(candidates), 0, 0, f'FAILED: {e}')
        sys.exit(1)
    print(f'  {len(stories)} stories selected')

    if args.test or args.dry_run:
        for s in stories:
            print(f'\n* {s["headline"]}  [{s.get("platform", "News")}: {s["source"]}]'
                  f'  {{{", ".join(s.get("labels", []))}}}')
            print(f'    {s["blurb"]}')
            print(f'    {s["url"]}')
        for p in socials:
            print(f'\n@ {p["account"]} (@{p["handle"]}): {p["text"][:120]}')
        return

    push_to_sheet(sheets, sid, gids, stamp, stories, socials, accounts)
    log_seen(sheets, sid, gids, stamp, candidates, {s['url'] for s in stories})
    log_run(sheets, sid, gids, stamp, len(candidates), len(stories), len(socials), 'ok')
    print(f'Done: {len(stories)} stories, {len(socials)} social posts')
    print(f'  Sheet: https://docs.google.com/spreadsheets/d/{sid}/edit')

    if args.doc:
        label = f'{datetime.now(timezone.utc).astimezone():%A, %B %d, %Y %H:%M}'
        doc_id = push_to_doc(stories, label)
        print(f'  Doc:   https://docs.google.com/document/d/{doc_id}/edit')

    # Local cache only; the sheet remains the source of truth.
    STATE['seen'] = sorted(seen_stories | {s['url'] for s in stories})[-1500:]
    STATE['seen_social'] = sorted(seen_social | {p['url'] for p in socials})[-1000:]
    STATE['accounts'] = accounts
    save_state(STATE)


if __name__ == '__main__':
    main()
