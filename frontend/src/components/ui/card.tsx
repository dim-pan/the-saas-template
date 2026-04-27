import { cn } from '@/utils/cn';
import type React from 'react';

export interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export function Card(props: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border bg-surface text-foreground shadow-sm',
        props.className,
      )}
    >
      {props.children}
    </div>
  );
}

export interface CardHeaderProps {
  children: React.ReactNode;
  className?: string;
}

export function CardHeader(props: CardHeaderProps) {
  return (
    <div className={cn('flex flex-col space-y-1.5 p-6', props.className)}>
      {props.children}
    </div>
  );
}

export interface CardTitleProps {
  children: React.ReactNode;
  className?: string;
}

export function CardTitle(props: CardTitleProps) {
  return (
    <h3 className={cn('text-lg font-semibold leading-none', props.className)}>
      {props.children}
    </h3>
  );
}

export interface CardDescriptionProps {
  children: React.ReactNode;
  className?: string;
}

export function CardDescription(props: CardDescriptionProps) {
  return (
    <p className={cn('text-sm text-muted-foreground', props.className)}>
      {props.children}
    </p>
  );
}

export interface CardContentProps {
  children: React.ReactNode;
  className?: string;
}

export function CardContent(props: CardContentProps) {
  return (
    <div className={cn('p-6 pt-0', props.className)}>{props.children}</div>
  );
}

export interface CardFooterProps {
  children: React.ReactNode;
  className?: string;
}

export function CardFooter(props: CardFooterProps) {
  return (
    <div className={cn('flex items-center p-6 pt-0', props.className)}>
      {props.children}
    </div>
  );
}
