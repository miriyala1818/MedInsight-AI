import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export function ConfidenceBadge({ score, className }: { score: number; className?: string }) {
  const variant = score >= 85 ? 'success' : score >= 60 ? 'warning' : 'outline';
  const label = score >= 85 ? 'High Confidence' : score >= 60 ? 'Medium' : 'Low';
  return (
    <Badge variant={variant as 'success' | 'warning' | 'outline'} className={cn('gap-2 px-3 py-1 text-xs font-semibold', className)}>
      <div className={cn(
        "h-2 w-2 rounded-full",
        score >= 85 ? "bg-success animate-pulse" : score >= 60 ? "bg-warning" : "bg-muted-foreground"
      )} />
      <span>{label}</span>
      <span className="opacity-75 font-mono">{score}%</span>
    </Badge>
  );
}
