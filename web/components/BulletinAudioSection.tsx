'use client';

import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Language, MediaByLang } from '@/types';
import AudioPlayer from './AudioPlayer';
import { audioUrl } from '@/lib/audio-url';
import { useTranslation } from './LanguageProvider';

interface Props {
  media: MediaByLang;
  stem: string; // used to construct a human-readable download filename
  autoplay?: boolean; // URL parameter ?autoplay=1
}

const languageNames: Record<Language, string> = {
  en: 'English',
  tl: 'Tagalog',
  ceb: 'Cebuano',
};

export default function BulletinAudioSection({ media, stem, autoplay }: Props) {
  const [language, setLanguage] = useState<Language>('ceb');
  const [scriptText, setScriptText] = useState<string | null>(null);
  const [scriptLoading, setScriptLoading] = useState(false);
  const { t } = useTranslation();

  useEffect(() => {
    const stored = localStorage.getItem('ws_language') as Language | null;
    if (stored) setLanguage(stored);

    const handler = () => {
      const updated = localStorage.getItem('ws_language') as Language | null;
      if (updated) setLanguage(updated);
    };
    window.addEventListener('ws:language-change', handler);
    return () => window.removeEventListener('ws:language-change', handler);
  }, []);

  useEffect(() => {
    const current = media[language];
    if (!current?.script_path) {
      setScriptText(null);
      return;
    }
    let cancelled = false;
    setScriptLoading(true);
    fetch(audioUrl(current.script_path))
      .then(r => r.text())
      .then(text => { if (!cancelled) setScriptText(text); })
      .catch(() => { if (!cancelled) setScriptText(null); })
      .finally(() => { if (!cancelled) setScriptLoading(false); });
    return () => { cancelled = true; };
  }, [language, media]);

  const current = media[language];
  const url = current?.audio_path ? audioUrl(current.audio_path) : null;
  // Only show player if audio is ready; pass null otherwise so AudioPlayer shows fallback
  const readyUrl = current?.status === 'ready' ? url : null;

  return (
    <div className="space-y-4">
      {/* Hero CTA */}
      {readyUrl && (
        <div className="text-center py-2">
          <p className="text-sm text-gray-300">
            {t('tap_to_hear')} <span className="text-red-400 font-medium">{languageNames[language]}</span>
          </p>
        </div>
      )}

      <AudioPlayer
        audioUrl={readyUrl}
        durationSeconds={current?.audio_duration_seconds ?? null}
        filename={`${stem}_${language}.mp3`}
        language={languageNames[language]}
        autoplay={autoplay}
      />
      {scriptLoading && (
        <p className="text-xs text-gray-500 px-1">Loading script...</p>
      )}
      {scriptText && !scriptLoading && (
        <details className="bg-white/5 rounded-xl p-4">
          <summary className="text-xs font-semibold text-gray-400 uppercase tracking-wide cursor-pointer hover:text-gray-300 transition-colors">
            {t('read_bulletin')}
            {scriptText && (
              <span className="block mt-2 text-sm font-normal text-gray-500 normal-case tracking-normal line-clamp-1">
                {scriptText.split('\n').find(line => line.trim().length > 0)?.replace(/^#+\s*/, '')}
              </span>
            )}
          </summary>
          <div className="mt-3 text-sm text-gray-300 leading-relaxed prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{scriptText}</ReactMarkdown>
          </div>
        </details>
      )}
    </div>
  );
}
