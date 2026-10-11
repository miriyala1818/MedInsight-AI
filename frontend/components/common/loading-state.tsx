import { Loader2 } from 'lucide-react';

export function LoadingState({ label = 'Loading...' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-border/80 bg-muted/10 px-6 py-14 text-center">
      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      <p className="mt-3 text-sm text-muted-foreground">{label}</p>
    </div>
  );
}
