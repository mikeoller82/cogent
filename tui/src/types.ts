/**
 * Message types for the conversation store
 */

export interface ToolCall {
  tool: string;
  args: Record<string, unknown>;
  label: string;
}

export interface ToolResult {
  tool: string;
  summary: string;
  display: string;
}

export interface LoopState {
  phase: string;
  iteration?: number;
  verdict?: string;
  notes?: string;
  message?: string;
}

export type Message =
  | { role: 'user'; content: string }
  | { role: 'assistant'; content: string }
  | { role: 'reasoning'; content: string }
  | { role: 'status'; content: string }
  | { role: 'tool_call'; data: ToolCall }
  | { role: 'tool_result'; data: ToolResult }
  | { role: 'loop'; data: LoopState }
  | { role: 'error'; content: string };
