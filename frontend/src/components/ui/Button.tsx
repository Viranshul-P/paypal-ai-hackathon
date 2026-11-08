import clsx from 'clsx';
import type { ButtonHTMLAttributes } from 'react';

type Variant = 'primary' | 'secondary';

export function buttonClass(variant: Variant = 'primary', className?: string) {
  return clsx(
    'inline-flex min-h-16 w-full items-center justify-center gap-2 rounded-full px-6 text-[1.15rem] font-extrabold no-underline transition-[background-color,transform] duration-150 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100',
    variant === 'primary' && 'bg-action text-white hover:bg-action-press',
    variant === 'secondary' && 'bg-card text-ink-2 hover:bg-tint',
    className,
  );
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

export function Button({ variant = 'primary', className, type = 'button', ...props }: ButtonProps) {
  return <button type={type} className={buttonClass(variant, className)} {...props} />;
}
