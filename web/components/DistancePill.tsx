'use client';

import { useEffect, useState } from 'react';
import { haversine } from '@/lib/haversine';

interface Props {
  stormLat: number;
  stormLon: number;
}

export default function DistancePill({ stormLat, stormLon }: Props) {
  const [label, setLabel] = useState<string | null>(null);

  useEffect(() => {
    const lat = parseFloat(localStorage.getItem('ws_lat') ?? '');
    const lon = parseFloat(localStorage.getItem('ws_lon') ?? '');
    const city = localStorage.getItem('ws_city');
    if (!city || isNaN(lat) || isNaN(lon)) return;
    const dist = haversine(lat, lon, stormLat, stormLon);
    setLabel(`📍 ${dist} km from ${city}`);
  }, [stormLat, stormLon]);

  if (!label) return null;
  return (
    <span className="text-sm font-medium text-orange-400">{label}</span>
  );
}
