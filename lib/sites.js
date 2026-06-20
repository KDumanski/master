// ============================================================================
// MASTER — single source of truth for every site in the portfolio.
// ----------------------------------------------------------------------------
// This one file drives BOTH:
//   1. the public directory page (app/page.jsx) — the clickable list of sites
//   2. the deploy-control scripts (scripts/*.mjs) — which repos to stage/deploy
//
// To add a site: copy a block below and fill it in. To change where a site
// lives or how it deploys, edit it here. Nothing else needs to change.
//
// FIELDS
//   key        unique slug (used in scripts + as React key)
//   name       display name
//   owner      GitHub owner/org (almost always 'KDumanski')
//   repo       GitHub repo name
//   dir        local folder under c:/Propcheck Git/clone (for deploy scripts)
//   stack      'next' (static export → ./out) | 'static' (serve repo root)
//   status     'live' (deployed + reachable) | 'staging' (not yet deployed)
//   hosting    'domain' (custom CNAME — DO NOT disrupt) | 'pages' (github.io)
//   domain     custom domain, if hosting==='domain'
//   url        the canonical live URL (domain or github.io project page)
//   category   grouping for the directory ('Client', 'Project', 'Internal')
//   blurb      one-line description for the card
//   manage     true → deploy-control scripts may stage/deploy it
//   excluded   true → never touch (e.g. the stoop app, data scrapers)
// ============================================================================

const GH = 'KDumanski';

// github.io project-page URL for a repo (default Pages location).
const pagesUrl = (owner, repo) => `https://${owner.toLowerCase()}.github.io/${repo}/`;

export const SITES = [
  // ---------------- Client sites on custom domains (LIVE) ----------------
  {
    key: 'stark-level',
    name: 'Stark Level Solutions',
    owner: GH, repo: 'Stark-Level', dir: 'Stark Level',
    stack: 'static', status: 'live', hosting: 'domain',
    domain: 'starklevelsolutions.com',
    url: 'https://starklevelsolutions.com',
    category: 'Client',
    blurb: 'Business solutions & consulting site.',
    manage: true,
  },
  {
    key: 'omar-art',
    name: 'Omar Chacon Art',
    owner: GH, repo: 'Omar-art-website', dir: 'Omars Art Website',
    stack: 'static', status: 'live', hosting: 'domain',
    domain: 'omarchaconart.com',
    url: 'https://omarchaconart.com',
    category: 'Client',
    blurb: 'Portfolio site for artist Omar Chacon.',
    manage: true,
  },
  {
    key: 'virtue-signals',
    name: 'The Virtue Signals',
    owner: GH, repo: 'TheVirtueSignals', dir: 'TheVirtueSignals',
    stack: 'static', status: 'live', hosting: 'domain',
    domain: 'thevirtuesignals.net',
    url: 'https://thevirtuesignals.net',
    category: 'Client',
    blurb: 'Band / music project site.',
    manage: true,
  },
  {
    key: 'marborough-house',
    name: 'Marborough House',
    owner: GH, repo: 'Marborough-House', dir: 'Marborough-House',
    stack: 'static', status: 'live', hosting: 'domain',
    domain: 'marboroughhousenh.com',
    url: 'https://marboroughhousenh.com',
    category: 'Client',
    blurb: 'New Hampshire inn / hospitality site.',
    manage: true,
  },
  {
    key: 'dental-group',
    name: 'Dental Group',
    owner: GH, repo: 'DentalGroup', dir: 'DentalGroup',
    stack: 'static', status: 'staging', hosting: 'pages',
    domain: null,
    url: pagesUrl(GH, 'DentalGroup'),
    category: 'Client',
    blurb: 'Dental practice website.',
    // Repo exists on GitHub but is not cloned locally yet — clone it into
    // …/clone/DentalGroup and flip manage:true to bring it under deploy control.
    manage: false,
  },

  // ---------------- Sites staged on GitHub Pages (project pages) ----------------
  {
    key: 'fabians-tours',
    name: "Fabian's Tours",
    owner: GH, repo: 'fabians-tours', dir: 'Fabians Tours',
    stack: 'next', status: 'live', hosting: 'pages',
    domain: null,
    url: pagesUrl(GH, 'fabians-tours'),
    category: 'Client',
    blurb: 'Cinematic luxury Egypt tours & sacred journeys.',
    manage: true,
  },
  {
    key: 'world-cup',
    name: 'World Cup 2026 Fan Guide',
    owner: GH, repo: 'world-cup', dir: 'World Cup',
    stack: 'next', status: 'staging', hosting: 'pages',
    domain: null,
    url: pagesUrl(GH, 'world-cup'),
    category: 'Project',
    blurb: 'A taste of home in all 16 host cities across the USA, Canada & Mexico.',
    manage: true,
  },
  {
    key: 'symbiotiks',
    name: 'Symbiotiks',
    owner: GH, repo: 'Symbiotiks', dir: 'Symbiotiks',
    stack: 'static', status: 'staging', hosting: 'pages',
    domain: null,
    url: pagesUrl(GH, 'Symbiotiks'),
    category: 'Project',
    blurb: 'Pitch deck & company site.',
    manage: true,
  },
  {
    key: 'stark-production',
    name: 'Stark Production Group',
    owner: GH, repo: 'Stasrk-Production-Group', dir: 'Stasrk Production Group',
    stack: 'static', status: 'staging', hosting: 'pages',
    domain: null,
    url: pagesUrl(GH, 'Stasrk-Production-Group'),
    category: 'Client',
    blurb: 'Production company site.',
    manage: true,
  },
  {
    key: 'yoga',
    name: 'Yoga',
    owner: GH, repo: 'Yoga', dir: 'Yoga',
    // Multi-folder app (web / backend / ad-studio) — not a one-click static deploy.
    // Listed in the directory; manage=false until its build/output is settled.
    stack: 'static', status: 'staging', hosting: 'pages',
    domain: null,
    url: pagesUrl(GH, 'Yoga'),
    category: 'Project',
    blurb: 'Yoga studio site (multi-part app — deploy WIP).',
    manage: false,
  },
];

// ----------------------------- Derived helpers -----------------------------

export const CATEGORY_ORDER = ['Client', 'Project', 'Internal'];

export function sitesByCategory() {
  const groups = new Map();
  for (const s of SITES) {
    if (!groups.has(s.category)) groups.set(s.category, []);
    groups.get(s.category).push(s);
  }
  return CATEGORY_ORDER
    .filter((c) => groups.has(c))
    .map((c) => ({ category: c, sites: groups.get(c) }));
}

export const HUB_STATS = {
  total: SITES.length,
  live: SITES.filter((s) => s.status === 'live').length,
  staging: SITES.filter((s) => s.status === 'staging').length,
  domains: SITES.filter((s) => s.hosting === 'domain').length,
};
