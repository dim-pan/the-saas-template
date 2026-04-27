import type React from 'react';
import { cn } from '@/utils/cn';

export type ButtonVariant =
  | 'default'
  | 'secondary'
  | 'outline'
  | 'ghost'
  | 'destructive'
  | 'link';

export type ButtonSize = 'sm' | 'md' | 'lg' | 'icon';

export type ButtonType = 'button' | 'submit' | 'reset';

export interface ButtonProps {
  children: React.ReactNode;
  className?: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  type?: ButtonType;
  isDisabled?: boolean;
  ariaLabel?: string;
  onClick?: () => void;
}

const BUTTON_BASE_CLASSNAME =
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background disabled:pointer-events-none disabled:opacity-50';

const BUTTON_VARIANT_CLASSNAME: Record<ButtonVariant, string> = {
  default: 'bg-primary text-primary-foreground hover:bg-primary/90',
  secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
  outline: 'border border-border bg-background hover:bg-muted',
  ghost: 'hover:bg-muted',
  destructive: 'bg-danger text-danger-foreground hover:bg-danger/90',
  link: 'text-primary underline-offset-4 hover:underline',
};

const BUTTON_SIZE_CLASSNAME: Record<ButtonSize, string> = {
  sm: 'h-9 px-3',
  md: 'h-10 px-4 py-2',
  lg: 'h-11 px-8',
  icon: 'h-10 w-10',
};

export function Button(props: ButtonProps) {
  const variant = props.variant ?? 'default';
  const size = props.size ?? 'md';

  return (
    <button
      type={props.type ?? 'button'}
      disabled={props.isDisabled}
      aria-label={props.ariaLabel}
      onClick={props.onClick}
      className={cn(
        BUTTON_BASE_CLASSNAME,
        BUTTON_VARIANT_CLASSNAME[variant],
        BUTTON_SIZE_CLASSNAME[size],
        props.className,
      )}
    >
      {props.children}
    </button>
  );
}
