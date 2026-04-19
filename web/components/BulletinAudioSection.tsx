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
}

export default function BulletinAudioSection({ media, stem }: Props) {
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
    setScriptLoading(true);
    fetch(audioUrl(current.script_path))
      .then(r => r.text())
      .then(text => setScriptText(text))
      .catch(() => setScriptText(null))
      .finally(() => setScriptLoading(false));
  }, [language, media]);

  const current = media[language];
  const url = current?.audio_path ? audioUrl(current.audio_path) : null;
  // Only show player if audio is ready; pass null otherwise so AudioPlayer shows fallback
  const readyUrl = current?.status === 'ready' ? url : null;

  return (
    <div className="space-y-4">
      <AudioPlayer
        audioUrl={readyUrl}
        durationSeconds={current?.audio_duration_seconds ?? null}
        filename={`${stem}_${language}.mp3`}
      />
      {scriptLoading && (
        <p className="text-xs text-gray-500 px-1">Loading script...</p>
      )}
      {scriptText && !scriptLoading && (
        <details className="bg-white/5 rounded-xl p-4">
          <summary className="text-xs font-semibold text-gray-400 uppercase tracking-wide cursor-pointer">
            {t('read_bulletin')}
          </summary>
          <div className="mt-3 text-sm text-gray-300 leading-relaxed prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{scriptText}</ReactMarkdown>
          </div>
        </details>
      )}
    </div>
  );
}
