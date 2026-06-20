# Master ◆

**One repo to rule them all.** Master is the control center for the whole site portfolio. It does two jobs:

1. **A public directory** — a GitHub Pages landing page listing every site (Fabian's, World Cup, Stark Level, Omar's Art, etc.) with live links and deploy status, so anyone can find and open them.
2. **Central deploy control** — scripts that stage and deploy all the *other* repos to GitHub Pages from one place, using one universal workflow, without touching the sites already happily running on custom domains.

Live once deployed: **`https://kdumanski.github.io/master/`**

---

## The one file that matters: [`lib/sites.js`](lib/sites.js)

Everything — the directory page **and** the deploy scripts — reads from this single list. Add or change a site there and both update. Each entry:

```js
{
  key: 'world-cup',                 // unique slug
  name: 'World Cup 2026 Fan Guide',
  owner: 'KDumanski', repo: 'world-cup', dir: 'World Cup',
  stack: 'next',                    // 'next' (static export) | 'static' (plain HTML)
  status: 'staging',                // 'live' | 'staging'
  hosting: 'pages',                 // 'pages' (github.io) | 'domain' (custom CNAME)
  domain: null,
  url: 'https://kdumanski.github.io/world-cup/',
  category: 'Project',              // 'Client' | 'Project' | 'Internal'
  blurb: '…',
  manage: true,                     // may the deploy scripts stage/deploy it?
}
```

### To add a new site
1. Drop its folder next to this one (under `…/clone/<dir>`).
2. Add a block to `SITES` in `lib/sites.js`.
3. `npm run sites:status` to confirm Master sees it.

---

## Deploy control scripts

All scripts are **dry-run by default** and only act on sites with `manage: true`. Run from the Master folder.

| Command | What it does |
|---|---|
| `npm run preview <key>` | Build (if needed), serve, and **open the site in your browser**. The "ask → change → see it" loop. `--build` forces a rebuild, `--list` lists keys. **Safe anytime.** |
| `npm run sites:status` | Read-only. Branch, uncommitted changes, ahead/behind, whether a deploy workflow exists. **Safe anytime.** |
| `npm run sites:stage` | Shows which repos would get the universal deploy workflow. |
| `node scripts/stage.mjs --apply --commit` | Writes `.github/workflows/deploy.yml` into each repo and commits it. |
| `npm run sites:deploy` | Shows what would be pushed/created/enabled. |
| `node scripts/deploy.mjs --apply --enable` | Creates missing GitHub repos, pushes (triggers deploy), and turns on Pages-via-Actions. |

Useful flags: `--only key1,key2` (act on specific sites), `--dry-run` (force preview).

### Universal staging templates
- [`templates/deploy-static.yml`](templates/deploy-static.yml) — plain HTML sites (uploads repo root; **preserves CNAME** so custom domains keep working).
- [`templates/deploy-next.yml`](templates/deploy-next.yml) — Next.js `output:'export'` sites (builds `./out`; copies CNAME into the build if present).

Edit the template here once, re-run `stage.mjs --apply`, and every repo gets the update.

---

## Custom-domain sites are safe

Stark Level, Omar's Art, The Virtue Signals and Marborough House run on their own domains. The staging templates **upload the CNAME file unchanged**, so applying the universal workflow to them does *not* break the domain — it just standardizes how they deploy. If a domain site is ever missing its `CNAME`, `sites:stage` flags it in red before you apply.

---

## Run the directory page locally

```bash
npm install
npm run dev          # http://localhost:3000
npm run build        # static export → ./out
```

## Deploy Master itself

Push this repo to `KDumanski/master` → the included [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml) builds and publishes it to `kdumanski.github.io/master/`.

```bash
gh repo create KDumanski/master --public --source=. --push
gh api -X POST repos/KDumanski/master/pages -f build_type=workflow
```

---

## What's intentionally excluded
- **The stoop / front-end app** — the main Propcheck product, not a portfolio site.
- **Data scrapers** (zillow, loopnet, stock, address_history) — not websites.
- **Yoga** is listed but `manage: false` until its multi-folder build output is settled.
