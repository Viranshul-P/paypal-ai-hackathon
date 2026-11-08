import clsx from 'clsx';
import { useId } from 'react';

interface SwitchRowProps {
  label: string;
  hint: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

// Adapted from Watermelon UI's Switch 19: a labelled row whose hint follows the state.
export function SwitchRow({ label, hint, checked, onChange }: SwitchRowProps) {
  const id = useId();
  return (
    <div className="flex items-center justify-between gap-4 py-2.5">
      <label htmlFor={id} className="cursor-pointer">
        <span className="block font-semibold">{label}</span>
        <span className="block text-sm text-ink-2">{hint}</span>
      </label>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={clsx(
          'relative h-8 w-14 shrink-0 rounded-full transition-colors duration-150',
          checked ? 'bg-action' : 'bg-ink-2/40',
        )}
      >
        <span
          className={clsx(
            'absolute top-1 left-1 size-6 rounded-full bg-white transition-transform duration-150',
            checked && 'translate-x-6',
          )}
        />
      </button>
    </div>
  );
}
