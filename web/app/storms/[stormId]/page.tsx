import { notFound } from 'next/navigation';
import Link from 'next/link';
import { getStormDetail } from '@/lib/supabase/queries';
import { audioUrl } from '@/lib/audio-url';
import { formatDate } from '@/lib/format-date';
import BulletinAudioSection from '@/components/BulletinAudioSection';
import BulletinHistoryAccordion from '@/components/BulletinHistoryAccordion';
import LatestBulletinSection from '@/components/LatestBulletinSection';
import AffectedAreas from '@/components/AffectedAreas';
import DistancePill from '@/components/DistancePill';
import PageLabel from '@/components/PageLabel';

export const revalidate = 600; // 10 minutes

const SIGNAL_BG: Record<number, string> = {
  1: 'from-blue-900 to-blue-800',
  2: 'from-yellow-900 to-yellow-800',
  3: 'from-orange-900 to-orange-800',
  4: 'from-red-900 to-red-800',
  5: 'from-red-950 to-red-900',
};

function heroBg(signal: number | null): string {
  return signal != null ? (SIGNAL_BG[signal] ?? 'from-gray-900 to-gray-800') : 'from-gray-900 to-gray-800';
}

interface Props {
  params: { stormId: string };
}

export default async function StormDetailPage({ params }: Props) {
  const detail = await getStormDetail(params.stormId);
  if (!detail) notFound();

  const { storm, latestBulletin, latestMedia, bulletinHistory } = detail;
  const chartUrl = latestBulletin.chart_path ? audioUrl(latestBulletin.chart_path) : null;

  return (
    <div className="space-y-6">
      {/* Back */}
      <Link href="/" className="text-sm text-gray-400 hover:text-white transition-colors">
        <PageLabel k="all_storms" />
      </Link>

      {/* Hero banner */}
      <div className={`rounded-2xl bg-gradient-to-br ${heroBg(storm.current_signal)} p-5 space-y-2`}>
        <div className="text-xs text-white/60 uppercase tracking-wide">
          {storm.current_category ?? 'Tropical Cyclone'}
        </div>
        <h1 className="text-4xl font-extrabold text-white">{storm.storm_name}</h1>
        {storm.current_reference && (
          <p className="text-sm text-white/70">{storm.current_reference}</p>
        )}
        {storm.current_lat != null && storm.current_lon != null && (
          <DistancePill stormLat={storm.current_lat} stormLon={storm.current_lon} />
        )}
        <div className="text-xs text-white/40">
          Bulletin #{latestBulletin.bulletin_number} · {formatDate(latestBulletin.issued_at)}
        </div>
      </div>

      {/* Audio player */}
      <BulletinAudioSection media={latestMedia} stem={latestBulletin.stem} />

      {/* Storm track chart / Latest bulletin PDF */}
      <LatestBulletinSection
        chartUrl={chartUrl}
        stormName={storm.storm_name}
      />

      {/* Affected areas */}
      <AffectedAreas areas={latestBulletin.affected_areas} />

      {/* Bulletin history */}
      {bulletinHistory.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
            <PageLabel k="past_bulletins" />
          </h2>
          <BulletinHistoryAccordion 
            bulletins={bulletinHistory} 
            stormName={storm.storm_name}
          />
        </section>
      )}

      {/* Mode 2 stub */}
      <div className="rounded-2xl border border-white/5 bg-white/3 p-5 opacity-40">
        <div className="text-sm font-semibold text-white">🎙 <PageLabel k="storm_summary_audio" /></div>
        <div className="text-xs text-gray-400 mt-1"><PageLabel k="coming_soon" /></div>
      </div>
    </div>
  );
}
