import * as React from 'react';

import { cn } from '@/lib/utils';

export function Tabs({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('flex gap-2', className)} {...props} />;
}

export function TabButton({ active, className, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { active?: boolean }) {
  return (
    <button
      className={cn(
        'rounded-full px-3 py-1.5 text-sm transition-colors',
        active ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:text-foreground',
        className
      )}
      {...props}
    />
  );
}
