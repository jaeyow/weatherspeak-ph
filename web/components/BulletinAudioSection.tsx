'use client';

import { useEffect, useState } from 'react';
import type { Language, MediaByLang } from '@/types';
import AudioPlayer from './AudioPlayer';
import { audioUrl } from '@/lib/audio-url';

interface Props {
  media: MediaByLang;
  stem: string; // used to construct a human-readable download filename
}

export default function BulletinAudioSection({ media, stem }: Props) {
  const [language, setLanguage] = useState<Language>('tl');

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

  const current = media[language];
  const url = current?.audio_path ? audioUrl(current.audio_path) : null;
  // Only show player if audio is ready; pass null otherwise so AudioPlayer shows fallback
  const readyUrl = current?.status === 'ready' ? url : null;

  return (
    <AudioPlayer
      audioUrl={readyUrl}
      durationSeconds={current?.audio_duration_seconds ?? null}
      filename={`${stem}_${language}.mp3`}
    />
  );
}
