'use client'
import { useState, useEffect } from 'react';
import { useDeviceFingerprint } from '@/lib/useDeviceFingerprint';
import Link from 'next/link';
import Image from 'next/image';

export function Menu() {
  const [isOpen, setIsOpen] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [isStaff, setIsStaff] = useState(false);
  const [isSuperuser, setIsSuperuser] = useState(false);
  const [banned, setBanned] = useState<any>(null);
  const { fingerprint, deviceDetails } = useDeviceFingerprint();

  useEffect(() => {
    if (!fingerprint) return;

    fetch('/api/auth/me')
      .then((r) => r.json())
      .then(async (data) => {
        setUsername(data?.user?.username ?? null);
        setIsStaff(data?.user?.isStaff ?? false);
        setIsSuperuser(data?.user?.isSuperuser ?? false);
        
        // Check ban status
        const banCheck = await fetch('/api/auth/check-ban', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            userId: data?.user?.id,
            fingerprint,
          }),
        }).then(r => r.json());
        
        if (banCheck.banned) {
          setBanned(banCheck);
        } else if (data?.user?.id && deviceDetails) {
          // Track device/IP if logged in and not banned
          fetch('/api/auth/track', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              userId: data.user.id,
              fingerprint,
              deviceDetails,
            }),
          });
        }
      });
  }, [fingerprint, deviceDetails]);

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
            {username ? (
              <Link href={`/u/${username}`} onClick={() => setIsOpen(false)}>
                <li>Signed in as <strong>{username}</strong></li>
              </Link>
            ) : (
              <Link href="/account/login" onClick={() => setIsOpen(false)}>
                <li>Login</li>
              </Link>
            )}
            <Link href="/" onClick={() => setIsOpen(false)}><li>Home</li></Link>
            <Link href="/report" onClick={() => setIsOpen(false)}><li>Report a Bug</li></Link>
            <Link href="/site-updates" onClick={() => setIsOpen(false)}><li>Site Updates</li></Link>
            <Link href="/subscribe" onClick={() => setIsOpen(false)}><li>Subscribe</li></Link>
          </ul>
          
          {/* Admin links */}
          {(isStaff || isSuperuser) && (
            <ul>
              {isStaff && (
                <Link href="/staff/" onClick={() => setIsOpen(false)}>
                  <li>Staff Portal</li>
                </Link>
              )}
              {isSuperuser && (
                <Link href="/admin/" onClick={() => setIsOpen(false)}>
                  <li>Admin Portal</li>
                </Link>
              )}
            </ul>
          )}
          
          <hr />
          
          {username && (
            <ul>
              <Link href="/account/logout" onClick={() => setIsOpen(false)}>
                <li>Logout</li>
              </Link>
            </ul>
          )}
        </nav>
      )}
    </>
  );
}