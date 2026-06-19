/** @jsxImportSource @opentui/react */
import { theme } from '../theme';

export function Header() {
  return (
    <box
      style={{
        flexDirection: 'column',
        borderStyle: 'round',
        borderColor: theme.headerBorder,
        backgroundColor: theme.headerBg,
        padding: { left: 2, right: 2, top: 1, bottom: 1 },
        margin: { left: 1, right: 1, top: 1 },
      }}
    >
      {/* Title row */}
      <box
        style={{
          flexDirection: 'row',
          alignItems: 'center',
        }}
      >
        <text
          style={{
            color: theme.primaryBright,
            fontWeight: 'bold',
          }}
          content="◆"
        />
        <text
          style={{
            color: theme.text,
            fontWeight: 'bold',
            padding: { left: 1 },
          }}
          content=" COGENT"
        />
        <text
          style={{
            color: theme.accent,
            padding: { left: 1 },
          }}
          content="·"
        />
        <text
          style={{
            color: theme.textMuted,
            padding: { left: 1 },
          }}
          content="AI coworker"
        />
        <box style={{ flexGrow: 1 }} />
        <text
          style={{
            color: theme.textDim,
          }}
          content="v0.1"
        />
      </box>

      {/* Subtitle row */}
      <box
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          marginTop: 1,
        }}
      >
        <text
          style={{
            color: theme.primary,
          }}
          content="━━━"
        />
        <text
          style={{
            color: theme.textMuted,
            padding: { left: 2 },
          }}
          content="Plan"
        />
        <text
          style={{
            color: theme.textDim,
            padding: { left: 1, right: 1 },
          }}
          content="·"
        />
        <text
          style={{
            color: theme.textMuted,
          }}
          content="Execute"
        />
        <text
          style={{
            color: theme.textDim,
            padding: { left: 1, right: 1 },
          }}
          content="·"
        />
        <text
          style={{
            color: theme.textMuted,
          }}
          content="Verify"
        />
        <box style={{ flexGrow: 1 }} />
        <text
          style={{
            color: theme.textDim,
          }}
          content="type /help for commands"
        />
      </box>
    </box>
  );
}
