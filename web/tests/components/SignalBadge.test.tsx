import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import SignalBadge from '@/components/SignalBadge';

describe('SignalBadge', () => {
  it('displays the signal number', () => {
    render(<SignalBadge signal={4} />);
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('renders without crashing when signal is null', () => {
    render(<SignalBadge signal={null} />);
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('applies red background for signal 4', () => {
    const { container } = render(<SignalBadge signal={4} />);
    expect(container.firstChild).toHaveStyle({ backgroundColor: '#c0392b' });
  });

  it('applies orange background for signal 3', () => {
    const { container } = render(<SignalBadge signal={3} />);
    expect(container.firstChild).toHaveStyle({ backgroundColor: '#e67e22' });
  });

  it('applies yellow background for signal 2', () => {
    const { container } = render(<SignalBadge signal={2} />);
    expect(container.firstChild).toHaveStyle({ backgroundColor: '#f1c40f' });
  });

  it('applies blue background for signal 1', () => {
    const { container } = render(<SignalBadge signal={1} />);
    expect(container.firstChild).toHaveStyle({ backgroundColor: '#3498db' });
  });
});
