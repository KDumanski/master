import { Inter, Bricolage_Grotesque } from 'next/font/google';
import './globals.css';
import ThemeScript from '@/components/ThemeScript';

const inter = Inter({ subsets: ['latin'], variable: '--font-body-stack', display: 'swap' });
const display = Bricolage_Grotesque({ subsets: ['latin'], variable: '--font-display-stack', display: 'swap' });

export const metadata = {
  title: 'Master — Portfolio & Deploy Control',
  description: 'One place for every site in the portfolio — live links, deploy status, and central staging to GitHub Pages.',
};
export const viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: dark)', color: '#0a0c10' },
    { media: '(prefers-color-scheme: light)', color: '#f4f6fb' },
  ],
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${inter.variable} ${display.variable}`} suppressHydrationWarning>
      <head><ThemeScript /></head>
      <body>{children}</body>
    </html>
  );
}
