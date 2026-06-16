/** @jsxImportSource @opentui/react */
import { theme } from '../theme';
import type { Message, ToolCall, ToolResult, LoopState } from '../types';

interface ChatAreaProps {
  messages: Message[];
  isProcessing: boolean;
}

function ToolCallView({ data }: { data: ToolCall }) {
  return (
    <box style={{ flexDirection: 'row', padding: { left: 2 } }}>
      <text style={{ color: theme.warning }} content="⚡ " />
      <text style={{ color: theme.accent }} content={data.tool} />
      <text style={{ color: theme.textMuted }} content={` ${data.label}`} />
    </box>
  );
}

function ToolResultView({ data }: { data: ToolResult }) {
  return (
    <box style={{ flexDirection: 'column', padding: { left: 2 } }}>
      <box style={{ flexDirection: 'row' }}>
        <text style={{ color: theme.success }} content="✓ " />
        <text style={{ color: theme.textMuted }} content={data.display} />
      </box>
      {data.summary && (
        <text
          style={{ color: theme.textDim, padding: { left: 4 } }}
          content={data.summary.slice(0, 200)}
        />
      )}
    </box>
  );
}

function LoopStateView({ data }: { data: LoopState }) {
  const phaseColors: Record<string, string> = {
    PLAN: theme.warning,
    EXECUTE: theme.primary,
    VERIFY: theme.success,
    DONE: theme.success,
    ERROR: theme.error,
  };
  const color = phaseColors[data.phase] || theme.textMuted;

  return (
    <box style={{ flexDirection: 'row', padding: { left: 2 } }}>
      <text style={{ color }} content={`◆ ${data.phase}`} />
      {data.iteration !== undefined && (
        <text
          style={{ color: theme.textDim }}
          content={` #${data.iteration}`}
        />
      )}
      {data.verdict && (
        <text
          style={{
            color: data.verdict === 'PASS' ? theme.success : theme.warning,
          }}
          content={` ${data.verdict}`}
        />
      )}
      {data.message && (
        <text style={{ color: theme.textMuted }} content={` — ${data.message}`} />
      )}
    </box>
  );
}

function StatusMessage({ content }: { content: string }) {
  return (
    <box style={{ flexDirection: 'row', padding: { left: 2 } }}>
      <text style={{ color: theme.textDim }} content="⋯ " />
      <text style={{ color: theme.textMuted }} content={content} />
    </box>
  );
}

function ErrorMessage({ content }: { content: string }) {
  return (
    <box
      style={{
        flexDirection: 'row',
        padding: { left: 1, right: 1 },
        backgroundColor: theme.error,
      }}
    >
      <text style={{ color: '#ffffff' }} content={`✗ ${content}`} />
    </box>
  );
}

/** Render a single message in the chat */
function MessageItem({ message }: { message: Message }) {
  switch (message.role) {
    case 'user':
      return (
        <box style={{ flexDirection: 'column', marginTop: 1 }}>
          <box
            style={{
              flexDirection: 'row',
              padding: { left: 1, right: 1 },
              backgroundColor: theme.surfaceAlt,
              alignSelf: 'flex-start',
            }}
          >
            <text style={{ color: theme.primary, fontWeight: 'bold' }} content="You " />
          </box>
          <text
            style={{
              color: theme.text,
              padding: { left: 1 },
            }}
            content={message.content}
          />
        </box>
      );

    case 'assistant':
      return (
        <box style={{ flexDirection: 'column', marginTop: 1 }}>
          <box
            style={{
              flexDirection: 'row',
              padding: { left: 1, right: 1 },
              backgroundColor: theme.secondary,
              alignSelf: 'flex-start',
            }}
          >
            <text style={{ color: '#ffffff', fontWeight: 'bold' }} content="Cogent " />
          </box>
          <text
            style={{
              color: theme.text,
              padding: { left: 1 },
            }}
            content={message.content}
          />
        </box>
      );

    case 'reasoning':
      return (
        <box style={{ flexDirection: 'row', padding: { left: 1 } }}>
          <text style={{ color: theme.textDim }} content="💭 " />
          <text
            style={{ color: theme.textDim }}
            content={message.content.slice(0, 300)}
          />
        </box>
      );

    case 'tool_call':
      return <ToolCallView data={message.data} />;

    case 'tool_result':
      return <ToolResultView data={message.data} />;

    case 'loop':
      return <LoopStateView data={message.data} />;

    case 'status':
      return <StatusMessage content={message.content} />;

    case 'error':
      return <ErrorMessage content={message.content} />;

    default:
      return null;
  }
}

/** Scrolling message list */
export function ChatArea({ messages, isProcessing }: ChatAreaProps) {
  return (
    <box
      style={{
        flexDirection: 'column',
        flexGrow: 1,
        borderStyle: 'single',
        borderColor: theme.border,
        backgroundColor: theme.bg,
      }}
    >
      <scrollbox
        style={{
          flexDirection: 'column',
          flexGrow: 1,
          padding: 1,
        }}
      >
        {messages.length === 0 && !isProcessing && (
          <box
            style={{
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 4,
            }}
          >
            <text
              style={{ color: theme.textMuted }}
              content="Welcome to Cogent — your AI co-worker"
            />
            <text
              style={{ color: theme.textDim }}
              content="Type a message below to get started."
            />
            <box style={{ height: 1 }} />
            <text
              style={{ color: theme.textDim }}
              content="Commands: /help  /clear  /connect  /quit"
            />
          </box>
        )}

        {messages.map((msg, i) => (
          <MessageItem key={i} message={msg} />
        ))}

        {isProcessing && (
          <box style={{ flexDirection: 'row', padding: { left: 1 }, marginTop: 1 }}>
            <text style={{ color: theme.secondary }} content="● " />
            <text style={{ color: theme.textMuted }} content="Cogent is thinking..." />
          </box>
        )}
      </scrollbox>
    </box>
  );
}
