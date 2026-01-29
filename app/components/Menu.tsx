'use client'

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';

export function Menu() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button 
        id="menu-toggle" 
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Toggle menu"
      >
        <Image 
          src="https://cdn.mybustimes.cc/mybustimes/staticfiles/src/icons/Burger-Menu-Black.webp" 
          height={35} 
          width={35} 
          alt="Burger Menu Icon" 
          className="logo-light"
        />
        <Image 
          src="https://cdn.mybustimes.cc/mybustimes/staticfiles/src/icons/Burger-Menu-White.webp" 
          height={35} 
          width={35} 
          alt="Burger Menu Icon" 
          className="logo-dark"
        />
      </button>

      {isOpen && (
        <nav className="mobile-menu">
          <ul>
            <li><Link href="/" onClick={() => setIsOpen(false)}>Home</Link></li>
            <li><Link href="/about" onClick={() => setIsOpen(false)}>About</Link></li>
            <li><Link href="/search" onClick={() => setIsOpen(false)}>Search</Link></li>
            <li><Link href="/contact" onClick={() => setIsOpen(false)}>Contact</Link></li>
            <li><Link href="/report" onClick={() => setIsOpen(false)}>Report a Bug</Link></li>
            <li><Link href="/site-updates" onClick={() => setIsOpen(false)}>Site Updates</Link></li>
          </ul>
        </nav>
      )}
    </>
  );
}