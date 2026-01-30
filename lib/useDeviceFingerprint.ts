'use client'
import { useEffect, useState } from 'react';

export function useDeviceFingerprint() {
  const [fingerprint, setFingerprint] = useState<string | null>(null);
  const [deviceDetails, setDeviceDetails] = useState<string | null>(null);

  useEffect(() => {
    // Generate fingerprint from browser properties
    const generateFingerprint = () => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillText('fingerprint', 2, 2);
      }
      
      const data = {
        userAgent: navigator.userAgent,
        language: navigator.language,
        screen: `${screen.width}x${screen.height}`,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        canvas: canvas.toDataURL(),
        platform: navigator.platform,
      };

      // Simple hash function
      const hash = JSON.stringify(data).split('').reduce((a, b) => {
        a = ((a << 5) - a) + b.charCodeAt(0);
        return a & a;
      }, 0);

      return Math.abs(hash).toString(16);
    };

    const fp = generateFingerprint();
    setFingerprint(fp);
    setDeviceDetails(JSON.stringify({
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      language: navigator.language,
    }));
  }, []);

  return { fingerprint, deviceDetails };
}