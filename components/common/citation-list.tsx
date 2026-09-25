import Link from 'next/link';
import { ChevronDown, ExternalLink } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Citation } from '@/lib/types';

export function CitationList({ citations }: { citations: Citation[] }) {
  return (
    <div className="space-y-3">
      {citations.map((citation) => (
        <Card key={citation.id} className="overflow-hidden border-border/80">
          <CardContent className="p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{citation.source}</Badge>
                  <span className="text-xs text-muted-foreground">{citation.section}</span>
                </div>
                <h4 className="text-sm font-semibold leading-snug">{citation.title}</h4>
                <p className="max-w-3xl text-sm text-muted-foreground">{citation.snippet}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Button variant="outline" size="sm">
                  Open <ExternalLink className="h-3.5 w-3.5" />
                </Button>
                <Button variant="ghost" size="sm" aria-label="Expand citation">
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
