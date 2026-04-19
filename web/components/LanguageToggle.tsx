'use client';

import { useEffect, useState } from 'react';
import type { Language } from '@/types';

const LABELS: Record<Language, string> = { ceb: 'CEB', tl: 'TL', en: 'EN' };
const LANGUAGES: Language[] = ['ceb', 'tl', 'en'];

export default function LanguageToggle() {
  const [selected, setSelected] = useState<Language>('ceb');

  useEffect(() => {
    const stored = localStorage.getItem('ws_language') as Language | null;
    if (stored && LANGUAGES.includes(stored)) setSelected(stored);
  }, []);

  const handleSelect = (lang: Language) => {
    setSelected(lang);
    localStorage.setItem('ws_language', lang);
    window.dispatchEvent(new Event('ws:language-change'));
  };

  return (
    <div className="flex rounded-lg overflow-hidden border border-white/10">
      {LANGUAGES.map(lang => (
        <button
          key={lang}
          onClick={() => handleSelect(lang)}
          className={`px-3 py-1 text-sm font-semibold transition-colors ${
            selected === lang
              ? 'bg-red-600 text-white'
              : 'bg-white/5 text-gray-400 hover:bg-white/10'
          }`}
        >
          {LABELS[lang]}
        </button>
      ))}
    </div>
  );
}
