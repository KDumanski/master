// sites:stage — install the universal GitHub Pages deploy workflow into each
// managed repo. Picks the template by stack (next vs static). Preserves any
// CNAME file (custom domains stay intact — the templates handle that).
//
//   node scripts/stage.mjs               # DRY RUN — shows what would change
//   node scripts/stage.mjs --apply       # actually writes the workflow files
//   node scripts/stage.mjs --apply --commit   # ...and commits in each repo
//   node scripts/stage.mjs --only world-cup,symbiotiks --apply
//
// Staging only writes the workflow file + commits. It does NOT push — pushing
// is the deploy step (scripts/deploy.mjs), kept separate so you can review.
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { loadSites, siteDir, isGitRepo, run, c, HUB_ROOT } from './_lib.mjs';

const argv = process.argv.slice(2);
const apply = argv.includes('--apply');
const commit = argv.includes('--commit');
const onlyIdx = argv.indexOf('--only');
const only = onlyIdx >= 0 ? (argv[onlyIdx + 1] || '').split(',').map((s) => s.trim()) : null;

const all = await loadSites();
const sites = (only ? all.filter((s) => only.includes(s.key)) : all.filter((s) => s.manage && !s.excluded));

const templates = {
  next: readFileSync(path.join(HUB_ROOT, 'templates', 'deploy-next.yml'), 'utf8'),
  static: readFileSync(path.join(HUB_ROOT, 'templates', 'deploy-static.yml'), 'utf8'),
};

console.log(c.bold(`\n  Universal staging  ${apply ? c.green('(APPLY)') : c.amber('(dry run)')}  — ${sites.length} sites\n`));

let changed = 0;
for (const s of sites) {
  const dir = siteDir(s);
  if (!existsSync(dir) || !isGitRepo(dir)) { console.log(`  ${c.red('✗')} ${s.name} — repo missing/not git, skipped`); continue; }

  const tpl = templates[s.stack] || templates.static;
  const wfDir = path.join(dir, '.github', 'workflows');
  const wfPath = path.join(wfDir, 'deploy.yml');
  const existing = existsSync(wfPath) ? readFileSync(wfPath, 'utf8') : null;
  const hasCNAME = existsSync(path.join(dir, 'CNAME'));

  const same = existing === tpl;
  const note = s.hosting === 'domain'
    ? c.blue(`domain ${s.domain}${hasCNAME ? '' : c.red(' (NO CNAME file!)')}`)
    : c.dim('github.io');

  if (same) { console.log(`  ${c.dim('=')} ${s.name} — already up to date  ${note}`); continue; }

  console.log(`  ${apply ? c.green('✎') : c.amber('~')} ${s.name} — ${existing ? 'update' : 'add'} ${s.stack} workflow  ${note}`);
  changed++;

  if (apply) {
    mkdirSync(wfDir, { recursive: true });
    writeFileSync(wfPath, tpl);
    if (commit) {
      run('git add .github/workflows/deploy.yml', dir);
      const r = run('git commit -m "Add universal GitHub Pages deploy workflow (via Hub)"', dir);
      console.log(`      ${r.ok ? c.green('committed') : c.dim(r.out.split('\n')[0])}`);
    }
  }
}

console.log('');
console.log(c.dim(`  ${changed} repo(s) ${apply ? 'updated' : 'would change'}.`));
if (!apply) console.log(c.dim('  Re-run with --apply (add --commit to commit in each repo).'));
console.log('');
