import clsx from 'clsx';
import { OTPInput, type SlotProps } from 'input-otp';

// Adapted from Watermelon UI's Input OTP 5: spaced boxes where the active one grows.
function Slot({ char, isActive, hasFakeCaret }: SlotProps) {
  return (
    <div
      className={clsx(
        'flex size-16 items-center justify-center rounded-2xl border-2 bg-tint text-3xl font-extrabold transition-all duration-150',
        isActive ? 'scale-110 border-action' : 'border-line',
      )}
    >
      {char ? '•' : hasFakeCaret ? <span className="h-7 w-0.5 animate-pulse bg-action" /> : null}
    </div>
  );
}

interface PinInputProps {
  value: string;
  onChange: (value: string) => void;
  onComplete: (value: string) => void;
  disabled?: boolean;
}

export function PinInput({ value, onChange, onComplete, disabled }: PinInputProps) {
  return (
    <OTPInput
      maxLength={4}
      value={value}
      onChange={onChange}
      onComplete={onComplete}
      disabled={disabled}
      autoFocus
      inputMode="numeric"
      pattern="^[0-9]*$"
      aria-label="Family PIN"
      containerClassName="flex justify-center gap-3"
      render={({ slots }) => (
        <>
          {slots.map((slot, i) => (
            <Slot key={i} {...slot} />
          ))}
        </>
      )}
    />
  );
}
