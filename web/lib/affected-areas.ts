import type { AffectedAreas, SignalSection } from '@/types';

export function parseAffectedAreas(areas: AffectedAreas | null): SignalSection[] {
  if (!areas) return [];
  const signals = [5, 4, 3, 2, 1] as const;
  return signals
    .map(signal => ({
      signal,
      areas: (areas[`signal_${signal}` as keyof AffectedAreas] as string[] | undefined) ?? [],
    }))
    .filter(({ areas }) => areas.length > 0);
}
