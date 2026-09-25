declare module 'react' {
  export type ReactNode = any;
  export type ReactElement = any;

  export type PropsWithChildren<P = object> = P & { children?: ReactNode };
  export type ComponentProps<T> = T extends (props: infer P) => any ? P : any;

  export interface Attributes {
    key?: string | number;
  }

  export interface DOMAttributes<T> {
    onClick?: (...args: any[]) => any;
    onChange?: (...args: any[]) => any;
    onSubmit?: (...args: any[]) => any;
  }

  export interface HTMLAttributes<T> extends DOMAttributes<T> {
    className?: string;
    children?: ReactNode;
  }

  export interface ButtonHTMLAttributes<T> extends HTMLAttributes<T> {
    type?: 'button' | 'submit' | 'reset';
    disabled?: boolean;
  }

  export interface InputHTMLAttributes<T> extends HTMLAttributes<T> {
    placeholder?: string;
    value?: any;
    defaultValue?: any;
    type?: string;
  }

  export interface TextareaHTMLAttributes<T> extends HTMLAttributes<T> {
    placeholder?: string;
    value?: any;
    defaultValue?: any;
    rows?: number;
  }

  export interface FormEvent<T = any> {
    preventDefault(): void;
    target: T;
  }

  export function forwardRef<T, P = object>(render: any): any;
  export function useEffect(effect: any, deps?: any[]): void;
  export function useMemo<T>(factory: () => T, deps?: any[]): T;
  export function useState<T>(initial: T | (() => T)): [T, (value: T | ((prev: T) => T)) => void];

  export const Fragment: any;
  const React: any;
  export default React;
}

declare module 'next/link' {
  import type { ReactNode } from 'react';
  export default function Link(props: { href: string; children?: ReactNode; className?: string }): any;
}

declare module 'next/navigation' {
  export function redirect(path: string): never;
}

declare module 'next-themes' {
  import type { ReactNode } from 'react';

  export function useTheme(): {
    theme?: string;
    setTheme: (theme: string) => void;
    resolvedTheme?: string;
    systemTheme?: string;
  };

  export function ThemeProvider(props: {
    children?: ReactNode;
    attribute?: string;
    defaultTheme?: string;
    enableSystem?: boolean;
    disableTransitionOnChange?: boolean;
  }): any;
}

declare module 'lucide-react' {
  export const Bell: any;
  export const MoonStar: any;
  export const Search: any;
  export const SunMedium: any;
  export const Brain: any;
  export const ChartColumn: any;
  export const FileText: any;
  export const Microscope: any;
  export const ShieldCheck: any;
  export const ChevronDown: any;
  export const ExternalLink: any;
  export const Paperclip: any;
  export const Send: any;
  export const Sparkles: any;
  export const ArrowLeft: any;
  export const BookOpen: any;
}

declare global {
  namespace JSX {
    interface IntrinsicElements {
      [elemName: string]: any;
    }

    interface Element {}
  }
}

export {};
