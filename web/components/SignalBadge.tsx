const SIGNAL_COLORS: Record<number, string> = {
  1: '#3498db',
  2: '#f1c40f',
  3: '#e67e22',
  4: '#c0392b',
  5: '#c0392b',
};

interface Props {
  signal: number | null;
}

export default function SignalBadge({ signal }: Props) {
  const bg = signal != null ? (SIGNAL_COLORS[signal] ?? '#6b7280') : '#6b7280';
  return (
    <div
      style={{ backgroundColor: bg }}
      className="w-14 h-14 rounded-lg flex flex-col items-center justify-center flex-shrink-0"
    >
      <span className="text-xs text-white/60 uppercase leading-none">SIG</span>
      <span className="text-3xl font-extrabold text-white leading-none">
        {signal ?? '—'}
      </span>
    </div>
  );
}
