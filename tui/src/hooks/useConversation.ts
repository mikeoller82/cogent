import { useState, useCallback, useRef } from 'react';
import type { Message } from '../types';
import { GatewayClient } from '../client/gateway';

/**
 * Core conversation hook — manages messages and SSE gateway connection.
 */
export function useConversation() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<
    'disconnected' | 'connecting' | 'connected' | 'error'
  >('disconnected');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const clientRef = useRef<GatewayClient | null>(null);

  const connect = useCallback(async (baseUrl = 'http://localhost:8000') => {
    const client = new GatewayClient(baseUrl);
    clientRef.current = client;

    setConnectionStatus('connecting');

    client.on('error', (e) => {
      const raw = String(e.data.message || '');
      const friendly = raw.includes('ECONNREFUSED') || raw.includes('fetch failed') || raw.includes('connect')
        ? `Cannot reach backend at \`${baseUrl}\`.\n\n  Start the server with \`cogent --server\`\n  or point to a running instance: \`cogent -u <url>\``
        : raw;
      setMessages((prev) => [
        ...prev,
        { role: 'error', content: friendly },
      ]);
      setConnectionStatus('error');
    });

    client.on('connected', (e) => {
      setSessionId(String(e.data.session_id || ''));
      setConnectionStatus('connected');
    });

    client.on('disconnected', () => {
      setConnectionStatus('disconnected');
    });

    try {
      await client.connect();
    } catch {
      setConnectionStatus('error');
    }

    return client;
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      const client = clientRef.current;
      if (!client || !text.trim()) return;

      setMessages((prev) => [...prev, { role: 'user', content: text }]);
      setIsProcessing(true);

      client.on('message', (e) => {
        const type = e.data.type as string;
        const content = e.data.content as string | undefined;

        if (type === 'reasoning') {
          if (content?.startsWith('[auto-continue')) return;
          setMessages((prev) => [
            ...prev,
            { role: 'reasoning', content: content ?? '' },
          ]);
        } else if (type === 'tool_call') {
          const data = e.data.data as any;
          setMessages((prev) => [
            ...prev,
            { role: 'tool_call', data: { tool: data?.tool ?? '', args: data?.args ?? {}, label: data?.label ?? '' } },
          ]);
        } else if (type === 'tool_result') {
          const data = e.data.data as any;
          setMessages((prev) => [
            ...prev,
            { role: 'tool_result', data: { tool: data?.tool ?? '', summary: data?.summary ?? '', display: data?.display ?? '' } },
          ]);
        } else if (type === 'loop') {
          const data = e.data.data as any;
          if (data) {
            setMessages((prev) => [
              ...prev,
              { role: 'loop', data },
            ]);
          }
        } else if (type === 'artifact') {
          setMessages((prev) => [
            ...prev,
            { role: 'status', content: `artifact: ${content ?? ''}` },
          ]);
        } else if (type === 'provider') {
          // Provider fallback / rate-limit event
          const msg = content || 'provider event';
          setMessages((prev) => [
            ...prev,
            { role: 'status', content: `⚡ ${msg}` },
          ]);
        }
      });

      client.on('status', (e) => {
        const content = e.data.content as string;
        if (content) {
          setMessages((prev) => [
            ...prev,
            { role: 'status', content },
          ]);
        }
      });

      client.on('final', (e) => {
        const content = e.data.content as string;
        if (content) {
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content },
          ]);
        } else {
          // Final event with no content — still need something
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: '(no response)' },
          ]);
        }
        setIsProcessing(false);
      });

      client.on('error', (e) => {
        setMessages((prev) => [
          ...prev,
          { role: 'error', content: String(e.data.content || e.data.message || '') },
        ]);
        setIsProcessing(false);
      });

      try {
        await client.send(text);
        // If the stream ended without a final/error event, ensure processing stops
        setIsProcessing(false);
      } catch {
        setIsProcessing(false);
      }
    },
    []
  );

  const disconnect = useCallback(() => {
    clientRef.current?.disconnect();
    clientRef.current = null;
    setConnectionStatus('disconnected');
    setSessionId(null);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const addSystemMessage = useCallback((content: string) => {
    setMessages((prev) => [...prev, { role: 'system', content }]);
  }, []);

  const handleCommand = useCallback(async (text: string): Promise<boolean> => {
    const cmd = text.trim().toLowerCase();

    if (cmd === '/clear') {
      clearMessages();
      return true;
    }

    if (cmd === '/quit' || cmd === '/exit') {
      process.exit(0);
    }

    if (cmd === '/help') {
      addSystemMessage(
        '── Cogent Commands ──────────────────────\n\n' +
        '/help     Show this help message\n' +
        '/skills   List available agent skills\n' +
        '/session  Show current session info\n' +
        '/connect  Reconnect to the backend server\n' +
        '/clear    Clear the conversation\n' +
        '/quit     Exit Cogent\n' +
        '\nTip: Type any message to chat with Cogent.'
      );
      return true;
    }

    if (cmd === '/session') {
      const client = clientRef.current;
      const sid = client?.getSessionId() || sessionId;
      const status = connectionStatus;
      const url = (client as any)?.baseUrl ?? 'unknown';
      addSystemMessage(
        `session  ${sid ? sid.slice(0, 12) + '…' : 'none'}\n` +
        `status   ${status}\n` +
        `server   ${url}`
      );
      return true;
    }

    if (cmd === '/connect') {
      addSystemMessage('Reconnecting to server…');
      return true;
    }

    if (cmd === '/skills') {
      // Fetch skills from the backend API
      const client = clientRef.current;
      const baseUrl = (client as any)?.baseUrl ?? 'http://localhost:8000';
      addSystemMessage('Fetching installed skills…');

      try {
        const res = await fetch(`${baseUrl}/skills`);
        if (!res.ok) {
          addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
          return true;
        }
        const skills: Array<{ name: string; description?: string }> = await res.json();
        if (!skills || skills.length === 0) {
          addSystemMessage('No skills installed. Use /help to learn more about Cogent.');
          return true;
        }
        const lines = skills.map(
          (s, i) => `  ${i + 1}. ${s.name}${s.description ? ' — ' + s.description : ''}`
        );
        addSystemMessage(
          `Installed skills (${skills.length}):\n${lines.join('\n')}`
        );
      } catch (e) {
        addSystemMessage(`Failed to fetch skills: ${e instanceof Error ? e.message : String(e)}`);
      }
      return true;
    }

    return false; // not a command
  }, [clearMessages, addSystemMessage, sessionId, connectionStatus]);

  return {
    messages,
    isProcessing,
    connectionStatus,
    sessionId,
    connect,
    sendMessage,
    disconnect,
    clearMessages,
    addSystemMessage,
    handleCommand,
  };
}
