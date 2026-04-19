'use client';

import { useRef, useState } from 'react';

interface Props {
  audioUrl: string | null;
  durationSeconds: number | null;
  filename: string;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function AudioPlayer({ audioUrl, durationSeconds, filename }: Props) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [current, setCurrent] = useState(0);

  if (!audioUrl) {
    return (
      <p className="text-gray-400 text-sm py-4">Audio not yet available for this language.</p>
    );
  }

  const total = durationSeconds ?? 0;

  const handlePlayPause = () => {
    if (!audioRef.current) return;
    if (playing) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setPlaying(!playing);
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) setCurrent(Math.floor(audioRef.current.currentTime));
  };

  const handleEnded = () => setPlaying(false);

  const progress = total > 0 ? (current / total) * 100 : 0;

  return (
    <div className="bg-white/5 rounded-xl p-4 space-y-3">
      <audio
        ref={audioRef}
        src={audioUrl}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        preload="metadata"
      />

      {/* Progress bar */}
      <div className="w-full bg-white/10 h-1 rounded-full">
        <div
          className="bg-red-500 h-1 rounded-full transition-all"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={handlePlayPause}
            aria-label={playing ? 'Pause' : 'Play'}
            className="w-10 h-10 rounded-full bg-red-600 flex items-center justify-center text-white hover:bg-red-500 transition-colors"
          >
            {playing ? '⏸' : '▶'}
          </button>
          <span className="text-sm text-gray-400">
            <span>{formatTime(current)}</span>
            {' / '}
            <span>{total > 0 ? formatTime(total) : '--:--'}</span>
          </span>
        </div>

        <a
          href={audioUrl}
          download={filename}
          className="text-sm text-gray-300 bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg transition-colors"
        >
          ⬇ Download
        </a>
      </div>
    </div>
  );
}
