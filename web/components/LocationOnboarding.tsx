'use client';

import { useEffect, useState } from 'react';
import { getProvinces, getCitiesForProvince, getCityCoords } from '@/lib/geography';
import type { Language } from '@/types';
import { useTranslation } from './LanguageProvider';

const LANGUAGES: { code: Language; label: string }[] = [
  { code: 'ceb', label: 'Cebuano' },
  { code: 'tl', label: 'Tagalog' },
  { code: 'en', label: 'English' },
];

export default function LocationOnboarding() {
  const [show, setShow] = useState(false);
  const [province, setProvince] = useState('');
  const [city, setCity] = useState('');
  const [language, setLanguage] = useState<Language>('ceb');
  const provinces = getProvinces();
  const { t } = useTranslation();

  useEffect(() => {
    if (!localStorage.getItem('ws_province')) setShow(true);
  }, []);

  if (!show) return null;

  const cities = province ? getCitiesForProvince(province) : [];

  const handleProvince = (p: string) => {
    setProvince(p);
    setCity('');
  };

  const handleSubmit = () => {
    if (!province || !city) return;
    const coords = getCityCoords(city);
    localStorage.setItem('ws_province', province);
    localStorage.setItem('ws_city', city);
    localStorage.setItem('ws_language', language);
    if (coords) {
      localStorage.setItem('ws_lat', String(coords.lat));
      localStorage.setItem('ws_lon', String(coords.lon));
    }
    window.dispatchEvent(new Event('ws:language-change'));
    setShow(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
      <div className="bg-gray-900 rounded-2xl p-6 w-full max-w-sm space-y-5">
        {/* Header */}
        <div className="text-center">
          <div className="text-4xl mb-2">🌀</div>
          <h2 className="text-xl font-bold text-white">WeatherSpeak PH</h2>
          <p className="text-sm text-gray-400 mt-1">{t('setup_subtitle')}</p>
        </div>

        {/* Location */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-gray-300 uppercase tracking-wide">
            📍 {t('your_location')}
          </label>
          <select
            value={province}
            onChange={e => handleProvince(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white"
          >
            <option value="">Province ▾</option>
            {provinces.map(p => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <select
            value={city}
            onChange={e => setCity(e.target.value)}
            disabled={!province}
            className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white disabled:opacity-40"
          >
            <option value="">City / Municipality ▾</option>
            {cities.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        {/* Language */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-gray-300 uppercase tracking-wide">
            🌐 Language / Wika / Pinulongan
          </label>
          <div className="flex gap-2">
            {LANGUAGES.map(l => (
              <button
                key={l.code}
                onClick={() => setLanguage(l.code)}
                className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-colors ${
                  language === l.code
                    ? 'bg-red-600 text-white'
                    : 'bg-white/5 text-gray-400 hover:bg-white/10'
                }`}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={!province || !city}
          className="w-full bg-red-600 hover:bg-red-500 disabled:opacity-40 text-white font-bold py-3 rounded-lg transition-colors"
        >
          {t('get_started')}
        </button>
      </div>
    </div>
  );
}
