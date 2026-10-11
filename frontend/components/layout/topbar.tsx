"use client";

import { Menu, MoonStar, SunMedium, Sparkles } from 'lucide-react';
import { useTheme } from 'next-themes';

import { Button } from '@/components/ui/button';

interface TopbarProps {
  onMenuClick?: () => void;
}

export function Topbar({ onMenuClick }: TopbarProps) {
  const { theme, setTheme } = useTheme();

  return (
    <header className="sticky top-0 z-30 border-b border-border/50 backdrop-blur-xl bg-background/70">
      <div className="flex items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-4">
          {onMenuClick && (
            <button
              onClick={onMenuClick}
              className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <Menu className="h-5 w-5" />
            </button>
          )}
          <div className="hidden sm:flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <p className="text-sm font-medium text-foreground">MedInsight AI</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="md"
            aria-label="Toggle theme"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="rounded-xl hover:bg-muted"
          >
            {theme === 'dark' ? (
              <SunMedium className="h-4 w-4 text-muted-foreground" />
            ) : (
              <MoonStar className="h-4 w-4 text-muted-foreground" />
            )}
          </Button>
        </div>
      </div>
    </header>
  );
}
