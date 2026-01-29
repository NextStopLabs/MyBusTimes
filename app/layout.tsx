import type { Metadata } from "next";
import Link from "next/link";
import Image from 'next/image';
import Script from 'next/script';
import { Providers } from './providers';
import { ThemeToggle } from './components/ThemeToggle';
import { Menu } from './components/Menu';
import "./globals.css";


export const metadata: Metadata = {
  title: "Oops Someone forgot there title",
  description: "Please tell Kai to add a title to this page",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <Script src="/js/ads.js" strategy="beforeInteractive" />
      </head>
      <body>
        <Providers>
          <header className="header">
            <div className="site-header">
              <Link href="/">
                <Image src="https://cdn.mybustimes.cc/assets/main/Logo-Dark.svg" alt="Logo" width={175} height={55} className="logo-light"/>
                <Image src="https://cdn.mybustimes.cc/assets/main/Logo.svg" alt="Logo" width={175} height={55} className="logo-dark"/>
              </Link>
              <Menu />
              <form action="/search">
                <input type="search" name="q" id="q" placeholder="Search"/>
                <input type="submit" value="Search" className="search"/>
              </form>
            </div>
          </header>
          <main>
            {children}
          </main>
          <footer>
            <div className="ad-box" id="footer-ad-1"></div>
            <hr/>
            <ul className="footer-info">
                <li><Link href="/about">About</Link></li>•
                <li><Link href="/report">Report a Bug</Link></li>•
                <li><Link href="/site-updates">Site Updates</Link></li>•
                <li><Link href="/contact">Contact Us</Link></li>
            </ul>
            <hr/>
            <ul className="footer-info">
                <li><Link href="/rules/#terms">Terms and Conditions</Link></li>•
                <li><Link href="/rules/#content">User Generated Content</Link></li>
            </ul>
            <br/>
            <ul className="footer-info">
                <li><Link href="/rules/#privacy">Privacy Policy</Link></li>•
                <li><Link href="/rules/#copyright">Copyright Policy</Link></li>•
                <li><Link href="/rules/#rules">Ban Policy</Link></li>
            </ul>
            <hr/>
            <label htmlFor="theme-selector">Select Theme:</label>
            <select id="theme-selector" name="theme">
            </select>
            <br/>
            <ThemeToggle />
            <br/>
            <ul className="footer-info">
                <li id="users-stats">Online: 24 | Total: 3530</li>
            </ul>
            <br/>
            <ul className="footer-info">
                <li><Link href="https://status.mybustimes.cc/status/mbt">Site Status</Link></li>•
                <li><Link href="/data">Data Sources</Link></li>
            </ul>
            <hr/>
            <p style={{ marginTop: "30px" }}>
                Note: MyBusTimes is a fictional and community-run transport database.<br/>
                All data shown here is user generated and not real world data.
            </p>
            <br/>
            <Link href="https://github.com/Kai-codin/MyBusTimes">MyBusTimes</Link> ©<span id="year">2026</span> by <Link
                href="https://github.com/Kai-codin">KaiCodin</Link> is licensed under <Link
                href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</Link><img
                src="https://mirrors.creativecommons.org/presskit/icons/cc.svg" alt=""
                style={{ maxWidth: "1em", maxHeight: "1em", marginLeft: ".2em", marginBottom: 0 }} /><img
                src="https://mirrors.creativecommons.org/presskit/icons/by.svg" alt=""
                style={{ maxWidth: "1em", maxHeight: "1em", marginLeft: ".2em", marginBottom: 0 }} /><img
                src="https://mirrors.creativecommons.org/presskit/icons/nc.svg" alt=""
                style={{ maxWidth: "1em", maxHeight: "1em", marginLeft: ".2em", marginBottom: 0 }} /><img
                src="https://mirrors.creativecommons.org/presskit/icons/sa.svg" alt=""
                style={{ maxWidth: "1em", maxHeight: "1em", marginLeft: ".2em", marginBottom: 0 }} />
        </footer>
        </Providers>
      </body>
    </html>
  );
}