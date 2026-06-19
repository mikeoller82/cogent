/** @jsxImportSource @opentui/react */
import { useState, useCallback, useRef } from 'react';
import { theme } from '../theme';

interface InputBarProps {
  onSend: (text: string) => void;
  onCommand: (text: string) => Promise<boolean>;
  disabled: boolean;
  connected: boolean;
}

export function InputBar({ onSend, onCommand, disabled, connected }: InputBarProps) {
  const [value, setValue] = useState('');
  const inputRef = useRef<{ focus: () => void }>(null);

  const handleSubmit = useCallback(
    async (val: string) => {
      const trimmed = val.trim();
      if (!trimmed || disabled) return;

      if (trimmed.startsWith('/')) {
        const handled = await onCommand(trimmed);
        if (handled) {
          setValue('');
          return;
        }
      }

      onSend(trimmed);
      setValue('');
      setTimeout(() => inputRef.current?.focus(), 0);
    },
    [onSend, onCommand, disabled]
  );

  const connectedIcon = connected ? '▶' : '✗';

  return (
    <box
      style={{
        flexDirection: 'column',
        borderStyle: 'round',
        borderColor: connected ? theme.borderFocus : theme.border,
        backgroundColor: theme.surface,
        margin: { left: 1, right: 1, bottom: 0 },
      }}
    >
      {/* Prompt + Input — single command-line row */}
      <box
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          height: 1,
          padding: { left: 1, right: 1, top: 0 },
        }}
      >
        <text
          style={{ color: connected ? theme.success : theme.error }}
          content={connectedIcon}
        />
        <text
          style={{
            color: theme.primary,
            padding: { left: 1 },
          }}
          content="cogent"
        />
        <text
          style={{
            color: theme.textMuted,
            padding: { left: 1 },
          }}
          content="❯"
        />
        <input
          ref={inputRef}
          focused
          value={value}
          placeholder={
            connected
              ? 'Ask Cogent to do something...'
              : 'Disconnected — run cogent server first'
          }
          onSubmit={(val: string) => handleSubmit(val)}
          onInput={(val: string) => setValue(val)}
          style={{
            color: theme.text,
            placeholderColor: theme.textDim,
            backgroundColor: theme.surfaceAlt,
            flexGrow: 1,
          }}
        />
      </box>

      {/* Hint bar with all slash commands — own row */}
      <box
        style={{
          flexDirection: 'row',
          height: 1,
          padding: { left: 2, right: 1, top: 0, bottom: 1 },
        }}
      >
        <text
          style={{ color: theme.textDim }}
          content="/help  /skills  /sessions  /memory  /tasks  /mcp  /connect  /clear  /quit"
        />
      </box>
    </box>
  );
}
