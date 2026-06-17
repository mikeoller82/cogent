/**
 * Cogent TUI Gateway Client
 *
 * SSE client that connects to the Cogent FastAPI backend.
 * Adapted from frontend/src/lib/gateway.ts for terminal use.
 */

export type GatewayState = 'idle' | 'connecting' | 'connected' | 'closed' | 'error';
export type GatewayEventType =
  | 'connected'
  | 'status'
  | 'message'
  | 'final'
  | 'error'
  | 'heartbeat'
  | 'disconnected';

export interface GatewayEvent {
  type: GatewayEventType;
  data: Record<string, unknown>;
}

export type GatewayEventHandler = (event: GatewayEvent) => void;

interface Chunk {
  event?: string;
  data?: string;
}

export class GatewayClient {
  private baseUrl: string;
  private sessionId: string | null = null;
  private state: GatewayState = 'idle';
  private abortController: AbortController | null = null;
  private handlers = new Map<GatewayEventType, Set<GatewayEventHandler>>();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  getState(): GatewayState {
    return this.state;
  }

  getSessionId(): string | null {
    return this.sessionId;
  }

  on(eventType: GatewayEventType, handler: GatewayEventHandler): () => void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }
    this.handlers.get(eventType)!.add(handler);
    return () => this.handlers.get(eventType)?.delete(handler);
  }

  private emit(event: GatewayEvent): void {
    const eventHandlers = this.handlers.get(event.type);
    if (eventHandlers) {
      for (const handler of eventHandlers) {
        handler(event);
      }
    }
  }

  private setState(newState: GatewayState): void {
    this.state = newState;
  }

  async connect(sessionId?: string): Promise<void> {
    if (this.state === 'connecting' || this.state === 'connected') return;

    this.setState('connecting');
    this.abortController = new AbortController();

    try {
      if (!sessionId) {
        const res = await fetch(`${this.baseUrl}/api/sessions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: 'TUI session' }),
          signal: this.abortController.signal,
        });
        const session = (await res.json()) as { id: string };
        sessionId = session.id;
      }

      this.sessionId = sessionId;
      this.setState('connected');
      this.reconnectAttempts = 0;
      this.emit({ type: 'connected', data: { session_id: sessionId } });
    } catch (err) {
      this.setState('error');
      this.emit({ type: 'error', data: { message: String(err) } });
      throw err;
    }
  }

  async send(text: string): Promise<void> {
    if (!this.sessionId) {
      throw new Error('Not connected. Call connect() first.');
    }

    try {
      const response = await fetch(
        `${this.baseUrl}/api/sessions/${this.sessionId}/messages/stream`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Accept: 'text/event-stream',
          },
          body: JSON.stringify({ text, attachments: [] }),
          signal: this.abortController?.signal,
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body stream');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split('\n\n');
        buffer = chunks.pop() || '';

        for (const chunk of chunks) {
          this.processChunk(chunk);
        }
      }

      if (buffer.trim()) {
        this.processChunk(buffer);
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      this.emit({ type: 'error', data: { message: String(err) } });
      throw err;
    }
  }

  private processChunk(chunk: string): void {
    const lines = chunk.split('\n');
    let sseEventType = '';
    let data = '';

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        sseEventType = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        data = line.slice(6).trim();
      }
    }

    if (!data) return;

    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(data);
    } catch {
      parsed = { raw: data };
    }

    // Backend sends data: {"type":"reasoning","content":"..."} without
    // an SSE event: prefix. Fall back to parsed.type when empty.
    const type = sseEventType || (parsed.type as string) || '';

    switch (type) {
      case 'status':
        this.emit({ type: 'status', data: parsed });
        break;
      case 'tool':
        this.emit({ type: 'message', data: { type: 'tool_call', ...parsed } as any });
        break;
      case 'tool_result':
        this.emit({ type: 'message', data: { type: 'tool_result', ...parsed } as any });
        break;
      case 'artifact':
        this.emit({ type: 'message', data: { type: 'artifact', ...parsed } as any });
        break;
      case 'loop':
        this.emit({ type: 'message', data: { type: 'loop', ...parsed } as any });
        break;
      case 'reasoning':
        this.emit({ type: 'message', data: { type: 'reasoning', ...parsed } as any });
        break;
      case 'provider':
        this.emit({ type: 'message', data: { type: 'provider', ...parsed } as any });
        break;
      case 'final':
        this.emit({ type: 'final', data: parsed });
        break;
      case 'error':
        this.emit({ type: 'error', data: parsed });
        break;
      case 'user_saved':
        // Backend bookkeeping — handled implicitly
        break;
      case 'done': {
        // Backend sends the authoritative assistant message here.
        // Extract content and emit as final for the hook.
        const msg = (parsed.message as Record<string, unknown>) || {};
        const content = (msg.content as string) || '(no response)';
        this.emit({ type: 'final', data: { content } });
        break;
      }
      default:
        this.emit({ type: 'message', data: { type, ...parsed } as any });
    }
  }

  disconnect(): void {
    this.abortController?.abort();
    this.abortController = null;
    this.setState('closed');
    this.emit({ type: 'disconnected', data: {} });
  }

  async reconnect(): Promise<void> {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.emit({ type: 'error', data: { message: 'Max reconnection attempts reached' } });
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    const { promise, resolve } = Promise.withResolvers<void>();
    setTimeout(resolve, delay);
    await promise;

    await this.connect(this.sessionId || undefined);
  }
}
