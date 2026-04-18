import { describe, it, expect } from 'vitest';
import { getProvinces, getCitiesForProvince, getCityCoords } from '@/lib/geography';

describe('getProvinces', () => {
  it('returns a non-empty sorted list of province names', () => {
    const provinces = getProvinces();
    expect(provinces.length).toBeGreaterThan(0);
    expect(provinces).toEqual([...provinces].sort());
  });

  it('includes Metro Manila and Cebu', () => {
    const provinces = getProvinces();
    expect(provinces).toContain('Metro Manila');
    expect(provinces).toContain('Cebu');
  });
});

describe('getCitiesForProvince', () => {
  it('returns cities belonging to the given province', () => {
    const cities = getCitiesForProvince('Cebu');
    expect(cities.length).toBeGreaterThan(0);
    expect(cities).toContain('Cebu City');
  });

  it('returns empty array for unknown province', () => {
    expect(getCitiesForProvince('Atlantis')).toEqual([]);
  });
});

describe('getCityCoords', () => {
  it('returns lat/lon for a known city', () => {
    const coords = getCityCoords('Cebu City');
    expect(coords).not.toBeNull();
    expect(coords!.lat).toBeCloseTo(10.3157, 1);
    expect(coords!.lon).toBeCloseTo(123.8854, 1);
  });

  it('returns null for unknown city', () => {
    expect(getCityCoords('Gotham')).toBeNull();
  });
});
