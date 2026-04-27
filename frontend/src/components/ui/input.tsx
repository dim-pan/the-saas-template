import { cn } from '@/utils/cn';

export type InputType =
  | 'text'
  | 'email'
  | 'password'
  | 'search'
  | 'tel'
  | 'url';

export interface InputProps {
  id?: string;
  name?: string;
  type?: InputType;
  value: string;
  placeholder?: string;
  className?: string;
  isRequired?: boolean;
  isDisabled?: boolean;
  autoComplete?: string;
  onChange?: (value: string) => void;
  onBlur?: (value: string) => void;
}

export function Input(props: InputProps) {
  return (
    <input
      id={props.id}
      name={props.name}
      type={props.type ?? 'text'}
      value={props.value}
      placeholder={props.placeholder}
      required={props.isRequired}
      disabled={props.isDisabled}
      autoComplete={props.autoComplete}
      onChange={(event) => {
        if (props.onChange) {
          props.onChange(event.target.value);
        }
      }}
      onBlur={(event) => {
        if (props.onBlur) {
          props.onBlur(event.target.value);
        }
      }}
      className={cn(
        'flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background disabled:cursor-not-allowed disabled:opacity-50',
        props.className,
      )}
    />
  );
}
