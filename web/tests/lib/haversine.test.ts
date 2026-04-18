import { describe, it, expect } from 'vitest';
import { haversine } from '@/lib/haversine';

describe('haversine', () => {
  it('returns 0 for identical coordinates', () => {
    expect(haversine(10.3157, 123.8854, 10.3157, 123.8854)).toBe(0);
  });

  it('returns roughly 5300 km between Manila and London', () => {
    // Manila: 14.5995, 120.9842 — London: 51.5074, -0.1278
    const dist = haversine(14.5995, 120.9842, 51.5074, -0.1278);
    expect(dist).toBeGreaterThan(10000);
    expect(dist).toBeLessThan(12000);
  });

  it('returns ~582 km from Manila to Cebu City', () => {
    const dist = haversine(14.5995, 120.9842, 10.3157, 123.8854);
    expect(dist).toBeGreaterThan(550);
    expect(dist).toBeLessThan(620);
  });

  it('returns a whole number (Math.round applied)', () => {
    const dist = haversine(14.5995, 120.9842, 10.3157, 123.8854);
    expect(Number.isInteger(dist)).toBe(true);
  });
});
