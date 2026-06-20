// sites:status — read-only overview of every managed site.
// Shows local repo state (branch, dirty, ahead/behind) and whether a deploy
// workflow is present. Never modifies anything.
import { existsSync } from 'node:fs';
import path from 'node:path';
import { loadSites, siteDir, isGitRepo, run, c, parseArgs, selectSites } from './_lib.mjs';

const args = parseArgs(process.argv);
const sites = selectSites(await loadSites(), args);

console.log(c.bold(`\n  Master — site status  (${sites.length} sites)\n`));
const pad = (s, n) => (s + ' '.repeat(n)).slice(0, n);

for (const s of sites) {
  const dir = siteDir(s);
  if (!existsSync(dir)) { console.log(`  ${c.red('✗')} ${pad(s.name, 26)} ${c.dim('(local folder missing)')}`); continue; }
  if (!isGitRepo(dir)) { console.log(`  ${c.amber('•')} ${pad(s.name, 26)} ${c.dim('(not a git repo)')}`); continue; }

  const branch = run('git rev-parse --abbrev-ref HEAD', dir).out;
  const dirty = run('git status --porcelain', dir).out;
  const dirtyN = dirty ? dirty.split('\n').length : 0;
  // ahead/behind vs upstream (if set)
  const ab = run('git rev-list --left-right --count @{u}...HEAD', dir);
  let sync = c.dim('no upstream');
  if (ab.ok && ab.out) {
    const [behind, ahead] = ab.out.split('\t').map(Number);
    sync = (ahead || behind)
      ? `${ahead ? c.amber('↑' + ahead) : ''}${behind ? c.blue(' ↓' + behind) : ''}`.trim()
      : c.green('in sync');
  }
  const wfStatic = existsSync(path.join(dir, '.github/workflows/deploy.yml'));
  const wf = wfStatic ? c.green('deploy.yml') : c.amber('no workflow');
  const dirtyStr = dirtyN ? c.amber(`${dirtyN} uncommitted`) : c.green('clean');
  const tag = s.hosting === 'domain' ? c.blue(`🌐 ${s.domain}`) : c.dim('📄 pages');

  console.log(`  ${c.green('●')} ${pad(s.name, 26)} ${pad(branch, 8)} ${pad(dirtyStr, 22)} ${pad(sync, 20)} ${pad(wf, 22)} ${tag}`);
}
console.log('');
