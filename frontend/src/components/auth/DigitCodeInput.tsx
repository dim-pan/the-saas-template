import { useRef, useState } from 'react';
import { cn } from '@/utils/cn';

function normalizeDigits(value: string, numberOfDigits: number) {
  return value.replaceAll(/\D/g, '').slice(0, numberOfDigits);
}

interface DigitCodeInputProps {
  id?: string;
  numberOfDigits: number;
  value: string;
  isDisabled?: boolean;
  onChange: (value: string) => void;
}

export function DigitCodeInput(props: DigitCodeInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isFocused, setIsFocused] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);

  const normalized = normalizeDigits(props.value, props.numberOfDigits);
  const digits = normalized
    .padEnd(props.numberOfDigits, ' ')
    .split('')
    .slice(0, props.numberOfDigits);

  const syncActiveIndex = () => {
    const el = inputRef.current;
    if (!el) return;
    const pos = Math.min(el.selectionStart ?? 0, props.numberOfDigits - 1);
    setActiveIndex(pos);
  };

  return (
    <div
      className={cn(
        'relative flex items-center gap-2',
        !props.isDisabled && 'cursor-text',
      )}
      id={props.id}
      onClick={() => inputRef.current?.focus()}
    >
      {digits.map((digit, i) => (
        <div
          key={i}
          className={cn(
            'flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-border bg-background text-sm text-foreground',
            isFocused &&
              i === activeIndex &&
              'ring-2 ring-ring ring-offset-2 ring-offset-background',
          )}
        >
          {digit === ' ' ? '' : digit}
        </div>
      ))}
      <input
        ref={inputRef}
        type="text"
        inputMode="numeric"
        autoComplete="one-time-code"
        pattern="[0-9]*"
        maxLength={props.numberOfDigits}
        value={normalized}
        disabled={props.isDisabled}
        aria-label="One-time code"
        className="absolute inset-0 cursor-text opacity-0 disabled:cursor-not-allowed"
        onFocus={() => {
          setIsFocused(true);
          syncActiveIndex();
        }}
        onBlur={() => setIsFocused(false)}
        onClick={() => requestAnimationFrame(syncActiveIndex)}
        onSelect={() => requestAnimationFrame(syncActiveIndex)}
        onKeyUp={() => requestAnimationFrame(syncActiveIndex)}
        onChange={(e) => {
          props.onChange(normalizeDigits(e.target.value, props.numberOfDigits));
          requestAnimationFrame(syncActiveIndex);
        }}
        onPaste={(e) => {
          const text = e.clipboardData.getData('text');
          const next = normalizeDigits(text, props.numberOfDigits);
          if (next.length > 0) {
            e.preventDefault();
            props.onChange(next);
            requestAnimationFrame(syncActiveIndex);
          }
        }}
      />
    </div>
  );
}
