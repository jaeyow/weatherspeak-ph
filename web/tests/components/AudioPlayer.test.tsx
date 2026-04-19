import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import AudioPlayer from '@/components/AudioPlayer';

describe('AudioPlayer', () => {
  it('renders play button when audioUrl is provided', () => {
    render(
      <AudioPlayer
        audioUrl="https://example.com/audio.mp3"
        durationSeconds={272}
        filename="bulletin-en.mp3"
      />
    );
    expect(screen.getByRole('button', { name: /play/i })).toBeInTheDocument();
  });

  it('renders a download link pointing to the audio URL', () => {
    render(
      <AudioPlayer
        audioUrl="https://example.com/audio.mp3"
        durationSeconds={272}
        filename="bulletin-en.mp3"
      />
    );
    const link = screen.getByRole('link', { name: /download/i });
    expect(link).toHaveAttribute('href', 'https://example.com/audio.mp3');
    expect(link).toHaveAttribute('download', 'bulletin-en.mp3');
  });

  it('shows "Audio not yet available" when audioUrl is null', () => {
    render(<AudioPlayer audioUrl={null} durationSeconds={null} filename="bulletin-en.mp3" />);
    expect(screen.getByText(/audio not yet available/i)).toBeInTheDocument();
  });

  it('formats duration as mm:ss', () => {
    render(
      <AudioPlayer
        audioUrl="https://example.com/audio.mp3"
        durationSeconds={272}
        filename="bulletin-en.mp3"
      />
    );
    expect(screen.getByText('4:32')).toBeInTheDocument();
  });
});
