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

  const getBaseUrl = useCallback((): string => {
    return clientRef.current?.getBaseUrl() ?? 'http://localhost:8000';
  }, []);

  const handleCommand = useCallback(async (text: string): Promise<boolean> => {
    const parts = text.trim().split(/\s+/);
    const cmd = parts[0]?.toLowerCase() ?? '';
    const args = parts.slice(1);

    // ── /clear ──────────────────────────────────────────
    if (cmd === '/clear') {
      clearMessages();
      return true;
    }

    // ── /quit / /exit ────────────────────────────────────
    if (cmd === '/quit' || cmd === '/exit') {
      process.exit(0);
    }

    // ── /help ────────────────────────────────────────────
    if (cmd === '/help') {
      addSystemMessage(
        '── Cogent Commands ─────────────────────────────────\n\n' +
        'Session\n' +
        '  /session                        Show current session info\n' +
        '  /sessions                       List all sessions\n' +
        '  /connect                        Reconnect to server\n' +
        '  /disconnect                     Disconnect from server\n' +
        '  /clear                          Clear conversation\n' +
        '  /quit                           Exit Cogent\n\n' +
        'Memory (KV store)\n' +
        '  /memory                         List all stored memories\n' +
        '  /memory add <key> <value>       Store a memory\n' +
        '  /memory delete <key>            Delete a memory\n\n' +
        'Tasks (scheduled)\n' +
        '  /tasks                          List scheduled tasks\n' +
        '  /tasks run <id>                 Run a task now\n' +
        '  /tasks delete <id>              Delete a task\n\n' +
        'Skills\n' +
        '  /skills                         List installed skills\n' +
        '  /skills install <github-url>    Import skills from a GitHub repo\n' +
        '  /skills forge <github-url>      Generate a skill from a GitHub repo via LLM\n' +
        '  /skills delete <name>           Delete an installed skill\n\n' +
        'MCP Registry\n' +
        '  /mcp                            List installed MCP servers\n' +
        '  /mcp search <query>             Search MCP registry\n' +
        '  /mcp install <server-id>        Install an MCP server\n' +
        '  /mcp remove <server-id>         Remove an MCP server\n' +
        '  /mcp sync                       Sync latest MCP servers from GitHub\n\n' +
        'Tip: Type any message to chat with Cogent.'
      );
      return true;
    }

    // ── /disconnect ──────────────────────────────────────
    if (cmd === '/disconnect') {
      disconnect();
      addSystemMessage('Disconnected from server.');
      return true;
    }

    // ── /connect ─────────────────────────────────────────
    if (cmd === '/connect') {
      addSystemMessage('Reconnecting to server…');
      return true;
    }

    // ── /session ─────────────────────────────────────────
    if (cmd === '/session') {
      const client = clientRef.current;
      const sid = client?.getSessionId() || sessionId;
      const status = connectionStatus;
      const url = getBaseUrl();
      addSystemMessage(
        `session  ${sid ? sid.slice(0, 12) + '…' : 'none'}\n` +
        `status   ${status}\n` +
        `server   ${url}`
      );
      return true;
    }

    // ── /sessions ────────────────────────────────────────
    if (cmd === '/sessions') {
      const baseUrl = getBaseUrl();
      addSystemMessage('Fetching sessions…');

      try {
        const res = await fetch(`${baseUrl}/api/sessions`);
        if (!res.ok) {
          addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
          return true;
        }
        const sessions: Array<{ id: string; title?: string; updated_at?: string }> = await res.json();
        if (!sessions || sessions.length === 0) {
          addSystemMessage('No sessions found. Start a chat to create one.');
          return true;
        }
        const lines = sessions.slice(0, 20).map(
          (s, i) => `  ${i + 1}. ${s.id.slice(0, 12)}…  ${s.title ?? '(untitled)'}`
        );
        const total = sessions.length;
        addSystemMessage(
          `Sessions (${total}${total > 20 ? ', showing 20' : ''}):\n${lines.join('\n')}`
        );
      } catch (e) {
        addSystemMessage(`Failed to list sessions: ${e instanceof Error ? e.message : String(e)}`);
      }
      return true;
    }

    // ── /memory ──────────────────────────────────────────
    if (cmd === '/memory') {
      const baseUrl = getBaseUrl();
      const sub = args[0]?.toLowerCase();

      // /memory add <key> <value>
      if (sub === 'add') {
        const key = args[1];
        const value = args.slice(2).join(' ');
        if (!key || !value) {
          addSystemMessage('Usage: /memory add <key> <value>');
          return true;
        }
        try {
          const res = await fetch(`${baseUrl}/api/memory`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key, value }),
          });
          if (!res.ok) {
            addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
            return true;
          }
          addSystemMessage(`Memory stored: ${key}`);
        } catch (e) {
          addSystemMessage(`Failed to store memory: ${e instanceof Error ? e.message : String(e)}`);
        }
        return true;
      }

      // /memory delete <key>
      if (sub === 'delete') {
        const key = args[1];
        if (!key) {
          addSystemMessage('Usage: /memory delete <key>');
          return true;
        }
        try {
          const res = await fetch(`${baseUrl}/api/memory/${encodeURIComponent(key)}`, {
            method: 'DELETE',
          });
          if (!res.ok) {
            addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
            return true;
          }
          addSystemMessage(`Memory deleted: ${key}`);
        } catch (e) {
          addSystemMessage(`Failed to delete memory: ${e instanceof Error ? e.message : String(e)}`);
        }
        return true;
      }

      // /memory (list)
      addSystemMessage('Fetching memories…');
      try {
        const res = await fetch(`${baseUrl}/api/memory`);
        if (!res.ok) {
          addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
          return true;
        }
        const mems: Array<{ key: string; value: string }> = await res.json();
        if (!mems || mems.length === 0) {
          addSystemMessage('No memories stored. Use /memory add <key> <value> to store one.');
          return true;
        }
        const lines = mems.map((m, i) => `  ${i + 1}. ${m.key}: ${m.value.slice(0, 80)}`);
        addSystemMessage(`Memories (${mems.length}):\n${lines.join('\n')}`);
      } catch (e) {
        addSystemMessage(`Failed to list memories: ${e instanceof Error ? e.message : String(e)}`);
      }
      return true;
    }

    // ── /tasks ───────────────────────────────────────────
    if (cmd === '/tasks') {
      const baseUrl = getBaseUrl();
      const sub = args[0]?.toLowerCase();

      // /tasks run <id>
      if (sub === 'run') {
        const taskId = args[1];
        if (!taskId) {
          addSystemMessage('Usage: /tasks run <task-id>');
          return true;
        }
        try {
          const res = await fetch(`${baseUrl}/api/tasks/${encodeURIComponent(taskId)}/run`, {
            method: 'POST',
          });
          if (!res.ok) {
            addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
            return true;
          }
          addSystemMessage(`Task triggered: ${taskId}`);
        } catch (e) {
          addSystemMessage(`Failed to run task: ${e instanceof Error ? e.message : String(e)}`);
        }
        return true;
      }

      // /tasks delete <id>
      if (sub === 'delete') {
        const taskId = args[1];
        if (!taskId) {
          addSystemMessage('Usage: /tasks delete <task-id>');
          return true;
        }
        try {
          const res = await fetch(`${baseUrl}/api/tasks/${encodeURIComponent(taskId)}`, {
            method: 'DELETE',
          });
          if (!res.ok) {
            addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
            return true;
          }
          addSystemMessage(`Task deleted: ${taskId}`);
        } catch (e) {
          addSystemMessage(`Failed to delete task: ${e instanceof Error ? e.message : String(e)}`);
        }
        return true;
      }

      // /tasks (list)
      addSystemMessage('Fetching scheduled tasks…');
      try {
        const res = await fetch(`${baseUrl}/api/tasks`);
        if (!res.ok) {
          addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
          return true;
        }
        const tasks: Array<{ id: string; name?: string; cadence?: string; status?: string; next_run?: string }> = await res.json();
        if (!tasks || tasks.length === 0) {
          addSystemMessage('No tasks scheduled.');
          return true;
        }
        const lines = tasks.map(
          (t, i) => `  ${i + 1}. ${t.name ?? t.id.slice(0, 12)}  |  ${t.cadence ?? '—'}  |  ${t.status ?? '—'}`
        );
        addSystemMessage(`Scheduled tasks (${tasks.length}):\n${lines.join('\n')}`);
      } catch (e) {
        addSystemMessage(`Failed to list tasks: ${e instanceof Error ? e.message : String(e)}`);
      }
      return true;
    }

    // ── /skills ──────────────────────────────────────────
    if (cmd === '/skills') {
      const baseUrl = getBaseUrl();
      const sub = args[0]?.toLowerCase();

      // /skills install <url>
      if (sub === 'install') {
        const repoUrl = args[1];
        if (!repoUrl) {
          addSystemMessage('Usage: /skills install <github-repo-url>');
          return true;
        }
        addSystemMessage(`Importing skills from ${repoUrl}…`);
        try {
          const res = await fetch(`${baseUrl}/api/skills/import`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ repo_url: repoUrl }),
          });
          if (!res.ok) {
            addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
            return true;
          }
          const result = await res.json();
          addSystemMessage(`Skills imported: ${JSON.stringify(result)}`);
        } catch (e) {
          addSystemMessage(`Failed to import skills: ${e instanceof Error ? e.message : String(e)}`);
        }
        return true;
      }

      // /skills forge <url>
      if (sub === 'forge') {
        const repoUrl = args[1];
        if (!repoUrl) {
          addSystemMessage('Usage: /skills forge <github-repo-url>');
          return true;
        }
        addSystemMessage(`Forging skill from ${repoUrl}…`);
        try {
          const res = await fetch(`${baseUrl}/api/skills/forge`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ repo_url: repoUrl }),
          });
          if (!res.ok) {
            addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
            return true;
          }
          const result = await res.json();
          addSystemMessage(`Skill forged: ${JSON.stringify(result)}`);
        } catch (e) {
          addSystemMessage(`Failed to forge skill: ${e instanceof Error ? e.message : String(e)}`);
        }
        return true;
      }

      // /skills delete <name>
      if (sub === 'delete') {
        const name = args[1];
        if (!name) {
          addSystemMessage('Usage: /skills delete <skill-name>');
          return true;
        }
        try {
          const res = await fetch(`${baseUrl}/api/skills/${encodeURIComponent(name)}`, {
            method: 'DELETE',
          });
          if (!res.ok) {
            addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
            return true;
          }
          addSystemMessage(`Skill deleted: ${name}`);
        } catch (e) {
          addSystemMessage(`Failed to delete skill: ${e instanceof Error ? e.message : String(e)}`);
        }
        return true;
      }

      // /skills (list)
      addSystemMessage('Fetching installed skills…');
      try {
        const res = await fetch(`${baseUrl}/api/skills`);
        if (!res.ok) {
          addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
          return true;
        }
        const skills: Array<{ name: string; description?: string }> = await res.json();
        if (!skills || skills.length === 0) {
          addSystemMessage('No skills installed. Use /skills install <url> to add some.');
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

    // ── /mcp ─────────────────────────────────────────────
    if (cmd === '/mcp') {
      const baseUrl = getBaseUrl();
      const sub = args[0]?.toLowerCase();

      // /mcp search <query>
      if (sub === 'search') {
        const query = args.slice(1).join(' ');
        if (!query) {
          addSystemMessage('Usage: /mcp search <query>');
          return true;
        }
        addSystemMessage(`Searching MCP registry for "${query}"…`);
        try {
          const res = await fetch(`${baseUrl}/api/mcp/registry?query=${encodeURIComponent(query)}`);
          if (!res.ok) {
            addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
            return true;
          }
          const results: Array<{ id?: string; name?: string; description?: string; stars?: number; language?: string }> = await res.json();
          if (!results || results.length === 0) {
            addSystemMessage(`No MCP servers found for "${query}".`);
            return true;
          }
          const lines = results.slice(0, 15).map(
            (s, i) => `  ${i + 1}. ${s.name ?? s.id ?? '?'}  ⭐${s.stars ?? 0}  ${s.language ?? ''}`
          );
          addSystemMessage(
            `MCP servers matching "${query}" (${results.length}):\n${lines.join('\n')}`
          );
        } catch (e) {
          addSystemMessage(`Failed to search MCP: ${e instanceof Error ? e.message : String(e)}`);
        }
        return true;
      }

      // /mcp install <server-id>
      if (sub === 'install') {
        const serverId = args[1];
        if (!serverId) {
          addSystemMessage('Usage: /mcp install <server-id>');
          return true;
        }
        addSystemMessage(`Installing MCP server: ${serverId}…`);
        try {
          const res = await fetch(`${baseUrl}/api/mcp/install`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ server_id: serverId }),
          });
          if (!res.ok) {
            addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
            return true;
          }
          addSystemMessage(`MCP server installed: ${serverId}`);
        } catch (e) {
          addSystemMessage(`Failed to install MCP server: ${e instanceof Error ? e.message : String(e)}`);
        }
        return true;
      }

      // /mcp remove <server-id>
      if (sub === 'remove') {
        const serverId = args[1];
        if (!serverId) {
          addSystemMessage('Usage: /mcp remove <server-id>');
          return true;
        }
        try {
          const res = await fetch(`${baseUrl}/api/mcp/remove`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ server_id: serverId }),
          });
          if (!res.ok) {
            addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
            return true;
          }
          addSystemMessage(`MCP server removed: ${serverId}`);
        } catch (e) {
          addSystemMessage(`Failed to remove MCP server: ${e instanceof Error ? e.message : String(e)}`);
        }
        return true;
      }

      // /mcp sync
      if (sub === 'sync') {
        addSystemMessage('Syncing MCP registry…');
        try {
          const res = await fetch(`${baseUrl}/api/mcp/registry/sync`, { method: 'POST' });
          if (!res.ok) {
            addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
            return true;
          }
          addSystemMessage('MCP registry synced successfully.');
        } catch (e) {
          addSystemMessage(`Failed to sync MCP registry: ${e instanceof Error ? e.message : String(e)}`);
        }
        return true;
      }

      // /mcp (list installed)
      addSystemMessage('Fetching installed MCP servers…');
      try {
        const res = await fetch(`${baseUrl}/api/mcp/installed`);
        if (!res.ok) {
          addSystemMessage(`Error: server returned ${res.status} ${res.statusText}`);
          return true;
        }
        const installed: Array<{ id?: string; name?: string; status?: string }> = await res.json();
        if (!installed || installed.length === 0) {
          addSystemMessage('No MCP servers installed. Use /mcp search <query> then /mcp install <id>.');
          return true;
        }
        const lines = installed.map(
          (s, i) => `  ${i + 1}. ${s.name ?? s.id ?? '?'}  |  ${s.status ?? '—'}`
        );
        addSystemMessage(`Installed MCP servers (${installed.length}):\n${lines.join('\n')}`);
      } catch (e) {
        addSystemMessage(`Failed to list MCP servers: ${e instanceof Error ? e.message : String(e)}`);
      }
      return true;
    }

    return false; // not a command
  }, [clearMessages, addSystemMessage, disconnect, sessionId, connectionStatus, getBaseUrl]);

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
