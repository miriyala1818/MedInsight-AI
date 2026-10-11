import { cn } from '@/lib/utils';

type BadgeVariant = 'default' | 'success' | 'warning' | 'outline';

type BadgeProps = {
  className?: string;
  variant?: BadgeVariant;
  children?: any;
};

export function Badge({
  className,
  variant = 'default',
  children
}: BadgeProps) {
  const variants: Record<BadgeVariant, string> = {
    default: 'bg-primary/10 text-primary border border-primary/20',
    success: 'bg-success/15 text-success border border-success/20',
    warning: 'bg-warning/15 text-warning border border-warning/20',
    outline: 'bg-transparent text-muted-foreground border border-border'
  };

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium tracking-wide',
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
