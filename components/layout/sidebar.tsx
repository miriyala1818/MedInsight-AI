'use client';

import { Brain, ChartColumn, Microscope, Search, MessageSquare, Clock, X, Plus, Trash2, Loader2, Sparkles } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { Separator } from '@/components/ui/separator';
import { listConversations, deleteConversation } from '@/lib/api';
import type { ConversationSummary } from '@/lib/types';
import { cn } from '@/lib/utils';

const navItems = [
  { href: '/chat', label: 'Chat', icon: Brain },
  { href: '/sources', label: 'Sources', icon: Search }
];

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

interface SidebarProps {
  onClose?: () => void;
}

export function Sidebar({ onClose }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [recentChats, setRecentChats] = useState<ConversationSummary[]>([]);
  const [loading, setLoading] = useState(true);

  const loadChats = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listConversations();
      setRecentChats(data.conversations);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadChats();
  }, [loadChats]);

  // Listen for custom event to refresh conversations list
  useEffect(() => {
    const handler = () => loadChats();
    window.addEventListener('conversations-updated', handler);
    return () => window.removeEventListener('conversations-updated', handler);
  }, [loadChats]);

  function handleNewChat() {
    router.push('/chat');
    onClose?.();
    // Dispatch event so ChatWorkspace knows to reset
    window.dispatchEvent(new CustomEvent('new-chat'));
  }

  async function handleDeleteChat(e: React.MouseEvent, id: string) {
    e.preventDefault();
    e.stopPropagation();

    // Optimistic: remove from UI immediately
    const previousChats = recentChats;
    setRecentChats(prev => prev.filter(c => c.id !== id));

    // If we're currently viewing this chat, navigate to fresh chat
    const params = new URLSearchParams(window.location.search);
    if (params.get('id') === id) {
      router.push('/chat');
      window.dispatchEvent(new CustomEvent('new-chat'));
    }

    try {
      await deleteConversation(id);
    } catch {
      // Restore on failure
      setRecentChats(previousChats);
    }
  }

  return (
    <aside className="flex h-screen flex-col sidebar-blur border-r border-border/50">
      {/* Header */}
      <div className="flex items-center justify-between p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary/80 shadow-lg shadow-primary/20">
            <Microscope className="h-5 w-5 text-primary-foreground" strokeWidth={2.5} />
          </div>
          <div>
            <p className="text-base font-bold tracking-tight gradient-text">MedInsight AI</p>
            <p className="text-[11px] text-muted-foreground font-medium">Medical AI Assistant</p>
          </div>
        </div>
        {onClose && (
          <button 
            onClick={onClose}
            className="lg:hidden rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      <Separator className="mx-6" />

      {/* Navigation */}
      <nav className="space-y-1 px-4 pt-6">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          
          const handleNavigation = () => {
            router.push(href as any);
            if (onClose) {
              onClose();
            }
          };
          
          return (
            <button
              key={href}
              onClick={handleNavigation}
              className={cn(
                'group flex items-center gap-3 rounded-xl px-4 py-3 text-[15px] font-medium transition-all duration-200 w-full text-left',
                active
                  ? 'bg-primary/15 text-primary shadow-sm border border-primary/20'
                  : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
              )}
            >
              <Icon className={cn("h-5 w-5 transition-transform duration-200", active ? "scale-110" : "group-hover:scale-105")} />
              <span>{label}</span>
            </button>
          );
        })}
      </nav>

      {/* New Chat Button */}
      <div className="px-4 pt-6">
        <button
          onClick={handleNewChat}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-primary to-primary/80 px-4 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-all hover:shadow-primary/30 hover:scale-[1.02] active:scale-[0.98]"
        >
          <Plus className="h-4 w-4" strokeWidth={2.5} />
          New Chat
        </button>
      </div>

      {/* Recent Chats section */}
      <Separator className="mx-6 mt-6" />
      <div className="flex-1 overflow-hidden px-4 pt-6">
        <div className="flex items-center gap-2 px-2 mb-3">
          <Clock className="h-4 w-4 text-muted-foreground" />
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Recent Chats</p>
        </div>
        <div className="space-y-1 overflow-y-auto pr-1" style={{ maxHeight: 'calc(100vh - 440px)' }}>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
            </div>
          ) : recentChats.length === 0 ? (
            <div className="py-8 text-center">
              <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-muted/30">
                <MessageSquare className="h-6 w-6 text-muted-foreground/40" />
              </div>
              <p className="text-xs text-muted-foreground/60">No recent chats</p>
            </div>
          ) : (
            recentChats.map(chat => {
              const params = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '');
              const isActive = params.get('id') === chat.id;
              return (
                <Link
                  key={chat.id}
                  href={`/chat?id=${chat.id}`}
                  onClick={onClose}
                  className={cn(
                    'group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all duration-200',
                    isActive
                      ? 'bg-primary/10 border border-primary/20 text-foreground shadow-sm'
                      : 'hover:bg-muted/50 text-muted-foreground hover:text-foreground'
                  )}
                >
                  <div className={cn(
                    "rounded-lg p-1.5 transition-colors",
                    isActive ? "bg-primary/20" : "bg-muted/50 group-hover:bg-muted"
                  )}>
                    <MessageSquare className={cn('h-3.5 w-3.5', isActive ? 'text-primary' : 'text-muted-foreground')} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className={cn(
                      'truncate text-sm font-medium transition-colors',
                      isActive ? 'text-primary' : 'text-foreground group-hover:text-primary'
                    )}>
                      {chat.title || 'New Conversation'}
                    </p>
                    <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                      <span>{relativeTime(chat.updated_at)}</span>
                      {chat.message_count > 0 && (
                        <>
                          <span>·</span>
                          <span className="flex items-center gap-0.5">
                            <Sparkles className="h-3 w-3" />
                            {chat.message_count}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDeleteChat(e, chat.id)}
                    className="rounded-lg p-1.5 text-muted-foreground/0 transition-all hover:bg-red-500/10 hover:text-red-500 group-hover:text-muted-foreground/60"
                    title="Delete conversation"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </Link>
              );
            })
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-border/50 p-4">
        <div className="rounded-xl bg-muted/30 p-3 text-xs text-muted-foreground">
          <p className="font-medium mb-1">Evidence-Based Answers</p>
          <p className="text-[11px] leading-relaxed">
            All responses are grounded in peer-reviewed medical literature from trusted sources.
          </p>
        </div>
      </div>
    </aside>
  );
}
