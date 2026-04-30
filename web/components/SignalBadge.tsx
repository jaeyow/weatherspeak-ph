'use client';

import { useState } from 'react';

const SIGNAL_COLORS: Record<number, string> = {
  1: '#3498db',
  2: '#f1c40f',
  3: '#e67e22',
  4: '#c0392b',
  5: '#c0392b',
};

const SIGNAL_INFO: Record<number, { name: string; description: string }> = {
  1: { name: 'Signal #1', description: 'Strong winds expected. Secure light objects.' },
  2: { name: 'Signal #2', description: 'Damaging winds. Stay indoors, secure property.' },
  3: { name: 'Signal #3', description: 'Destructive winds. Evacuate if advised.' },
  4: { name: 'Signal #4', description: 'Very destructive winds. Evacuate immediately.' },
  5: { name: 'Signal #5', description: 'Catastrophic winds. Life-threatening situation.' },
};

interface Props {
  signal: number | null;
  showTooltip?: boolean; // Show info icon and tooltip
}

export default function SignalBadge({ signal, showTooltip = false }: Props) {
  const [showInfo, setShowInfo] = useState(false);
  const bg = signal != null ? (SIGNAL_COLORS[signal] ?? '#6b7280') : '#6b7280';
  const info = signal != null ? SIGNAL_INFO[signal] : null;

  return (
    <div className="relative group">
      <div
        style={{ backgroundColor: bg }}
        className="w-14 h-14 rounded-lg flex flex-col items-center justify-center flex-shrink-0 group-hover:scale-105 group-hover:shadow-lg transition-all"
      >
        <span className="text-xs text-white/60 group-hover:text-white/80 uppercase leading-none transition-colors">SIG</span>
        <span className="text-3xl font-extrabold text-white leading-none">
          {signal ?? '—'}
        </span>
      </div>
      
      {/* Tooltip on hover */}
      {showTooltip && info && (
        <div className="absolute left-0 top-full mt-2 w-64 bg-gray-900 text-white text-xs rounded-lg p-3 shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
          <div className="font-semibold mb-1">{info.name}</div>
          <div className="text-gray-300">{info.description}</div>
        </div>
      )}
    </div>
  );
}
