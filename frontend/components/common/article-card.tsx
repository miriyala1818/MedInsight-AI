import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ConfidenceBadge } from '@/components/common/confidence-badge';
import { ArticlePreview } from '@/lib/types';

export function ArticleCard({ article }: { article: ArticlePreview }) {
  return (
    <Card className="group overflow-hidden border-border/80 transition hover:-translate-y-0.5 hover:shadow-soft">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">{article.journal}</Badge>
              <ConfidenceBadge score={article.confidence} />
            </div>
            <h3 className="text-base font-semibold leading-snug group-hover:text-primary">{article.title}</h3>
            <p className="text-sm text-muted-foreground">{article.authors.join(', ')}</p>
            <p className="max-w-2xl text-sm text-muted-foreground">{article.abstract}</p>
          </div>
          <div className="text-right text-xs text-muted-foreground">
            <p>{article.publicationDate}</p>
            <p>{article.pmid}</p>
          </div>
        </div>
        <div className="mt-4 flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Medical article preview</span>
          <Button variant="outline" size="sm">Open article</Button>
        </div>
      </CardContent>
    </Card>
  );
}
