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
      const barW = Math.floor(step * 0.6);
      const centerY = canvas.height / 2;
      ctx.fillStyle = 'rgba(239,68,68,0.25)';
      for (let i = 0; i < barCount; i++) {
        const x = i * step + (step - barW) / 2;
        ctx.beginPath();
        ctx.roundRect(x, centerY - 1, barW, 2, 1);
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
      const barW = Math.floor(step * 0.6);
      const centerY = canvas.height / 2;
      const maxH = centerY - 2;

      ctx.fillStyle = '#ef4444';
      for (let i = 0; i < half; i++) {
        const barH = Math.max(2, (data[i] / 255) * maxH);

        // Right side: bin 0 is just right of center, bin half-1 is far right
        const rx = (half + i) * step + (step - barW) / 2;
        ctx.beginPath();
        ctx.roundRect(rx, centerY - barH, barW, barH * 2, 2);
        ctx.fill();

        // Left side: mirror of right (bin 0 is just left of center)
        const lx = (half - 1 - i) * step + (step - barW) / 2;
        ctx.beginPath();
        ctx.roundRect(lx, centerY - barH, barW, barH * 2, 2);
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
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function AudioPlayer({ audioUrl, durationSeconds, filename }: Props) {
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

  const progress = total > 0 ? (current / total) * 100 : 0;

  return (
    <div className="bg-white/5 rounded-xl p-4 space-y-3">
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

      {/* Waveform */}
      <Waveform playing={playing} analyser={analyser} />

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
          ⬇ {t('download')}
        </a>
      </div>
    </div>
  );
}
