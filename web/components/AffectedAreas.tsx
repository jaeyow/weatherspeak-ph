'use client';

import { useState } from 'react';
import { parseAffectedAreas } from '@/lib/affected-areas';
import type { AffectedAreas as AffectedAreasType } from '@/types';

const SIGNAL_COLORS: Record<number, string> = {
  1: 'bg-blue-900/40 border-blue-700',
  2: 'bg-yellow-900/40 border-yellow-700',
  3: 'bg-orange-900/40 border-orange-700',
  4: 'bg-red-900/40 border-red-700',
  5: 'bg-red-900/60 border-red-600',
};

interface Props {
  areas: AffectedAreasType | null;
}

export default function AffectedAreas({ areas }: Props) {
  const [open, setOpen] = useState<number | null>(null);
  const sections = parseAffectedAreas(areas);

  if (sections.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
        Affected Areas
      </h3>
      {sections.map(({ signal, areas: list }) => (
        <div
          key={signal}
          className={`border rounded-lg overflow-hidden ${SIGNAL_COLORS[signal] ?? 'bg-gray-900/40 border-gray-700'}`}
        >
          <button
            onClick={() => setOpen(open === signal ? null : signal)}
            className="w-full flex items-center justify-between px-4 py-3 text-left"
          >
            <span className="font-semibold text-white text-sm">
              Signal #{signal}
            </span>
            <span className="text-gray-400 text-xs">
              {list.length} area{list.length !== 1 ? 's' : ''} {open === signal ? '▲' : '▼'}
            </span>
          </button>
          {open === signal && (
            <ul className="px-4 pb-3 space-y-1">
              {list.map(area => (
                <li key={area} className="text-sm text-gray-300">
                  {area}
                </li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}
