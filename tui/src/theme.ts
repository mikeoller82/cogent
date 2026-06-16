/**
 * Cogent TUI Theme
 * Dark terminal color palette
 */

export const theme = {
  bg: '#0d1117',
  surface: '#161b22',
  surfaceAlt: '#1c2333',
  border: '#30363d',
  borderFocus: '#58a6ff',
  primary: '#58a6ff',
  secondary: '#a855f7',
  success: '#3fb950',
  warning: '#d29922',
  error: '#f85149',
  text: '#e6edf3',
  textMuted: '#8b949e',
  textDim: '#484f58',
  accent: '#79c0ff',
} as const;

export type Theme = typeof theme;
