import { describe, it, expect } from 'vitest';
import { parseAffectedAreas } from '@/lib/affected-areas';

describe('parseAffectedAreas', () => {
  it('returns empty array for null input', () => {
    expect(parseAffectedAreas(null)).toEqual([]);
  });

  it('returns empty array when all signal arrays are empty', () => {
    expect(parseAffectedAreas({ signal_1: [] })).toEqual([]);
  });

  it('returns sections sorted highest signal first', () => {
    const result = parseAffectedAreas({
      signal_1: ['Pangasinan'],
      signal_3: ['Eastern Samar'],
      signal_4: ['Leyte'],
    });
    expect(result.map(s => s.signal)).toEqual([4, 3, 1]);
  });

  it('includes areas list for each signal level', () => {
    const result = parseAffectedAreas({
      signal_2: ['Cebu', 'Bohol'],
    });
    expect(result[0]).toEqual({ signal: 2, areas: ['Cebu', 'Bohol'] });
  });

  it('omits signal levels with no areas', () => {
    const result = parseAffectedAreas({
      signal_4: ['Leyte'],
      signal_5: [],
    });
    expect(result.length).toBe(1);
    expect(result[0].signal).toBe(4);
  });
});
