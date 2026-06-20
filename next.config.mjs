const isProd = process.env.NODE_ENV === 'production';

// GitHub Pages serves a project repo under /<repo>. Defaults to /master.
// Set BASE_PATH=none for a custom domain / user.github.io root.
const rawBase = process.env.BASE_PATH ?? '/master';
const repo = rawBase === 'none' || rawBase === '/' || rawBase === '' ? '' : rawBase;
const basePath = isProd ? repo : '';

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
  basePath,
  assetPrefix: basePath || undefined,
  trailingSlash: true,
  env: { NEXT_PUBLIC_BASE_PATH: basePath },
};

export default nextConfig;
