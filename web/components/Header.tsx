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

  const handleChangeLocation = () => {
    window.dispatchEvent(new Event('ws:change-location'));
  };

  return (
    <header className="sticky top-0 z-40 bg-gray-950/90 backdrop-blur border-b border-white/5">
      <div className="max-w-lg md:max-w-2xl lg:max-w-4xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-xl">🌀</span>
          <span className="font-extrabold text-white text-base leading-none">
            WeatherSpeak PH
          </span>
        </Link>
        <div className="flex items-center gap-2">
          {city && (
            <button
              onClick={handleChangeLocation}
              className="px-2.5 py-1 rounded-full bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 hover:border-blue-500/50 transition-colors cursor-pointer"
              title="Change location"
            >
              <span className="text-xs text-blue-300 font-medium">📍 {city}</span>
            </button>
          )}
          <LanguageToggle />
        </div>
      </div>
    </header>
  );
}
