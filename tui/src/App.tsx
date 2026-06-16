/** @jsxImportSource @opentui/react */
import { useEffect } from 'react';
import { Header } from './components/Header';
import { ChatArea } from './components/ChatArea';
import { InputBar } from './components/InputBar';
import { StatusBar } from './components/StatusBar';
import { useConversation } from './hooks/useConversation';
import { theme } from './theme';

interface AppProps {
  baseUrl?: string;
}

/**
 * Cogent TUI main application component.
 *
 * Layout:
 * ┌────────────────────────────────────────┐
 * │ Header (ASCII logo + branding)         │
 * ├────────────────────────────────────────┤
 * │ ChatArea (scrollable message list)     │
 * │                                        │
 * │                                        │
 * ├────────────────────────────────────────┤
 * │ InputBar (prompt entry)                │
 * ├────────────────────────────────────────┤
 * │ StatusBar (connection, session info)   │
 * └────────────────────────────────────────┘
 */
export function App({ baseUrl = 'http://localhost:8000' }: AppProps) {
  const {
    messages,
    isProcessing,
    connectionStatus,
    sessionId,
    connect,
    sendMessage,
  } = useConversation();


  // Connect on mount
  useEffect(() => {
    (async () => {
      try {
        await connect(baseUrl);
      } catch {
        // Connection error handled in hook
      }
    })();
  }, [baseUrl, connect]);


  const handleSend = (text: string) => {
    // Reconnect if disconnected
    if (connectionStatus === 'disconnected' || connectionStatus === 'error') {
      connect(baseUrl).then(() => sendMessage(text));
    } else {
      sendMessage(text);
    }
  };

  return (
    <box
      style={{
        flexDirection: 'column',
        backgroundColor: theme.bg,
        width: '100%',
        height: '100%',
      }}
    >
      {/* Top bar: logo + info */}
      <Header />

      {/* Main chat area — expands to fill */}
      <ChatArea messages={messages} isProcessing={isProcessing} />

      {/* Input area */}
      <InputBar
        onSend={handleSend}
        disabled={isProcessing}
        connected={connectionStatus === 'connected'}
      />

      {/* Bottom status bar */}
      <StatusBar
        connectionStatus={connectionStatus}
        sessionId={sessionId}
        messageCount={messages.length}
        isProcessing={isProcessing}
      />
    </box>
  );
}
