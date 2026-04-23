'use client';

import { useState } from 'react';
import PageLabel from '@/components/PageLabel';

interface Props {
  chartUrl: string | null;
  pdfUrl: string | null;
  stormName: string;
  bulletinNumber: number | null;
}

export default function LatestBulletinSection({ chartUrl, pdfUrl, stormName, bulletinNumber }: Props) {
  const [isExpanded, setIsExpanded] = useState(true);

  const handleToggle = () => {
    setIsExpanded(prev => !prev);
  };

  if (!chartUrl) return null;

  return (
    <div className="rounded-xl overflow-hidden bg-white/5">
      {/* Header - always clickable */}
      <button
        onClick={handleToggle}
        type="button"
        className="w-full flex justify-between items-center px-3 pt-3 pb-2 text-left hover:bg-white/10 cursor-pointer active:bg-white/15 transition-colors"
      >
        <p className="text-xs text-gray-400 uppercase tracking-wide">
          <PageLabel k="storm_track" />
        </p>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${isExpanded ? 'rotate-180' : 'rotate-0'}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Chart image - shows when expanded */}
      {isExpanded && chartUrl && (
        /* eslint-disable-next-line @next/next/no-img-element */
        <img
          src={chartUrl}
          alt={`Storm track chart for ${stormName}`}
          className="w-full h-auto"
        />
      )}
    </div>
  );
}
