'use client';

import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { Sidebar } from '@/components/layout/sidebar';
import { Topbar } from '@/components/layout/topbar';

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [desktopOpen, setDesktopOpen] = useState(true);

  return (
    <div className="relative min-h-screen bg-background text-foreground flex overflow-hidden">
      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div 
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}
      
      {/* Mobile sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-72 transform transition-transform duration-300 lg:hidden ${
        mobileOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <Sidebar onClose={() => setMobileOpen(false)} />
      </div>

      {/* Desktop sidebar */}
      <div className={`hidden lg:block transition-all duration-300 ease-in-out overflow-hidden flex-shrink-0 z-20 bg-background/50 ${
        desktopOpen ? 'w-72' : 'w-0'
      }`}>
        <div className="w-72 h-full">
          <Sidebar />
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 flex-col min-w-0">
        <Topbar onMenuClick={() => {
          setMobileOpen(!mobileOpen);
          setDesktopOpen(!desktopOpen);
        }} />
        <main className="flex-1 overflow-x-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}
