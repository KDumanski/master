// sites:deploy — push managed repos to trigger their GitHub Pages deploy, and
// (optionally) enable Pages-via-Actions on the repo through the gh API.
//
//   node scripts/deploy.mjs                    # DRY RUN — what would happen
//   node scripts/deploy.mjs --apply            # push each repo (triggers deploy)
//   node scripts/deploy.mjs --apply --enable   # ...and enable Pages via gh API
//   node scripts/deploy.mjs --only world-cup --apply --enable
//
// SAFETY:
//  - dry run unless --apply
//  - refuses to push a repo with uncommitted changes (commit first)
//  - skips repos with no upstream unless --enable creates the remote first
//  - never force-pushes; never touches a repo not in the managed list
import { existsSync } from 'node:fs';
import { loadSites, siteDir, isGitRepo, run, ghReady, c } from './_lib.mjs';

const argv = process.argv.slice(2);
const apply = argv.includes('--apply');
const enable = argv.includes('--enable');
const onlyIdx = argv.indexOf('--only');
const only = onlyIdx >= 0 ? (argv[onlyIdx + 1] || '').split(',').map((s) => s.trim()) : null;

const all = await loadSites();
const sites = (only ? all.filter((s) => only.includes(s.key)) : all.filter((s) => s.manage && !s.excluded));

console.log(c.bold(`\n  Deploy  ${apply ? c.green('(APPLY)') : c.amber('(dry run)')}  — ${sites.length} sites\n`));

const gh = ghReady();
if (enable && !gh.ok) {
  console.log(`  ${c.red('✗')} --enable needs gh: ${gh.why}\n`);
  process.exit(1);
}

for (const s of sites) {
  const dir = siteDir(s);
  const repoFull = `${s.owner}/${s.repo}`;
  if (!existsSync(dir) || !isGitRepo(dir)) { console.log(`  ${c.red('✗')} ${s.name} — repo missing, skip`); continue; }

  const dirty = run('git status --porcelain', dir).out;
  if (dirty) { console.log(`  ${c.amber('•')} ${s.name} — ${c.amber('uncommitted changes, skip')} (commit first)`); continue; }

  const branch = run('git rev-parse --abbrev-ref HEAD', dir).out || 'main';
  const hasRemote = run('git remote get-url origin', dir).ok;

  console.log(`  ${apply ? c.green('▶') : c.amber('~')} ${s.name}  ${c.dim(repoFull)} ${c.dim('→ ' + s.url)}`);

  if (!apply) {
    console.log(`      would: ${hasRemote ? '' : 'create repo, '}push ${branch}${enable ? ', enable Pages' : ''}`);
    continue;
  }

  // 1. Ensure the GitHub repo exists (create from local if gh is ready).
  if (!hasRemote || enable) {
    if (gh.ok) {
      const exists = run(`gh repo view ${repoFull}`).ok;
      if (!exists) {
        const cr = run(`gh repo create ${repoFull} --public --source="${dir}" --remote=origin`, dir);
        console.log(`      ${cr.ok ? c.green('repo created') : c.red('create failed: ') + cr.out.split('\n')[0]}`);
      }
    } else if (!hasRemote) {
      console.log(`      ${c.red('no remote and gh unavailable')} — set origin or run gh auth login`);
      continue;
    }
  }

  // 2. Push (triggers the deploy workflow).
  const push = run(`git push -u origin ${branch}`, dir);
  console.log(`      ${push.ok ? c.green('pushed') : c.red('push failed: ') + push.out.split('\n')[0]}`);

  // 3. Enable Pages-via-Actions (idempotent; ignores "already exists").
  if (enable && gh.ok && push.ok) {
    const en = run(`gh api -X POST repos/${repoFull}/pages -f build_type=workflow`);
    const ok = en.ok || /already exists/i.test(en.out);
    console.log(`      ${ok ? c.green('Pages enabled (Actions)') : c.amber('Pages: ' + en.out.split('\n')[0])}`);
  }
}

console.log('');
if (!apply) console.log(c.dim('  Re-run with --apply (add --enable to create repos & turn on Pages).\n'));
