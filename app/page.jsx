import { sitesByCategory, HUB_STATS } from '@/lib/sites';
import SiteCard from '@/components/SiteCard';
import SectionReveal from '@/components/SectionReveal';
import ThemeToggle from '@/components/ThemeToggle';
import styles from './page.module.css';

const CATEGORY_LABEL = {
  Client: 'Client sites',
  Project: 'Projects',
  Internal: 'Internal',
};

export default function Home() {
  const groups = sitesByCategory();
  return (
    <>
      <header className={styles.topbar}>
        <div className={`container ${styles.topbarInner}`}>
          <span className={styles.brand}>
            <span className={styles.brandMark} aria-hidden>◆</span> Master
          </span>
          <ThemeToggle />
        </div>
      </header>

      <section className={styles.hero}>
        <div className={styles.heroGlow} aria-hidden />
        <div className={`container ${styles.heroInner}`}>
          <span className="kicker">Portfolio · Deploy control</span>
          <h1 className={styles.heroTitle}>Every site, in one place.</h1>
          <p className={`lead ${styles.heroLead}`}>
            A single directory of every website in the portfolio — live links, hosting and deploy
            status at a glance. This repo also centrally stages and deploys the sites to GitHub Pages.
          </p>
          <div className={styles.stats}>
            <Stat n={HUB_STATS.total} label="Sites" />
            <Stat n={HUB_STATS.live} label="Live" tone="live" />
            <Stat n={HUB_STATS.staging} label="Staging" tone="staging" />
            <Stat n={HUB_STATS.domains} label="On custom domains" />
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          {groups.map((g) => (
            <div key={g.category} className={styles.group}>
              <SectionReveal className={styles.groupHead}>
                <h2 className={styles.groupTitle}>{CATEGORY_LABEL[g.category] || g.category}</h2>
                <span className={styles.groupCount}>{g.sites.length} {g.sites.length === 1 ? 'site' : 'sites'}</span>
              </SectionReveal>
              <div className="grid grid-3">
                {g.sites.map((s) => <SiteCard key={s.key} site={s} />)}
              </div>
            </div>
          ))}
        </div>
      </section>

      <footer className={styles.footer}>
        <div className="container">
          <span>Master — portfolio directory & deploy control.</span>
          <span className={styles.footMuted}>
            Live = deployed &amp; reachable · Staging = built, awaiting first deploy.
          </span>
        </div>
      </footer>
    </>
  );
}

function Stat({ n, label, tone }) {
  return (
    <div className={styles.stat}>
      <span className={`${styles.statN} ${tone ? styles[`tone_${tone}`] : ''}`}>{n}</span>
      <span className={styles.statLabel}>{label}</span>
    </div>
  );
}
