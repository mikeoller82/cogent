/** @jsxImportSource @opentui/react */
import { theme } from '../theme';

interface StatusBarProps {
  connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
  sessionId: string | null;
  messageCount: number;
  isProcessing: boolean;
}

export function StatusBar({
  connectionStatus,
  sessionId,
  messageCount,
  isProcessing,
}: StatusBarProps) {
  const statusColors: Record<string, string> = {
    disconnected: theme.error,
    connecting: theme.warning,
    connected: theme.success,
    error: theme.error,
  };

  const statusLabels: Record<string, string> = {
    disconnected: 'disconnected',
    connecting: 'connecting…',
    connected: 'connected',
    error: 'error',
  };

  return (
    <box
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        padding: { left: 1, right: 1 },
        backgroundColor: theme.surface,
        borderStyle: 'single',
        borderColor: theme.border,
      }}
    >
      {/* Connection status dot */}
      <box style={{ flexDirection: 'row', alignItems: 'center' }}>
        <text
          style={{ color: statusColors[connectionStatus] }}
          content={connectionStatus === 'connected' ? '●' : '○'}
        />
        <text
          style={{ color: theme.textMuted, padding: { left: 1 } }}
          content={statusLabels[connectionStatus]}
        />
      </box>

      {/* Session info */}
      {sessionId && (
        <box style={{ flexDirection: 'row', padding: { left: 2 } }}>
          <text style={{ color: theme.textDim }} content={`session: ${sessionId.slice(0, 8)}`} />
        </box>
      )}

      {/* Message count */}
      <box style={{ flexDirection: 'row', padding: { left: 2 } }}>
        <text style={{ color: theme.textDim }} content={`${messageCount} messages`} />
      </box>

      {/* Processing indicator */}
      {isProcessing && (
        <box style={{ flexDirection: 'row', padding: { left: 2 } }}>
          <text style={{ color: theme.secondary }} content="processing…" />
        </box>
      )}

      {/* Spacer */}
      <box style={{ flexGrow: 1 }} />

      {/* Version / server info */}
      <text
        style={{ color: theme.textDim }}
        content="Cogent TUI v0.1"
      />
    </box>
  );
}
