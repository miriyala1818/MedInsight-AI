"use client";

import { useEffect, useRef, useState } from 'react';
import { AlertCircle, BookOpen, Brain, CheckCircle2, FileSearch, GitMerge, MessageSquare, Send, ShieldCheck, Loader2 } from 'lucide-react';
import { useSearchParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { Button } from '@/components/ui/button';
import { ConfidenceBadge } from '@/components/common/confidence-badge';
import { EmptyState } from '@/components/common/empty-state';
import { getAppConfig, submitQuery, getConversation } from '@/lib/api';
import type { Message } from '@/lib/types';
import { cn } from '@/lib/utils';
import { SourceBadges } from '@/components/chat/source-badges';

// ── Agent pipeline step definitions ──────────────────────────────────────────
const PIPELINE_STEPS = [
  { id: 'planner',    label: 'Planning Query',          icon: Brain },
  { id: 'retrieval',  label: 'Searching Sources',     icon: FileSearch },
  { id: 'generation', label: 'Generating Answer', icon: BookOpen },
  { id: 'validation', label: 'Validating Sources',      icon: ShieldCheck },
  { id: 'citation',   label: 'Adding Citations',       icon: GitMerge },
  { id: 'response',   label: 'Finalizing Response',      icon: CheckCircle2 },
] as const;

type PipelineStep = typeof PIPELINE_STEPS[number]['id'];

function AgentProgress({
  step,
  showDetails,
  onToggle,
}: {
  step: PipelineStep | null;
  showDetails: boolean;
  onToggle: () => void;
}) {
  const currentIdx = PIPELINE_STEPS.findIndex((s) => s.id === step);

  return (
    <div className="flex justify-start animate-slide-in-up">
      <div className="glassmorphism-card rounded-2xl px-5 py-4 text-sm space-y-3 min-w-[300px]">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <p className="text-xs font-bold text-primary uppercase tracking-wider">Processing</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={onToggle}
            className="rounded-full text-xs px-3 py-1"
          >
            {showDetails ? 'Hide details' : 'Show details'}
          </Button>
        </div>

        {showDetails ? (
          <div className="space-y-2">
            {PIPELINE_STEPS.map((s, idx) => {
              const Icon = s.icon;
              const done = currentIdx > idx;
              const active = currentIdx === idx;
              return (
                <div
                  key={s.id}
                  className={cn(
                    'flex items-center gap-3 text-[13px] transition-all duration-300',
                    done && 'text-success',
                    active && 'text-primary font-semibold scale-105',
                    !done && !active && 'text-muted-foreground/40'
                  )}
                >
                  <Icon className={cn('h-4 w-4 shrink-0', active && 'animate-pulse')} />
                  <span className="flex-1">{s.label}</span>
                  {done && <CheckCircle2 className="h-3.5 w-3.5 text-success" />}
                  {active && (
                    <div className="flex gap-0.5">
                      <div className="h-1 w-1 rounded-full bg-primary animate-pulse" />
                      <div className="h-1 w-1 rounded-full bg-primary animate-pulse delay-75" />
                      <div className="h-1 w-1 rounded-full bg-primary animate-pulse delay-150" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : null}
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export function ChatWorkspace() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [pipelineStep, setPipelineStep] = useState<PipelineStep | null>(null);
  const [showPipelineDetails, setShowPipelineDetails] = useState(false);
  const [llmConfigured, setLlmConfigured] = useState<boolean | null>(null);
  const [sessionId] = useState(() => crypto.randomUUID());
  
  const [conversationId, setConversationId] = useState<string | null>(null);

  const searchParams = useSearchParams();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const pipelineTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastUrlIdRef = useRef<string | null>(null);

  // Load conversation from URL params — only react to actual URL changes
  useEffect(() => {
    const id = searchParams.get('id') ?? null;

    // Skip if the URL id hasn't actually changed
    if (id === lastUrlIdRef.current) return;
    lastUrlIdRef.current = id;

    if (id) {
      setConversationId(id);
      setMessages([]);
      setLoading(true);
      getConversation(id)
        .then(detail => {
          const loadedMessages: Message[] = detail.messages.map(m => ({
            id: m.id,
            role: m.role as 'user' | 'assistant',
            content: m.content,
            confidence: m.confidence_score ?? undefined,
            citations: m.citations ?? undefined,
            sources_used: m.sources_used ?? undefined,
          }));
          setMessages(loadedMessages);
        })
        .catch(() => {
          // handle error
        })
        .finally(() => {
          setLoading(false);
        });
    }
    // When URL has no id, don't reset — let the new-chat event handle resets.
    // The initial state (messages=[], conversationId=null) is already correct on mount.
  }, [searchParams]);

  // Listen for new-chat event from sidebar
  useEffect(() => {
    const handler = () => {
      setConversationId(null);
      setMessages([]);
      lastUrlIdRef.current = null;
    };
    window.addEventListener('new-chat', handler);
    return () => window.removeEventListener('new-chat', handler);
  }, []);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    const nextHeight = Math.min(textarea.scrollHeight, 200);
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > 200 ? 'auto' : 'hidden';
  }, [input]);

  // Scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Check LLM config on mount
  useEffect(() => {
    getAppConfig()
      .then((config) => setLlmConfigured(config.llm_configured))
      .catch(() => setLlmConfigured(false));
  }, []);

  // Simulate agent pipeline progress while waiting for the backend
  function startPipelineAnimation() {
    const steps = PIPELINE_STEPS.map(s => s.id) as PipelineStep[];
    let idx = 0;
    setPipelineStep(steps[0]);

    function advance() {
      idx += 1;
      if (idx < steps.length) {
        setPipelineStep(steps[idx]);
        pipelineTimerRef.current = setTimeout(advance, 1800);
      }
    }
    pipelineTimerRef.current = setTimeout(advance, 1800);
  }

  function stopPipelineAnimation() {
    if (pipelineTimerRef.current) {
      clearTimeout(pipelineTimerRef.current);
      pipelineTimerRef.current = null;
    }
    setPipelineStep(null);
  }

  function togglePipelineDetails() {
    setShowPipelineDetails((current) => !current);
  }

  const latestAssistant = [...messages].reverse().find((m) => m.role === 'assistant');

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
    };

    setMessages((curr) => [...curr, userMessage]);
    setInput('');
    setLoading(true);
    startPipelineAnimation();

    try {
      const response = await submitQuery(question, sessionId, conversationId ?? undefined);
      stopPipelineAnimation();

      if (response.conversation_id) {
        setConversationId(response.conversation_id);
      }
      // Notify sidebar to refresh conversation list
      window.dispatchEvent(new CustomEvent('conversations-updated'));

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.answer,
        confidence: response.confidence_score,
        sources_used: response.sources_used,
        citations: response.citations.map((c, i) => ({
          id: String(c.id ?? i),
          source: String(c.source ?? 'Source'),
          title: String(c.title ?? 'Reference'),
          url: String(c.url ?? '#'),
          snippet: String(c.snippet ?? ''),
          section: String(c.section ?? 'Evidence'),
        })),
      };
      setMessages((curr) => [...curr, assistantMessage]);
    } catch (error) {
      stopPipelineAnimation();
      const message = error instanceof Error ? error.message : 'Unable to reach the assistant.';
      setMessages((curr) => [
        ...curr,
        { id: crypto.randomUUID(), role: 'assistant', content: message, error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const form = e.currentTarget.closest('form');
      if (form) form.requestSubmit();
    }
  }

  return (
    <div className="flex h-[calc(100vh-73px)] flex-col">
      {/* Chat Header */}
      <div className="border-b border-border/50 bg-background/40 backdrop-blur-sm px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-foreground">Medical Assistant</h1>
            <p className="text-sm text-muted-foreground">
              Evidence-based answers with verified citations
            </p>
          </div>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl py-8">
          {/* LLM not configured warning */}
          {llmConfigured === false && (
            <div className="mb-6 animate-slide-in-up">
              <div className="glassmorphism-card flex items-start gap-4 rounded-2xl border-amber-500/30 p-5">
                <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" />
                <div>
                  <p className="font-semibold text-foreground mb-1">LLM not configured</p>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    Add your API key to <code className="text-xs bg-muted px-1.5 py-0.5 rounded">backend/.env</code> and restart the server.
                    See <code className="text-xs bg-muted px-1.5 py-0.5 rounded">.env.example</code> for setup instructions.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Message thread */}
          <div className="space-y-6">
            {messages.length === 0 ? (
              <EmptyState
                icon={MessageSquare}
                title="How can I help you today?"
                description="Ask any medical question — symptoms, medications, conditions, or treatments. I'll provide evidence-based answers with citations."
              />
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex animate-slide-in-up ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={cn(
                      'max-w-[85%] rounded-2xl px-5 py-4 shadow-lg transition-all duration-200 hover:shadow-xl',
                      message.role === 'user'
                        ? 'chat-bubble-user text-primary-foreground'
                        : message.error
                        ? 'glassmorphism-card border-danger/40 text-foreground'
                        : 'chat-bubble-assistant text-card-foreground'
                    )}
                  >
                    <div className="prose prose-sm dark:prose-invert max-w-none text-[15px] leading-7 prose-p:leading-7 prose-headings:font-bold prose-a:text-primary hover:prose-a:text-primary/80 prose-a:no-underline hover:prose-a:underline">
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        components={{
                          a: ({ node, ...props }) => (
                            <a {...props} target="_blank" rel="noopener noreferrer" />
                          )
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    </div>

                    {message.role === 'assistant' && !message.error && (
                      <>
                        {/* Citations */}
                        {message.citations?.length ? (
                          <div className="mt-5 pt-4 border-t border-border/30 space-y-3">
                            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                              <FileSearch className="h-3.5 w-3.5" />
                              Evidence &amp; Citations
                            </p>
                            <div className="grid gap-3">
                              {message.citations.map((citation, idx) => (
                                <div
                                  key={citation.id || idx}
                                  className="text-xs rounded-xl bg-background/40 backdrop-blur-sm p-3.5 border border-border/40 hover:border-primary/30 transition-all"
                                >
                                  <div className="flex items-center justify-between gap-2 mb-2">
                                    <span className="font-bold text-primary text-sm">
                                      {citation.source || 'Reference'}
                                    </span>
                                    {citation.section && (
                                      <span className="text-[10px] text-muted-foreground bg-muted/50 px-2 py-0.5 rounded-full">
                                        {citation.section}
                                      </span>
                                    )}
                                  </div>
                                  <h5 className="font-semibold text-foreground mb-2 leading-snug">
                                    {citation.url && citation.url !== '#' ? (
                                      <a
                                        href={citation.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="hover:text-primary transition-colors underline decoration-primary/30 hover:decoration-primary"
                                      >
                                        {citation.title || 'Source'}
                                      </a>
                                    ) : (
                                      citation.title || 'Source'
                                    )}
                                  </h5>
                                  {citation.snippet && (
                                    <p className="text-muted-foreground italic leading-relaxed border-l-2 border-primary/30 pl-3 py-1">
                                      &ldquo;{citation.snippet}&rdquo;
                                    </p>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : null}


                      </>
                    )}
                  </div>
                </div>
              ))
            )}

            {/* Loading: show agent pipeline progress */}
            {loading && (
        <AgentProgress
          step={pipelineStep}
          showDetails={showPipelineDetails}
          onToggle={togglePipelineDetails}
        />
      )}

            <div ref={bottomRef} />
          </div>
        </div>
      </div>

      {/* Input form */}
      <div className="border-t border-border/50 bg-background/40 backdrop-blur-sm px-4 sm:px-6 lg:px-8 py-4">
        <div className="mx-auto max-w-4xl">
          <form onSubmit={handleSubmit}>
            <div className="glassmorphism-card rounded-2xl p-4 shadow-lg">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about symptoms, medications, conditions, treatments... (Enter to send, Shift+Enter for new line)"
                disabled={loading}
                rows={1}
                className="w-full min-h-[48px] max-h-[200px] resize-none bg-transparent text-[15px] outline-none placeholder:text-muted-foreground disabled:opacity-60 leading-relaxed"
              />
              <div className="mt-3 flex items-center justify-between">
                <p className="text-xs text-muted-foreground flex items-center gap-2">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>Trusted Sources · Evidence-Based · Cited</span>
                </p>
                <Button 
                  type="submit" 
                  size="md" 
                  disabled={loading || !input.trim()}
                  className="rounded-xl shadow-lg shadow-primary/20 hover:shadow-primary/30 transition-all"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Processing
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4" />
                      Send
                    </>
                  )}
                </Button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
