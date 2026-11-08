import { Link } from 'react-router-dom';

export function PauseMark({ className = 'h-5' }: { className?: string }) {
  return (
    <svg viewBox="0 0 22 24" className={className} aria-hidden fill="currentColor">
      <rect x="2" width="7" height="24" rx="3.5" />
      <rect x="13" width="7" height="24" rx="3.5" />
    </svg>
  );
}

export function Brand() {
  return (
    <Link to="/" className="flex items-center gap-2 text-xl font-extrabold text-ink no-underline">
      <PauseMark className="h-[1.05rem] text-action" />
      Pauseline
    </Link>
  );
}
