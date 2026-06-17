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

      // Check if it's a command first
      if (trimmed.startsWith('/')) {
        const handled = await onCommand(trimmed);
        if (handled) {
          setValue('');
          return;
        }
      }

      onSend(trimmed);
      setValue('');
      // Refocus input after sending
      setTimeout(() => inputRef.current?.focus(), 0);
    },
    [onSend, onCommand, disabled]
  );

  return (
    <box
      style={{
        flexDirection: 'column',
        borderStyle: 'single',
        borderColor: connected ? theme.borderFocus : theme.border,
        backgroundColor: theme.surface,
      }}
    >
      {/* Prompt indicator */}
      <box style={{ flexDirection: 'row', alignItems: 'center', padding: { left: 1, right: 1 } }}>
        <text
          style={{
            color: connected ? theme.success : theme.error,
          }}
          content={connected ? '▶' : '✗'}
        />
        <text
          style={{
            color: theme.primary,
            padding: { left: 1 },
          }}
          content="cogent"
        />
        <text style={{ color: theme.textMuted }} content=" ❯ " />
      </box>

      {/* Input field */}
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
          padding: { left: 2, right: 1 },
          backgroundColor: theme.surface,
        }}
      />

      {/* Hint bar */}
      <box style={{ flexDirection: 'row', padding: { left: 1, right: 1 } }}>
        <text style={{ color: theme.textDim }} content="/help  /skills  /clear  /quit" />
      </box>
    </box>
  );
}
