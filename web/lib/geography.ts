import geo from '@/data/philippines-geography.json';
import type { PhilippinesGeography, GeoCity } from '@/types';

const data = geo as PhilippinesGeography;

export function getProvinces(): string[] {
  return Object.keys(data.provinces).sort();
}

export function getCitiesForProvince(province: string): string[] {
  return Object.entries(data.cities)
    .filter(([, city]) => city.province === province)
    .map(([name]) => name)
    .sort();
}

export function getCityCoords(city: string): { lat: number; lon: number } | null {
  const entry = data.cities[city] as GeoCity | undefined;
  if (!entry) return null;
  return { lat: entry.lat, lon: entry.lon };
}
