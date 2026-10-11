'use client';

import { MessageSquare, Plus, Trash2, Loader2, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ConversationSummary } from '@/lib/types';

interface ConversationSidebarProps {
  conversations: ConversationSummary[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  loading?: boolean;
}

function relativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHrs = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHrs < 24) return `${diffHrs}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  loading = false,
}: ConversationSidebarProps) {
  return (
    <div className="flex h-full flex-col">
      {/* New Chat Button */}
      <button
        onClick={onNew}
        className="mb-4 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-primary to-primary/80 px-4 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:shadow-primary/30 hover:scale-[1.02] active:scale-[0.98]"
      >
        <Plus className="h-4 w-4" strokeWidth={2.5} />
        New Chat
      </button>

      {/* Conversation List */}
      <div className="flex-1 space-y-2 overflow-y-auto pr-1" style={{ maxHeight: 'calc(100vh - 200px)' }}>
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
          </div>
        ) : conversations.length === 0 ? (
          <div className="py-12 text-center">
            <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-2xl bg-muted/30">
              <MessageSquare className="h-8 w-8 text-muted-foreground/40" />
            </div>
            <p className="text-sm font-medium text-muted-foreground">No conversations yet</p>
            <p className="mt-1 text-xs text-muted-foreground/60">Start a new chat to begin</p>
          </div>
        ) : (
          conversations.map(conv => {
            const isActive = conv.id === activeId;
            return (
              <div
                key={conv.id}
                className={cn(
                  'group relative flex cursor-pointer items-start gap-3 rounded-xl border p-3 text-sm transition-all duration-200',
                  isActive
                    ? 'glassmorphism-card border-primary/30 bg-primary/10 text-foreground shadow-sm'
                    : 'border-transparent hover:glassmorphism-card hover:border-border/50 text-muted-foreground hover:text-foreground'
                )}
                onClick={() => onSelect(conv.id)}
              >
                <div className={cn(
                  "mt-0.5 rounded-lg p-1.5 transition-colors",
                  isActive ? "bg-primary/20" : "bg-muted/50 group-hover:bg-muted"
                )}>
                  <MessageSquare className={cn('h-4 w-4', isActive ? 'text-primary' : 'text-muted-foreground')} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[14px] font-semibold leading-tight">
                    {conv.title || 'New Conversation'}
                  </p>
                  <div className="mt-1 flex items-center gap-2 text-[11px] text-muted-foreground">
                    <span>{relativeTime(conv.updated_at)}</span>
                    {conv.message_count > 0 && (
                      <>
                        <span>·</span>
                        <span className="flex items-center gap-1">
                          <Sparkles className="h-3 w-3" />
                          {conv.message_count}
                        </span>
                      </>
                    )}
                  </div>
                </div>
                <button
                  onClick={e => {
                    e.stopPropagation();
                    onDelete(conv.id);
                  }}
                  className="absolute right-2 top-2.5 rounded-lg p-1.5 text-muted-foreground/0 transition-all hover:bg-danger/10 hover:text-danger group-hover:text-muted-foreground/60"
                  title="Delete conversation"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
