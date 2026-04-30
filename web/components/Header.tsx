'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import LanguageToggle from './LanguageToggle';

export default function Header() {
  const [city, setCity] = useState<string | null>(null);

  useEffect(() => {
    setCity(localStorage.getItem('ws_city'));
    const handler = () => setCity(localStorage.getItem('ws_city'));
    window.addEventListener('ws:language-change', handler);
    return () => window.removeEventListener('ws:language-change', handler);
  }, []);

  return (
    <header className="sticky top-0 z-40 bg-gray-950/90 backdrop-blur border-b border-white/5">
      <div className="max-w-lg mx-auto px-4 py-3 flex items-center justify-between gap-3">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-xl">🌀</span>
          <span className="font-extrabold text-white text-base leading-none">
            WeatherSpeak PH
          </span>
        </Link>
        <div className="flex items-center gap-2">
          {city && (
            <div className="px-2.5 py-1 rounded-full bg-blue-500/20 border border-blue-500/30">
              <span className="text-xs text-blue-300 font-medium">📍 {city}</span>
            </div>
          )}
          <LanguageToggle />
        </div>
      </div>
    </header>
  );
}
