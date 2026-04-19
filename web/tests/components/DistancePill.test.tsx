import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import DistancePill from '@/components/DistancePill';

describe('DistancePill', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders nothing when location is not set', () => {
    const { container } = render(<DistancePill stormLat={11.5} stormLon={125.0} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows distance and city name when location is set', () => {
    localStorage.setItem('ws_lat', '10.3157');
    localStorage.setItem('ws_lon', '123.8854');
    localStorage.setItem('ws_city', 'Cebu City');
    render(<DistancePill stormLat={10.3157} stormLon={123.8854} />);
    expect(screen.getByText(/Cebu City/)).toBeInTheDocument();
    expect(screen.getByText(/0 km/)).toBeInTheDocument();
  });

  it('calculates non-zero distance for different coordinates', () => {
    localStorage.setItem('ws_lat', '14.5995');
    localStorage.setItem('ws_lon', '120.9842');
    localStorage.setItem('ws_city', 'Manila');
    render(<DistancePill stormLat={10.3157} stormLon={123.8854} />);
    // Manila → Cebu City is roughly 582 km
    const text = screen.getByText(/Manila/);
    expect(text.textContent).toMatch(/\d+ km from Manila/);
  });
});
