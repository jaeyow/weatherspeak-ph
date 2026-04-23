import { createServerClient } from './server';
import type { StormWithStatus, Bulletin, BulletinMedia, MediaByLang, Language } from '@/types';

function toMediaByLang(media: BulletinMedia[]): MediaByLang {
  return media.reduce<MediaByLang>((acc, m) => {
    acc[m.language as Language] = m;
    return acc;
  }, {});
}

export async function getActiveStorms(): Promise<StormWithStatus[]> {
  const supabase = createServerClient();
  const { data, error } = await supabase
    .from('storms_with_status')
    .select('*')
    .eq('is_active', true)
    .order('current_signal', { ascending: false, nullsFirst: false })
    .order('last_bulletin_at', { ascending: false });

  if (error) {
    console.error('[getActiveStorms]', error.message);
    return [];
  }
  return (data ?? []) as StormWithStatus[];
}

export async function getPastStorms(): Promise<StormWithStatus[]> {
  const supabase = createServerClient();
  const { data, error } = await supabase
    .from('storms_with_status')
    .select('*')
    .eq('is_active', false)
    .order('last_bulletin_at', { ascending: false })
    .limit(20);

  if (error) {
    console.error('[getPastStorms]', error.message);
    return [];
  }
  return (data ?? []) as StormWithStatus[];
}

export interface StormDetail {
  storm: StormWithStatus;
  latestBulletin: Bulletin;
  latestMedia: MediaByLang;
  bulletinHistory: Array<{
    id: string;
    bulletin_number: number | null;
    issued_at: string | null;
    pdf_url: string | null;
  }>;
}

export async function getStormDetail(stormId: string): Promise<StormDetail | null> {
  const supabase = createServerClient();

  const { data: storm, error: stormErr } = await supabase
    .from('storms_with_status')
    .select('*')
    .eq('id', stormId)
    .single();

  if (stormErr || !storm) return null;

  const { data: bulletins, error: bulletinErr } = await supabase
    .from('bulletins')
    .select('*, bulletin_media(*)')
    .eq('storm_id', stormId)
    .order('issued_at', { ascending: false });

  if (bulletinErr || !bulletins || bulletins.length === 0) return null;

  const [latest, ...rest] = bulletins as (Bulletin & { bulletin_media: BulletinMedia[] })[];

  return {
    storm: storm as StormWithStatus,
    latestBulletin: latest,
    latestMedia: toMediaByLang(latest.bulletin_media ?? []),
    bulletinHistory: rest.map(b => ({
      id: b.id,
      bulletin_number: b.bulletin_number,
      issued_at: b.issued_at,
      pdf_url: b.pdf_url ?? null,
    })),
  };
}

export interface BulletinDetail {
  bulletin: Bulletin;
  media: MediaByLang;
  stormId: string;
}

export async function getBulletin(bulletinId: string): Promise<BulletinDetail | null> {
  const supabase = createServerClient();

  const { data, error } = await supabase
    .from('bulletins')
    .select('*, bulletin_media(*)')
    .eq('id', bulletinId)
    .single();

  if (error || !data) return null;

  const bulletin = data as Bulletin & { bulletin_media: BulletinMedia[] };

  return {
    bulletin,
    media: toMediaByLang(bulletin.bulletin_media ?? []),
    stormId: bulletin.storm_id,
  };
}
