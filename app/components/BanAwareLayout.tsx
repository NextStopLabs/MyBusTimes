'use client'

import { useState, useEffect } from 'react';
import { useDeviceFingerprint } from '@/lib/useDeviceFingerprint';
import { BanMessage } from './BanMessage';

export function BanAwareLayout({ children }: { children: React.ReactNode }) {
  const [banned, setBanned] = useState<{ reason: string; type: string } | null | undefined>(undefined);
  const { fingerprint } = useDeviceFingerprint();

  useEffect(() => {
    if (!fingerprint) return;

    // Get client IP from server first, then check ban with that IP.
    // This ensures IP bans work even when the check-ban request headers don't expose the client IP (e.g. some serverless/proxy setups).
    fetch('/api/auth/my-ip')
      .then((r) => r.json())
      .then(({ ip }) =>
        fetch('/api/auth/me').then((r) => r.json()).then((data) => ({ ip, data }))
      )
      .then(async ({ ip, data }) => {
        const banCheck = await fetch('/api/auth/check-ban', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            userId: data?.user?.id,
            fingerprint,
            ip,
          }),
        }).then((r) => r.json());

        if (banCheck.banned) {
          setBanned(banCheck);
        } else {
          setBanned(null);
        }
      });
  }, [fingerprint]);

  // Only show ban screen once we have fingerprint and confirmed they're banned
  if (banned) {
    return <BanMessage banned={banned} fullPage />;
  }

  return <>{children}</>;
}
