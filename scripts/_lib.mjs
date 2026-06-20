// Shared helpers for the deploy-control scripts. Pure Node (no deps).
// Reads the site list straight from lib/sites.js so there's one source of truth.
import { execSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const HUB_ROOT = path.resolve(__dirname, '..');
// All client repos live as sibling folders of the Hub under .../clone/<dir>.
export const CLONE_ROOT = path.resolve(HUB_ROOT, '..');

// Import the ESM data file at runtime.
export async function loadSites() {
  const mod = await import(pathToFileURL(path.join(HUB_ROOT, 'lib', 'sites.js')).href);
  return mod.SITES;
}

// Absolute path to a site's local working copy.
export function siteDir(site) {
  return path.join(CLONE_ROOT, site.dir);
}

export function isGitRepo(dir) {
  return existsSync(path.join(dir, '.git'));
}

// Run a command, return { ok, out }. Never throws — callers decide what to do.
export function run(cmd, cwd) {
  try {
    const out = execSync(cmd, { cwd, stdio: ['ignore', 'pipe', 'pipe'], encoding: 'utf8' });
    return { ok: true, out: out.trim() };
  } catch (e) {
    return { ok: false, out: ((e.stdout || '') + (e.stderr || '')).trim() || e.message };
  }
}

// Is `gh` installed and authenticated?
export function ghReady() {
  const v = run('gh --version');
  if (!v.ok) return { ok: false, why: 'gh CLI not installed' };
  const a = run('gh auth status');
  if (!a.ok) return { ok: false, why: 'gh not authenticated — run: gh auth login' };
  return { ok: true };
}

// Pretty console helpers.
export const c = {
  dim: (s) => `\x1b[2m${s}\x1b[0m`,
  green: (s) => `\x1b[32m${s}\x1b[0m`,
  amber: (s) => `\x1b[33m${s}\x1b[0m`,
  red: (s) => `\x1b[31m${s}\x1b[0m`,
  blue: (s) => `\x1b[36m${s}\x1b[0m`,
  bold: (s) => `\x1b[1m${s}\x1b[0m`,
};

// Parse CLI args of the form: node x.mjs [--only key1,key2] [--all] [--dry-run]
export function parseArgs(argv) {
  const args = { only: null, all: false, dryRun: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--all') args.all = true;
    else if (a === '--dry-run' || a === '-n') args.dryRun = true;
    else if (a === '--only') args.only = (argv[++i] || '').split(',').map((s) => s.trim()).filter(Boolean);
  }
  return args;
}

// Resolve which sites a command should act on, honoring --only / manage flag.
export function selectSites(sites, args) {
  let sel = sites.filter((s) => s.manage && !s.excluded);
  if (args.only && args.only.length) {
    sel = sites.filter((s) => args.only.includes(s.key));
  }
  return sel;
}
