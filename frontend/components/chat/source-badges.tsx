'use client';

import { ShieldCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SourceBadgesProps {
  sources: string[];
  className?: string;
}

export function SourceBadges({ sources, className }: SourceBadgesProps) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className={cn('animate-in fade-in slide-in-from-bottom-2 duration-500', className)}>
      <div className="flex items-center gap-2">
        <ShieldCheck className="h-3.5 w-3.5 text-primary" />
        <span className="text-xs font-medium text-primary">
          Verified by {sources.length} trusted source{sources.length > 1 ? 's' : ''}
        </span>
      </div>
    </div>
  );
}
