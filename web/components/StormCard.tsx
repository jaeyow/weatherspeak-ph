import Link from 'next/link';
import SignalBadge from './SignalBadge';
import DistancePill from './DistancePill';
import type { StormWithStatus } from '@/types';

interface Props {
  storm: StormWithStatus;
  compact?: boolean; // true for past storms section
}

function timeAgo(iso: string | null): string {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3_600_000);
  if (h < 1) return 'just now';
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// SVG speaker icon for audio availability
function AudioIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
      <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
    </svg>
  );
}

export default function StormCard({ storm, compact = false }: Props) {
  if (compact) {
    return (
      <Link
        href={`/storms/${storm.id}`}
        className="flex items-center gap-3 p-3 rounded-xl bg-white/5 hover:bg-white/10 transition-colors"
      >
        <SignalBadge signal={storm.current_signal} />
        <div className="flex-1 min-w-0 flex items-center justify-between gap-2">
          <div className="min-w-0">
            <div className="font-bold text-white truncate">{storm.storm_name}</div>
            <div className="text-xs text-gray-400">
              {storm.current_category} · {timeAgo(storm.last_bulletin_at)}
            </div>
          </div>
          {/* Audio availability indicator */}
          <div className="flex-shrink-0">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/20 border border-red-500/40 text-red-300 text-sm font-medium">
              <AudioIcon />
              Audio
            </span>
          </div>
        </div>
      </Link>
    );
  }

  return (
    <Link
      href={`/storms/${storm.id}`}
      className="flex items-center gap-4 p-4 rounded-2xl bg-white/5 hover:bg-white/10 transition-colors"
    >
      <SignalBadge signal={storm.current_signal} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="text-xl font-extrabold text-white">{storm.storm_name}</div>
          {/* Audio availability indicator */}
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-red-500/20 border border-red-500/40 text-red-300 text-sm font-medium">
            <AudioIcon />
            Audio
          </span>
        </div>
        <div className="text-sm text-gray-400">{storm.current_category}</div>
        {storm.current_reference && (
          <div className="text-xs text-gray-500 truncate mt-0.5">{storm.current_reference}</div>
        )}
        <div className="mt-1 flex flex-wrap gap-2 items-center">
          {storm.current_lat != null && storm.current_lon != null && (
            <DistancePill stormLat={storm.current_lat} stormLon={storm.current_lon} />
          )}
          <span className="text-xs text-gray-500">{timeAgo(storm.last_bulletin_at)}</span>
        </div>
      </div>
    </Link>
  );
}
