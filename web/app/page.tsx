import { getActiveStorms, getPastStorms } from '@/lib/supabase/queries';
import StormCard from '@/components/StormCard';
import PageLabel from '@/components/PageLabel';

export const revalidate = 900; // 15 minutes

export default async function HomePage() {
  const [active, past] = await Promise.all([getActiveStorms(), getPastStorms()]);

  return (
    <div className="space-y-8">
      {/* Active storms */}
      <section>
        <h1 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
          <PageLabel k="active_typhoons" />
        </h1>
        {active.length === 0 ? (
          <div className="rounded-2xl bg-white/5 px-5 py-6 text-center">
            <div className="text-3xl mb-2">✅</div>
            <p className="font-semibold text-white"><PageLabel k="no_active_typhoons" /></p>
            <p className="text-sm text-gray-400 mt-1"><PageLabel k="stay_prepared" /></p>
          </div>
        ) : (
          <div className="space-y-3">
            {active.map(storm => (
              <StormCard key={storm.id} storm={storm} />
            ))}
          </div>
        )}
      </section>

      {/* Past storms */}
      {past.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
            <PageLabel k="past_storms" />
          </h2>
          <div className="space-y-2">
            {past.map(storm => (
              <StormCard key={storm.id} storm={storm} compact />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
