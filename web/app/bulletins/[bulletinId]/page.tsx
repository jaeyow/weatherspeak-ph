import { notFound } from 'next/navigation';
import Image from 'next/image';
import Link from 'next/link';
import { getBulletin } from '@/lib/supabase/queries';
import { audioUrl } from '@/lib/audio-url';
import { formatDate } from '@/lib/format-date';
import BulletinAudioSection from '@/components/BulletinAudioSection';
import AffectedAreas from '@/components/AffectedAreas';
import DistancePill from '@/components/DistancePill';

export const revalidate = 600; // 10 minutes

interface Props {
  params: { bulletinId: string };
}

export default async function BulletinDetailPage({ params }: Props) {
  const detail = await getBulletin(params.bulletinId);
  if (!detail) notFound();

  const { bulletin, media, stormId } = detail;
  const chartUrl = bulletin.chart_path ? audioUrl(bulletin.chart_path) : null;

  return (
    <div className="space-y-6">
      {/* Back */}
      <Link
        href={`/storms/${stormId}`}
        className="text-sm text-gray-400 hover:text-white transition-colors"
      >
        ← Back to Storm
      </Link>

      {/* Header */}
      <div className="rounded-2xl bg-white/5 p-5 space-y-1">
        <div className="text-xs text-gray-400 uppercase tracking-wide">
          {bulletin.bulletin_type} · Bulletin #{bulletin.bulletin_number}
        </div>
        <p className="text-white font-semibold">{bulletin.current_reference}</p>
        {bulletin.current_lat != null && bulletin.current_lon != null && (
          <DistancePill stormLat={bulletin.current_lat} stormLon={bulletin.current_lon} />
        )}
        <p className="text-xs text-gray-500">{formatDate(bulletin.issued_at)}</p>
      </div>

      {/* Audio */}
      <BulletinAudioSection media={media} stem={bulletin.stem} />

      {/* Chart */}
      {chartUrl && (
        <div className="rounded-xl overflow-hidden bg-white/5">
          <p className="text-xs text-gray-400 uppercase tracking-wide px-3 pt-3">Storm Track</p>
          <div className="relative w-full aspect-[4/3]">
            <Image
              src={chartUrl}
              alt="Storm track chart"
              fill
              className="object-contain"
              sizes="(max-width: 512px) 100vw, 512px"
            />
          </div>
        </div>
      )}

      {/* Affected areas */}
      <AffectedAreas areas={bulletin.affected_areas} />
    </div>
  );
}
