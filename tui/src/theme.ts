/**
 * Cogent TUI Theme
 * Blue & Black premium terminal palette
 */

export const theme = {
  bg: '#0a0e1a',
  surface: '#111827',
  surfaceAlt: '#1e293b',
  border: '#1e3a5f',
  borderFocus: '#3b82f6',
  primary: '#3b82f6',
  primaryBright: '#60a5fa',
  secondary: '#6366f1',
  success: '#22c55e',
  warning: '#f59e0b',
  error: '#ef4444',
  text: '#f1f5f9',
  textMuted: '#94a3b8',
  textDim: '#475569',
  accent: '#818cf8',
  headerBg: '#0f172a',
  headerBorder: '#1e40af',
} as const;

export type Theme = typeof theme;
