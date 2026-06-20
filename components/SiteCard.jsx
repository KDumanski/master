import styles from './SiteCard.module.css';

// Initials avatar from the site name (e.g. "World Cup 2026" -> "WC").
function initials(name) {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase();
}

// Pure server component — no event handlers. The card is a <div>; the site name
// is the primary link (stretched to cover the card via CSS), and the repo link
// is a separate sibling that sits above it. No nested anchors, valid HTML.
export default function SiteCard({ site }) {
  const isLive = site.status === 'live';
  const repoUrl = `https://github.com/${site.owner}/${site.repo}`;
  const accent = isLive ? 'var(--accent2)' : 'var(--amber)';

  return (
    <div className={`${styles.card} ${isLive ? styles.cardLive : ''}`} style={{ '--accent-site': accent }}>
      <div className={styles.top}>
        <span className={styles.avatar} aria-hidden>{initials(site.name)}</span>
        <span className={`${styles.status} ${isLive ? styles.live : styles.staging}`}>
          <span className={styles.dot} aria-hidden />
          {isLive ? 'Live' : 'Staging'}
        </span>
      </div>

      <h3 className={styles.name}>
        {isLive ? (
          // Stretched link — makes the whole card clickable without nesting anchors.
          <a className={styles.stretch} href={site.url} target="_blank" rel="noopener noreferrer">{site.name}</a>
        ) : (
          site.name
        )}
      </h3>
      <p className={styles.blurb}>{site.blurb}</p>

      <div className={styles.meta}>
        {site.hosting === 'domain'
          ? <span className={styles.domain}>🌐 {site.domain}</span>
          : <span className={styles.pages}>📄 GitHub Pages</span>}
        <span className={styles.stack}>{site.stack === 'next' ? 'Next.js' : 'Static'}</span>
      </div>

      <div className={styles.foot}>
        {isLive
          ? <span className={styles.visit}>Visit site →</span>
          : <span className={styles.pending}>Not deployed yet</span>}
        {/* sits above the stretched link so it stays independently clickable */}
        <a className={styles.repo} href={repoUrl} target="_blank" rel="noopener noreferrer">code ↗</a>
      </div>
    </div>
  );
}
