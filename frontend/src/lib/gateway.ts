/**
 * Cogent Gateway Client
 *
 * Manages the SSE (Server-Sent Events) connection to the Cogent FastAPI backend.
 * Mirrors Hermes' apps/shared/src/json-rpc-gateway.ts architecture
 * but adapted for Cogent's SSE-based streaming protocol.
 *
 * Events:
 *   - 'connected': Initial connection established
 *   - 'status': Turn status updates (thinking, tool_call, tool_result)
 *   - 'message': Streamed message content (delta)
 *   - 'final': Complete assistant message
 *   - 'error': Error events
 *   - 'heartbeat': Keep-alive pings
 *   - 'disconnected': Connection closed
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

interface PendingRequest {
  resolve: (value: unknown) => void;
  reject: (reason: unknown) => void;
  timeoutId: ReturnType<typeof setTimeout>;
}

interface Chunk {
  event?: string;
  data?: string;
}

export class GatewayClient {
  private baseUrl: string;
  private sessionId: string | null = null;
  private state: GatewayState = 'idle';
  private eventSource: EventSource | null = null;
  private abortController: AbortController | null = null;
  private handlers: Map<GatewayEventType, Set<GatewayEventHandler>> = new Map();
  private pendingRequests: Map<string, PendingRequest> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(baseUrl: string = 'http://localhost:8000') {
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

  off(eventType: GatewayEventType, handler: GatewayEventHandler): void {
    this.handlers.get(eventType)?.delete(handler);
  }

  private emit(event: GatewayEvent): void {
    const eventHandlers = this.handlers.get(event.type);
    if (eventHandlers) {
      eventHandlers.forEach((handler) => handler(event));
    }
  }

  private setState(newState: GatewayState): void {
    this.state = newState;
  }

  /**
   * Connect to the Cogent backend via SSE streaming.
   * Uses Fetch + ReadableStream for SSE (more reliable than EventSource
   * for POST-based streaming endpoints).
   */
  async connect(sessionId?: string): Promise<void> {
    if (this.state === 'connecting' || this.state === 'connected') {
      return;
    }

    this.setState('connecting');
    this.abortController = new AbortController();

    try {
      // Create session if not provided
      if (!sessionId) {
        const res = await fetch(`${this.baseUrl}/api/sessions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: 'Gateway session' }),
          signal: this.abortController.signal,
        });
        const session = await res.json();
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

  /**
   * Send a message via the streaming endpoint.
   * Reads the SSE stream and emits events as they arrive.
   */
  async send(text: string, attachments: Array<{ id: string; filename: string; size: number }> = []): Promise<void> {
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
          body: JSON.stringify({ text, attachments }),
          signal: this.abortController?.signal,
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body stream');
      }

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

      // Process remaining buffer
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

  /**
   * Disconnect from the backend.
   */
  disconnect(): void {
    this.abortController?.abort();
    this.abortController = null;
    this.eventSource?.close();
    this.eventSource = null;
    this.setState('closed');
    this.emit({ type: 'disconnected', data: {} });
  }

  /**
   * Reconnect with session persistence.
   */
  async reconnect(): Promise<void> {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.emit({ type: 'error', data: { message: 'Max reconnection attempts reached' } });
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    await new Promise((resolve) => setTimeout(resolve, delay));

    await this.connect(this.sessionId || undefined);
  }
}
