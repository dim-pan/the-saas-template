import { createPortal } from 'react-dom';
import { cn } from '@/utils/cn';
import { useEffect, useRef } from 'react';

export type BackdropDarkness = 'none' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
export type BackdropBlur = 'none' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
  className?: string;
  contentClassName?: string;
  backdropDarkness?: BackdropDarkness;
  backdropBlur?: BackdropBlur;
  fullscreen?: boolean;
  closeOnEsc?: boolean;
  closeOnBackdrop?: boolean;
}

const backdropDarknessMap: Record<BackdropDarkness, string> = {
  none: '',
  sm: 'bg-foreground/10',
  md: 'bg-foreground/20',
  lg: 'bg-foreground/35',
  xl: 'bg-foreground/50',
  '2xl': 'bg-foreground/70',
};

const backdropBlurMap: Record<BackdropBlur, string> = {
  none: '',
  sm: 'backdrop-blur-sm',
  md: 'backdrop-blur-md',
  lg: 'backdrop-blur-lg',
  xl: 'backdrop-blur-xl',
  '2xl': 'backdrop-blur-2xl',
};

export function Modal(props: ModalProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!props.isOpen) {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [props.isOpen]);

  // Only focus container on initial open, not on every render
  useEffect(() => {
    if (props.isOpen && containerRef.current) {
      const hasFocusInside = containerRef.current.querySelector(':focus');
      if (!hasFocusInside) {
        containerRef.current.focus();
      }
    }
  }, [props.isOpen]);

  if (!props.isOpen) {
    return null;
  }

  const modalContent = (
    <div
      ref={containerRef}
      onClick={() => {
        if (props.closeOnBackdrop !== false) {
          props.onClose();
        }
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape') {
          event.stopPropagation();
          if (props.closeOnEsc !== false) {
            event.preventDefault();
            props.onClose();
          }
        }
      }}
      tabIndex={-1}
      role="dialog"
      aria-modal="true"
      className={cn(
        'pointer-events-auto fixed inset-0 z-[9999] flex items-center justify-center overflow-hidden',
        props.fullscreen
          ? 'p-0'
          : 'px-2 sm:p-2 md:px-10 md:py-20 lg:px-40 lg:py-20 xl:px-80 xl:py-20 2xl:px-96 2xl:py-20',
        backdropDarknessMap[props.backdropDarkness ?? 'sm'],
        backdropBlurMap[props.backdropBlur ?? 'sm'],
        props.className,
      )}
    >
      <div
        className={cn(
          'max-h-full max-w-full',
          props.fullscreen
            ? 'h-full w-full'
            : 'w-full rounded-xl border border-border bg-surface text-foreground shadow-lg',
          props.contentClassName,
        )}
        onClick={(event) => event.stopPropagation()}
      >
        {props.children}
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
