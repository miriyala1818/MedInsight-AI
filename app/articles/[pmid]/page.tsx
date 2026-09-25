import { ArticleDetail } from '@/components/articles/article-detail';

type ArticlePageProps = {
  params: Promise<{ pmid: string }>;
};

export default async function ArticlePage({ params }: ArticlePageProps) {
  const { pmid } = await params;
  return <ArticleDetail pmid={pmid} />;
}
