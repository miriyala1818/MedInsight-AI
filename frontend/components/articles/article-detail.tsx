import Link from 'next/link';
import { ArrowLeft, BookOpen } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/common/empty-state';

export function ArticleDetail({ pmid }: { pmid: string }) {
  return (
    <div className="space-y-6">
      <Link
        href="/sources"
        className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-muted-foreground transition hover:bg-muted/50 hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to sources
      </Link>

      <Card className="overflow-hidden border-border/80">
        <CardHeader>
          <CardTitle className="text-xl">Article {pmid}</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={BookOpen}
            title="Article not loaded"
            description="Article details will be fetched dynamically once the retrieval service is connected. No static preview data is shown."
          />
        </CardContent>
      </Card>
    </div>
  );
}
