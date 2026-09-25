"use client";

import { useEffect, useState } from 'react';
import { BarChart3 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ConfidenceBadge } from '@/components/common/confidence-badge';
import { EmptyState } from '@/components/common/empty-state';
import { LoadingState } from '@/components/common/loading-state';
import { getEvaluationDashboard } from '@/lib/api';
import type { EvaluationDashboard } from '@/lib/types';

function formatPercent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

export function EvaluationDashboardView() {
  const [dashboard, setDashboard] = useState<EvaluationDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getEvaluationDashboard()
      .then(setDashboard)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <LoadingState label="Loading evaluation metrics..." />;
  }

  if (error) {
    return (
      <EmptyState
        icon={BarChart3}
        title="Unable to load dashboard"
        description={error}
      />
    );
  }

  if (!dashboard || dashboard.total_runs === 0) {
    return (
      <EmptyState
        icon={BarChart3}
        title="No evaluation data yet"
        description="Metrics will appear here after queries are evaluated. Send some messages through the chat to begin collecting performance data."
      />
    );
  }

  const executiveMetrics = [
    { label: 'Hallucination rate', value: formatPercent(dashboard.hallucination_rate) },
    { label: 'Citation accuracy', value: formatPercent(dashboard.citation_accuracy) },
    { label: 'Retrieval precision', value: formatPercent(dashboard.retrieval_precision) },
    { label: 'Source coverage', value: formatPercent(dashboard.source_coverage) }
  ];

  return (
    <div className="space-y-6">
      <Card className="overflow-hidden border-border/80">
        <CardHeader>
          <div>
            <CardTitle>Evaluation Dashboard</CardTitle>
            <p className="text-sm text-muted-foreground">
              Live metrics from evaluated sessions.
            </p>
          </div>
          <Badge variant="outline">{dashboard.total_runs} runs</Badge>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {executiveMetrics.map((metric) => (
            <div key={metric.label} className="rounded-2xl border border-border bg-muted/20 p-4">
              <p className="text-sm text-muted-foreground">{metric.label}</p>
              <p className="mt-2 text-3xl font-semibold tracking-tight">{metric.value}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="border-border/80">
          <CardHeader>
            <CardTitle>Confidence distribution</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-3">
            {dashboard.confidence_distribution.map((bucket) => (
              <div key={bucket.label} className="rounded-2xl border border-border bg-surface/30 p-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold">{bucket.label}</p>
                  <ConfidenceBadge score={bucket.max_score} />
                </div>
                <p className="mt-3 text-3xl font-semibold tracking-tight">{bucket.count}</p>
                <p className="mt-1 text-xs text-muted-foreground">Sessions</p>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-border/80">
          <CardHeader>
            <CardTitle>Source coverage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {dashboard.source_coverage_breakdown.length === 0 ? (
              <p className="text-sm text-muted-foreground">No source breakdown available yet.</p>
            ) : (
              dashboard.source_coverage_breakdown.map((source) => (
                <div key={source.source_name} className="rounded-2xl border border-border bg-surface/30 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold">{source.source_name}</p>
                      <p className="text-xs text-muted-foreground">{source.evidence_count} references</p>
                    </div>
                    <Badge variant="outline">{formatPercent(source.coverage_rate)} covered</Badge>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
