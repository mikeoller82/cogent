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

type MessageBase = { content: string };
type MessageWithData<T> = { data: T };

export type Message =
  | ({ role: 'user' } & MessageBase)
  | ({ role: 'assistant' } & MessageBase)
  | ({ role: 'reasoning' } & MessageBase)
  | ({ role: 'system' } & MessageBase)
  | ({ role: 'status' } & MessageBase)
  | ({ role: 'tool_call' } & MessageWithData<ToolCall>)
  | ({ role: 'tool_result' } & MessageWithData<ToolResult>)
  | ({ role: 'loop' } & MessageWithData<LoopState>)
  | ({ role: 'error' } & MessageBase);
