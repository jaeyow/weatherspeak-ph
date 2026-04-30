'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslation } from './LanguageProvider';

function Waveform({
  playing,
  analyser,
}: {
  playing: boolean;
  analyser: AnalyserNode | null;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;

    const drawIdle = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const barCount = 32; // matches half * 2 in the live draw loop
      const step = canvas.width / barCount;
      const barW = Math.max(2, Math.floor(step * 0.35)); // Thinner bars (0.35 instead of 0.6)
      const centerY = canvas.height / 2;
      ctx.fillStyle = 'rgba(239,68,68,0.45)'; // Raised from 0.25 to 0.45 for better visibility
      for (let i = 0; i < barCount; i++) {
        const x = i * step + (step - barW) / 2;
        ctx.beginPath();
        ctx.roundRect(x, centerY - 1, barW, 2, 0.5); // Sharper corners (0.5 instead of 1)
        ctx.fill();
      }
    };

    if (!playing || !analyser) {
      cancelAnimationFrame(rafRef.current);
      drawIdle();
      return;
    }

    const data = new Uint8Array(analyser.frequencyBinCount);

    const draw = () => {
      analyser.getByteFrequencyData(data);
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Mirror from center: bin 0 (low freq) sits at the middle,
      // higher frequencies spread outward to the left and right.
      const half = 16;                    // 16 bins per side = 32 bars total
      const barCount = half * 2;
      const step = canvas.width / barCount;
      const barW = Math.max(2, Math.floor(step * 0.35)); // Thinner bars (0.35 instead of 0.6)
      const centerY = canvas.height / 2;
      const maxH = centerY - 2;

      ctx.fillStyle = '#ef4444';
      for (let i = 0; i < half; i++) {
        const barH = Math.max(2, (data[i] / 255) * maxH);

        // Right side: bin 0 is just right of center, bin half-1 is far right
        const rx = (half + i) * step + (step - barW) / 2;
        ctx.beginPath();
        ctx.roundRect(rx, centerY - barH, barW, barH * 2, 1); // Sharper corners (1 instead of 2)
        ctx.fill();

        // Left side: mirror of right (bin 0 is just left of center)
        const lx = (half - 1 - i) * step + (step - barW) / 2;
        ctx.beginPath();
        ctx.roundRect(lx, centerY - barH, barW, barH * 2, 1); // Sharper corners (1 instead of 2)
        ctx.fill();
      }

      rafRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(rafRef.current);
  }, [playing, analyser]);

  return <canvas ref={canvasRef} width={400} height={64} className="w-full h-16" />;
}

interface Props {
  audioUrl: string | null;
  durationSeconds: number | null;
  filename: string;
  language?: string; // e.g. 'English', 'Tagalog', 'Cebuano'
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

// SVG icons to replace emoji
function PlayIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-7 h-7">
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="w-7 h-7">
      <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
    </svg>
  );
}

export default function AudioPlayer({ audioUrl, durationSeconds, filename, language }: Props) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const [analyser, setAnalyser] = useState<AnalyserNode | null>(null);
  const [playing, setPlaying] = useState(false);
  const [current, setCurrent] = useState(0);
  const { t } = useTranslation();

  useEffect(() => {
    return () => { audioCtxRef.current?.close(); };
  }, []);

  if (!audioUrl) {
    return (
      <p className="text-gray-400 text-sm py-4">{t('audio_not_available')}</p>
    );
  }

  const total = durationSeconds ?? 0;

  const handlePlayPause = () => {
    if (!audioRef.current) return;

    // Lazily create AudioContext + AnalyserNode on first play, synchronously
    // inside the click handler so browsers don't suspend the context.
    // crossOrigin="anonymous" on the <audio> element is required for
    // createMediaElementSource to work with remote (Supabase) URLs.
    if (!audioCtxRef.current) {
      try {
        const audioCtx = new AudioContext();
        const node = audioCtx.createAnalyser();
        node.fftSize = 64;
        node.smoothingTimeConstant = 0.75;
        const source = audioCtx.createMediaElementSource(audioRef.current);
        source.connect(node);
        node.connect(audioCtx.destination);
        audioCtxRef.current = audioCtx;
        setAnalyser(node); // triggers re-render so Waveform gets the node
      } catch {
        // Web Audio unavailable or CORS error — audio still plays via <audio>
      }
    }

    if (playing) {
      audioRef.current.pause();
      audioCtxRef.current?.suspend();
    } else {
      if (audioCtxRef.current) {
        audioCtxRef.current.resume().then(() => audioRef.current?.play());
      } else {
        audioRef.current.play();
      }
    }
    setPlaying(!playing);
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) setCurrent(Math.floor(audioRef.current.currentTime));
  };

  const handleEnded = () => {
    setPlaying(false);
    audioCtxRef.current?.suspend();
  };

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current || total === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const pct = clickX / rect.width;
    audioRef.current.currentTime = pct * total;
  };

  const progress = total > 0 ? (current / total) * 100 : 0;

  return (
    <div className="bg-white/5 rounded-xl p-5 space-y-4">
      {/* crossOrigin="anonymous" is required for createMediaElementSource
          to process audio from a cross-origin URL (Supabase storage) */}
      <audio
        ref={audioRef}
        src={audioUrl}
        crossOrigin="anonymous"
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        preload="metadata"
      />

      {/* Language pill */}
      {language && (
        <div className="flex items-center justify-center">
          <div className="inline-flex items-center px-4 py-1.5 rounded-full bg-red-500/20 text-red-400 text-base font-semibold tracking-wide">
            {language}
          </div>
        </div>
      )}

      {/* Waveform */}
      <Waveform playing={playing} analyser={analyser} />

      {/* Centered play button with time displays */}
      <div className="flex items-center justify-center gap-6">
        {/* Current time (left) */}
        <span className="text-sm text-gray-400 tabular-nums min-w-[3rem] text-right">
          {formatTime(current)}
        </span>

        {/* Play/Pause button - 64px, centered */}
        <button
          onClick={handlePlayPause}
          aria-label={playing ? 'Pause' : 'Play'}
          className="w-16 h-16 rounded-full bg-red-600 flex items-center justify-center text-white hover:bg-red-500 active:scale-95 transition-all shadow-lg hover:shadow-red-500/50"
        >
          {playing ? <PauseIcon /> : <PlayIcon />}
        </button>

        {/* Duration (right) */}
        <span className="text-sm text-gray-400 tabular-nums min-w-[3rem]">
          {total > 0 ? formatTime(total) : '--:--'}
        </span>
      </div>

      {/* Progress bar - thicker and clickable */}
      <div
        onClick={handleProgressClick}
        className="w-full bg-white/10 h-2 rounded-full cursor-pointer hover:h-3 transition-all"
      >
        <div
          className="bg-red-500 h-full rounded-full transition-all"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Download button - secondary style, centered below */}
      <div className="flex justify-center pt-1">
        <a
          href={audioUrl}
          download={filename}
          className="text-xs text-gray-400 hover:text-gray-200 transition-colors inline-flex items-center gap-1.5"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          <span>{t('download')}</span>
        </a>
      </div>
    </div>
  );
}
