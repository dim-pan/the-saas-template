import type React from 'react';
import { cn } from '@/utils/cn';

export interface LabelProps {
  htmlFor?: string;
  children: React.ReactNode;
  className?: string;
}

export function Label(props: LabelProps) {
  return (
    <label
      htmlFor={props.htmlFor}
      className={cn(
        'text-sm font-medium leading-none text-foreground peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
        props.className,
      )}
    >
      {props.children}
    </label>
  );
}
