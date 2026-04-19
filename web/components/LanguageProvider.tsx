'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import type { Language } from '@/types';
import { translations, type TranslationKey } from '@/lib/translations';

const LANGUAGES: Language[] = ['ceb', 'tl', 'en'];

interface LanguageContextValue {
  language: Language;
  t: (key: TranslationKey) => string;
}

const LanguageContext = createContext<LanguageContextValue>({
  language: 'ceb',
  t: (key) => translations.en[key],
});

export function useTranslation() {
  return useContext(LanguageContext);
}

export default function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguage] = useState<Language>('ceb');

  useEffect(() => {
    const stored = localStorage.getItem('ws_language') as Language | null;
    if (stored && LANGUAGES.includes(stored)) setLanguage(stored);

    const handler = () => {
      const updated = localStorage.getItem('ws_language') as Language | null;
      if (updated && LANGUAGES.includes(updated)) setLanguage(updated);
    };
    window.addEventListener('ws:language-change', handler);
    return () => window.removeEventListener('ws:language-change', handler);
  }, []);

  return (
    <LanguageContext.Provider value={{ language, t: (key) => translations[language][key] ?? translations.en[key] }}>
      {children}
    </LanguageContext.Provider>
  );
}
