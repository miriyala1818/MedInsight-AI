"use client";

import { useEffect, useState } from 'react';
import { Database, ShieldCheck } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/common/empty-state';
import { LoadingState } from '@/components/common/loading-state';
import { getAppConfig } from '@/lib/api';

export function SourceViewer() {
  const [sources, setSources] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAppConfig()
      .then((config) => setSources(config.trusted_sources))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <LoadingState label="Loading trusted sources..." />;
  }

  if (error) {
    return <EmptyState icon={Database} title="Unable to load sources" description={error} />;
  }

  return (
    <div className="space-y-6">
      <Card className="border-border/80">
        <CardHeader>
          <div>
            <CardTitle>Trusted Sources</CardTitle>
            <CardDescription>Verified evidence sources used by the AI assistant.</CardDescription>
          </div>
          <Badge variant="outline">{sources.length} configured</Badge>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {sources.map((source) => (
            <div key={source} className="rounded-2xl border border-border bg-surface/30 p-4 flex flex-col h-full">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-semibold">{source}</p>
                <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary border border-primary/20">
                  <ShieldCheck className="h-3 w-3" />
                  Verified
                </span>
              </div>
              <p className="mt-1 text-xs text-muted-foreground leading-relaxed flex-1">
                Peer-reviewed and trusted data source used to answer your questions.
              </p>
            </div>
          ))}
        </CardContent>
      </Card>

      <EmptyState
        icon={Database}
        title="No indexed articles yet"
        description="Article previews will appear once the assistant retrieves results for your queries."
      />
    </div>
  );
}
