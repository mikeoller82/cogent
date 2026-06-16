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
      currentAssistantRef.current = '';

      client.on('message', (e) => {
        const type = e.data.type as string;
        if (type === 'reasoning') {
          const content = e.data.content as string;
          if (content.startsWith('[auto-continue')) return;
          setMessages((prev) => [
            ...prev,
            { role: 'reasoning', content },
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

  return {
    messages,
    isProcessing,
    connectionStatus,
    sessionId,
    connect,
    sendMessage,
    disconnect,
  };
}
