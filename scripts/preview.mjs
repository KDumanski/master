// preview — build (if needed) and open any portfolio site in the browser.
//
//   npm run preview <site-key>          e.g. npm run preview world-cup
//   npm run preview <site-key> --build  force a fresh Next.js build first
//   node scripts/preview.mjs --list     list available site keys
//
// What it does, per the site's `stack` in lib/sites.js:
//   • next   → ensures deps, builds with BASE_PATH=none (so it serves at root),
//              then serves ./out
//   • static → serves the repo folder as-is (index.html at root)
// Then it serves on a fixed port and opens your default browser at that URL.
//
// This is the "ask → change → see it" loop: after I edit a site, run this and
// the result pops open. Ctrl+C stops the server.
import { spawn, spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { loadSites, siteDir, c } from './_lib.mjs';

const argv = process.argv.slice(2);
const key = argv.find((a) => !a.startsWith('-'));
const forceBuild = argv.includes('--build');
const wantList = argv.includes('--list');
const PORT = 4500;

const sites = await loadSites();

if (wantList || !key) {
  console.log(c.bold('\n  Preview a site:  npm run preview <key>\n'));
  for (const s of sites) {
    console.log(`  ${c.blue(s.key.padEnd(20))} ${c.dim(s.stack.padEnd(7))} ${s.name}`);
  }
  console.log('');
  process.exit(wantList ? 0 : 1);
}

const site = sites.find((s) => s.key === key);
if (!site) {
  console.log(c.red(`\n  No site with key "${key}".`) + c.dim('  Run with --list to see keys.\n'));
  process.exit(1);
}

const dir = siteDir(site);
if (!existsSync(dir)) {
  console.log(c.red(`\n  Site folder not found: ${dir}`));
  console.log(c.dim(`  (Clone the repo into …/clone/${site.dir} first.)\n`));
  process.exit(1);
}

// Run a command inheriting stdio so the user sees build output live.
function sh(cmd, args, cwd, env) {
  const r = spawnSync(cmd, args, { cwd, stdio: 'inherit', shell: true, env: { ...process.env, ...env } });
  if (r.status !== 0) { console.log(c.red(`\n  "${cmd} ${args.join(' ')}" failed.\n`)); process.exit(r.status || 1); }
}

let serveRoot = dir;

if (site.stack === 'next') {
  if (!existsSync(path.join(dir, 'node_modules'))) {
    console.log(c.dim('\n  Installing dependencies (first run)…'));
    sh('npm', ['install'], dir);
  }
  const outDir = path.join(dir, 'out');
  if (forceBuild || !existsSync(outDir)) {
    console.log(c.dim(`\n  Building ${site.name} (BASE_PATH=none for local preview)…`));
    sh('npm', ['run', 'build'], dir, { BASE_PATH: 'none' });
  } else {
    console.log(c.dim(`\n  Using existing build in ./out (pass --build to rebuild).`));
  }
  serveRoot = outDir;
}

const url = `http://localhost:${PORT}`;
console.log(c.green(`\n  ▶ Serving ${c.bold(site.name)} at ${url}`));
console.log(c.dim('  Press Ctrl+C to stop.\n'));

// Start the static server (npx serve), then open the browser once it's up.
const server = spawn('npx', ['serve', serveRoot, '-l', String(PORT), '--no-clipboard'], {
  stdio: 'inherit', shell: true,
});

// Open default browser (Windows 'start', macOS 'open', Linux 'xdg-open').
setTimeout(() => {
  const opener = process.platform === 'win32' ? ['cmd', ['/c', 'start', '', url]]
    : process.platform === 'darwin' ? ['open', [url]]
    : ['xdg-open', [url]];
  spawn(opener[0], opener[1], { stdio: 'ignore', shell: true, detached: true });
}, 1500);

const stop = () => { try { server.kill(); } catch {} process.exit(0); };
process.on('SIGINT', stop);
process.on('SIGTERM', stop);
server.on('exit', (code) => process.exit(code || 0));