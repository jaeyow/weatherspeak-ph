import { describe, it, expect, beforeEach } from 'vitest';

describe('audioUrl', () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_SUPABASE_URL = 'https://test.supabase.co';
  });

  it('constructs a full public storage URL from a path', async () => {
    const { audioUrl } = await import('@/lib/audio-url');
    const url = audioUrl('PAGASA_20-19W_Pepito_SWB_01/audio_en.mp3');
    expect(url).toBe(
      'https://test.supabase.co/storage/v1/object/public/weatherspeak-public/PAGASA_20-19W_Pepito_SWB_01/audio_en.mp3'
    );
  });

  it('handles paths without a leading slash', async () => {
    const { audioUrl } = await import('@/lib/audio-url');
    const url = audioUrl('somepath/audio_tl.mp3');
    expect(url).toContain('/storage/v1/object/public/weatherspeak-public/somepath/audio_tl.mp3');
  });
});
